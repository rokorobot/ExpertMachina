"""T2.6 shed verification (docs/t26-llama-index-inventory.md).

The llama-index -> native openai SDK shed touches LLM paths that CANNOT be
live-verified here (no real OPENAI_API_KEY - the standing open slot). This
suite closes that gap the only way available: it MOCKS the provider seam and
asserts (a) the two native helpers build the right request and parse the
right response, and (b) the two rewritten parsers (claim decomposition, asset
extraction) still turn a model reply into the same structures the
llama-index versions produced. The deterministic fallback paths (mock-key)
are covered by the rest of the harness; this suite covers the real-key
branch that the harness never enters.
"""
import os
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("EM_NLI_VERIFICATION", "off")
os.environ.setdefault("OPENAI_API_KEY", "mock-key")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import database as db


# --- fake openai SDK client (records requests, returns canned responses) ---

class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeCompletionResp:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


class _FakeEmbeddingDatum:
    def __init__(self, vector):
        self.embedding = vector


class _FakeEmbeddingResp:
    def __init__(self, vector):
        self.data = [_FakeEmbeddingDatum(vector)]


def _fake_openai_client(captured, *, completion=None, embedding=None):
    class _Completions:
        def create(self, **kw):
            captured["completion_request"] = kw
            return _FakeCompletionResp(completion)

    class _Embeddings:
        def create(self, **kw):
            captured["embedding_request"] = kw
            return _FakeEmbeddingResp(embedding)

    class _Chat:
        completions = _Completions()

    class _Client:
        chat = _Chat()
        embeddings = _Embeddings()

    return _Client()


def test_openai_complete_request_and_parse():
    from app import llm
    import openai
    captured = {}
    orig = openai.OpenAI
    openai.OpenAI = lambda *a, **k: _fake_openai_client(captured, completion="  the answer  ")
    try:
        out = llm.openai_complete("gpt-4o-mini", "my prompt")
    finally:
        openai.OpenAI = orig
    assert out == "the answer", f"output not stripped/parsed: {out!r}"
    req = captured["completion_request"]
    assert req["model"] == "gpt-4o-mini", req
    assert req["messages"] == [{"role": "user", "content": "my prompt"}], req
    print("Part 1 passed: openai_complete sends a single-user-message request and strips the reply.")


def test_openai_embedding_request_and_parse():
    from app import llm
    import openai
    captured = {}
    orig = openai.OpenAI
    openai.OpenAI = lambda *a, **k: _fake_openai_client(captured, embedding=[0.1, 0.2, 0.3])
    try:
        vec = llm.openai_embedding("hello world")
    finally:
        openai.OpenAI = orig
    assert vec == [0.1, 0.2, 0.3], vec
    req = captured["embedding_request"]
    assert req["model"] == "text-embedding-ada-002", req  # matches llama-index default (1536-dim)
    assert req["input"] == "hello world", req
    print("Part 2 passed: openai_embedding calls ada-002 and returns the vector.")


def test_claims_decompose_parses_json_array():
    from app import claims, llm
    os.environ["OPENAI_API_KEY"] = "sk-real-for-test"  # non-mock -> real branch runs
    orig_complete, orig_model = llm.openai_complete, llm.model_for
    # model_for() reads config from the DB; irrelevant to parsing - stub it.
    llm.model_for = lambda *a, **k: "gpt-4o-mini"
    # A model reply with prose around the JSON array (the regex must extract it).
    llm.openai_complete = lambda model, prompt: (
        'Here you go:\n["Deviations must be logged within 24 hours.", '
        '"Managers review deviations weekly unless escalated."]')
    try:
        out = claims._decompose_llm("some policy text")
    finally:
        llm.openai_complete, llm.model_for = orig_complete, orig_model
        os.environ["OPENAI_API_KEY"] = "mock-key"
    assert out == [
        "Deviations must be logged within 24 hours.",
        "Managers review deviations weekly unless escalated.",
    ], out
    print("Part 3 passed: claim decomposition extracts and parses the JSON array from the reply.")


def test_extraction_parses_json_into_assets():
    from app import extraction, crud, schemas, ingestion, llm
    import test_support
    # Isolated in-memory DB (StaticPool: single shared connection).
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    db.Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    ingestion.get_qdrant_client = lambda: (_ for _ in ()).throw(RuntimeError("qdrant disabled"))

    actor = test_support.governed_actor(session, "shed_tester")  # identity.Actor (D20)
    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Shed", description="", customer_id=customer.id), actor=actor)
    doc = crud.create_document(session, project_id=project.id, filename="p.txt",
                               file_path="uploads/p.txt", actor=actor)
    chunk = db.DocumentChunk(document_id=doc.id, text="Refunds over $500 need director approval.",
                             chunk_index=0)
    session.add(chunk); session.commit(); session.refresh(chunk)

    orig = llm.openai_complete
    llm.openai_complete = lambda model, prompt: (
        '{"assets": [{"type": "policy", "name": "Refund Approval", '
        '"owner": "Finance", "condition": "over $500", '
        '"source_citation": "p.1", "content": "Refunds over $500 need director approval.", '
        '"source_section": "Refunds"}]}')
    try:
        ok = extraction.extract_via_llm(session, project.id, doc, chunk, api_key="sk-real-for-test")
    finally:
        llm.openai_complete = orig

    assert ok is True, "extract_via_llm should report success"
    assets = session.query(db.KnowledgeAsset).filter_by(project_id=project.id).all()
    assert len(assets) == 1, f"expected 1 extracted asset, got {len(assets)}"
    a = assets[0]
    assert a.type == "POLICY", a.type                       # lowercased 'policy' -> normalized
    assert a.name == "Refund Approval", a.name
    assert a.extraction_method == "LLM_ASSISTED", a.extraction_method
    assert "director approval" in a.content, a.content
    session.close()
    print("Part 4 passed: asset extraction parses the JSON reply into a governed KnowledgeAsset.")


if __name__ == "__main__":
    print("\nT2.6 shed verification (mocked provider seam)...")
    test_openai_complete_request_and_parse()
    test_openai_embedding_request_and_parse()
    test_claims_decompose_parses_json_array()
    test_extraction_parses_json_into_assets()
    print("\n=== All T2.6 shed verification tests passed. ===")
