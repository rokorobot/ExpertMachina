import os
import sys
import json
import hashlib
import re
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ.setdefault("OPENAI_API_KEY", "mock-key")
os.environ.pop("OPENAI_MODEL", None)
os.environ["EM_PACKAGE_DIR"] = tempfile.mkdtemp(prefix="empkg_binding_test_")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database as db
from app import schemas
from app import crud
from app import llm
from app import identity
from app import evaluation
from app.main import update_llm_setting
import test_support

# v1.1 WS4 acceptance suite (docs/consumption-arc-v1.md, D22). The gate:
#
#   Given an approved AgentPackage with a current PackageModelSelection,
#   an authorized operator can create an ExpertAgent binding to an
#   existing active AGENT principal. Creation refuses: no selection,
#   selected-model mismatch, inactive/non-AGENT principal, clearance below
#   package clearance, missing artifact, hash drift. Audited. The binding
#   executes nothing, mints no tokens, orchestrates nothing. Later
#   selection changes do not rewrite existing bindings.


class FakeConsumerEngine:
    def __call__(self, model, system, user, max_tokens):
        match = re.search(r"\[asset_id (\d+)\][^\n]*\n  Content: ([^\n]+)", system)
        return match.group(2).strip()


def make_asset(session, project, doc, name, text, idx=0):
    chunk = db.DocumentChunk(document_id=doc.id, text=text, chunk_index=idx)
    session.add(chunk)
    session.commit()
    session.refresh(chunk)
    a = crud.create_knowledge_asset(session, schemas.KnowledgeAssetCreate(
        type="POLICY", name=name, content=text, project_id=project.id,
        document_id=doc.id, chunk_id=chunk.id, source_page=1, source_section="S1",
        source_hash=hashlib.sha256(text.encode()).hexdigest()))
    crud.update_knowledge_asset(session, asset_id=a.id,
                                update=schemas.KnowledgeAssetUpdate(status="APPROVED"),
                                actor=test_support.governed_actor(session, "qa"))
    session.refresh(a)
    return a


def run_package_eval(session, qa, project, model, pkg, consumer_model, provider):
    update_llm_setting("package_consumer", schemas.LLMFunctionSettingUpdate(
        model=consumer_model, provider=provider), db_session=session, actor=qa)
    run = evaluation.create_evaluation_run(session, schemas.EvaluationRunCreate(
        project_id=project.id, expert_model_id=model.id,
        run_type="PACKAGE", agent_package_id=pkg.id))
    evaluation.run_evaluation_batch(session, run.id)
    session.refresh(run)
    assert run.status == "COMPLETED", run.status
    return run


def expect_refusal(session, pkg_id, create, fragment, actor):
    try:
        crud.create_expert_agent_binding(session, pkg_id, create, actor=actor)
        raise AssertionError(f"Binding accepted but should refuse: {fragment}")
    except ValueError as e:
        assert fragment in str(e), f"expected '{fragment}' in: {e}"


def main():
    print("\nInitializing test database for Expert Agent Binding (WS4) checks...")
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    db.Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db.SessionLocal = TestingSessionLocal
    session = TestingSessionLocal()

    customer = crud.get_or_create_default_customer(session)
    qa = test_support.governed_actor(session, "qa")
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Binding Test", description="WS4", customer_id=customer.id), actor=qa)
    doc = crud.create_document(session, project_id=project.id, filename="Safety.txt",
                               file_path="uploads/s.txt", actor=qa)
    a_evac = make_asset(session, project, doc, "Evacuation Protocol",
                        "During thermal runaway, evacuate the battery hall immediately.", 0)
    model = crud.create_expert_model(session, schemas.ExpertModelCreate(
        name="Facility Safety Expert", description="", project_id=project.id,
        asset_ids=[a_evac.id]), actor=qa)
    pkg = crud.create_agent_package(session, schemas.AgentPackageCreate(
        name="Facility Safety Expert", project_id=project.id,
        expert_model_id=model.id, governance_version="1.0",
        clearance_level="INTERNAL"), actor=qa)
    pkg_other = crud.create_agent_package(session, schemas.AgentPackageCreate(
        name="Facility Safety Expert", project_id=project.id,
        expert_model_id=model.id, governance_version="2.0",
        clearance_level="INTERNAL"), actor=qa)

    b = db.BenchmarkQuestion(
        project_id=project.id,
        question="What must staff do during thermal runaway in the battery hall?",
        expected_claims_json=json.dumps([]), expected_answer_type="FACTUAL",
        required_citation_count=1, min_required_coverage=0.9)
    session.add(b)
    session.commit()

    agent_ok = identity.create_principal(session, "agent-hr", "HR Expert Agent",
                                         kind="AGENT", clearance="INTERNAL")
    agent_low = identity.create_principal(session, "agent-public", "Public Kiosk Agent",
                                          kind="AGENT", clearance="PUBLIC")
    agent_dead = identity.create_principal(session, "agent-retired", "Retired Agent",
                                           kind="AGENT", clearance="EXECUTIVE")
    agent_dead.active = False
    session.commit()

    saved_adapters = dict(llm.ADAPTERS)
    llm.ADAPTERS["OPENAI"] = FakeConsumerEngine()
    llm.ADAPTERS["ANTHROPIC"] = FakeConsumerEngine()
    try:
        run_a = run_package_eval(session, qa, project, model, pkg, "gpt-4o-mini", "openai")
        run_b = run_package_eval(session, qa, project, model, pkg, "claude-opus-4-8", "anthropic")

        ok = schemas.ExpertAgentBindingCreate(agent_principal_id=agent_ok.id)

        # Part 1: every refusal class, and nothing left behind.
        print("\n--- Part 1: Creation refuses, case by case ---")
        expect_refusal(session, pkg.id, ok, "no current model selection", qa)

        crud.set_package_model_selection(session, pkg.id, schemas.PackageModelSelectionUpdate(
            provider="OPENAI", model="gpt-4o-mini",
            supporting_evaluation_run_ids=[run_a.id, run_b.id],
            rationale="Best pass rate at lowest cost."), actor=qa)

        expect_refusal(session, pkg.id, schemas.ExpertAgentBindingCreate(
            agent_principal_id=qa.principal.id), "not AGENT", qa)
        expect_refusal(session, pkg.id, schemas.ExpertAgentBindingCreate(
            agent_principal_id=agent_dead.id), "deactivated", qa)
        expect_refusal(session, pkg.id, schemas.ExpertAgentBindingCreate(
            agent_principal_id=agent_low.id), "below the package's compiled clearance", qa)
        expect_refusal(session, pkg.id, schemas.ExpertAgentBindingCreate(
            agent_principal_id=agent_ok.id,
            expected_provider="ANTHROPIC", expected_model="claude-opus-4-8"),
            "Selected model mismatch", qa)
        try:
            crud.create_expert_agent_binding(session, pkg.id, schemas.ExpertAgentBindingCreate(
                agent_principal_id=99999), actor=qa)
            raise AssertionError("Missing principal must be a lookup failure")
        except LookupError:
            pass

        real_path = pkg.file_path
        pkg.file_path = real_path + ".gone"
        session.commit()
        expect_refusal(session, pkg.id, ok, "no .empkg artifact", qa)
        pkg.file_path = pkg_other.file_path  # a VALID chain, but the wrong artifact
        session.commit()
        expect_refusal(session, pkg.id, ok, "drifted artifact", qa)
        pkg.file_path = real_path
        session.commit()

        assert session.query(db.ExpertAgentBinding).count() == 0, \
            "No refused proposal may leave a binding behind"
        assert session.query(db.AuditEvent).filter(
            db.AuditEvent.event_type == "EXPERT_AGENT_BINDING_CREATED").count() == 0
        print("Part 1 passed: selection, principal, clearance, mismatch, artifact, and drift checks hold.")

        # Part 2: THE WS4 GATE - a governed binding, fully snapshotted,
        # audited, and inert.
        print("\n--- Part 2: A governed binding with full snapshots ---")
        credentials_before = session.query(db.Credential).count()
        binding = crud.create_expert_agent_binding(session, pkg.id, schemas.ExpertAgentBindingCreate(
            agent_principal_id=agent_ok.id,
            expected_provider="openai", expected_model="gpt-4o-mini"), actor=qa)
        assert binding.package_version == "1.0" and binding.package_hash == pkg.package_hash
        assert (binding.selected_provider, binding.selected_model_name) == ("OPENAI", "gpt-4o-mini"), \
            "The binding model must equal the current selection at issue time"
        assert binding.agent_principal_id == agent_ok.id
        assert binding.principal_clearance_at_issue == "INTERNAL"
        evidence = binding.selection_evidence
        assert evidence["supporting_evaluation_run_ids"] == [run_a.id, run_b.id]
        assert evidence["rationale"] == "Best pass rate at lowest cost."
        assert binding.identity_fact_id is not None, "The issuing actor's fact is part of the binding"
        events = session.query(db.AuditEvent).filter(
            db.AuditEvent.event_type == "EXPERT_AGENT_BINDING_CREATED").all()
        assert len(events) == 1 and events[0].identity_fact_id == binding.identity_fact_id
        details = json.loads(events[0].details)
        assert details["agent_principal_name"] == "agent-hr"
        assert details["selection_evidence"]["model"] == "gpt-4o-mini"
        # Inert by construction: no token minted, nothing executed.
        assert session.query(db.Credential).count() == credentials_before, \
            "A binding must NOT mint tokens - token issuance is a governed identity operation"
        print("Part 2 passed: snapshots, identity fact, audit - and zero credentials minted.")

        # Part 3: later selection changes never rewrite existing bindings.
        print("\n--- Part 3: Bindings are historical evidence ---")
        frozen = (binding.selected_provider, binding.selected_model_name,
                  binding.selection_evidence_json)
        crud.set_package_model_selection(session, pkg.id, schemas.PackageModelSelectionUpdate(
            provider="ANTHROPIC", model="claude-opus-4-8",
            supporting_evaluation_run_ids=[run_b.id],
            rationale="Re-selected after coverage review."), actor=qa)
        session.refresh(binding)
        assert (binding.selected_provider, binding.selected_model_name,
                binding.selection_evidence_json) == frozen, \
            "Changing the selection must not rewrite an issued binding"
        binding2 = crud.create_expert_agent_binding(session, pkg.id, schemas.ExpertAgentBindingCreate(
            agent_principal_id=agent_ok.id), actor=qa)
        assert binding2.selected_model_name == "claude-opus-4-8"
        assert session.query(db.ExpertAgentBinding).count() == 2, \
            "Bindings append - the old binding remains as deployment history"
        assert crud.list_expert_agent_bindings(session, pkg.id)[0].id == binding.id
        print("Part 3 passed: old binding frozen, new binding snapshots the new selection.")

        # Part 4: structural - a binding, never a runtime (D22).
        print("\n--- Part 4: Binding surface is append-only and execution-free ---")
        cols = {c.name for c in db.ExpertAgentBinding.__table__.columns}
        assert cols == {"id", "agent_package_id", "package_version", "package_hash",
                        "selected_provider", "selected_model_name", "agent_principal_id",
                        "principal_clearance_at_issue", "selection_evidence_json",
                        "identity_fact_id", "created_at"}, cols
        for forbidden in ("token", "status", "runtime", "endpoint", "tool"):
            assert not any(forbidden in c for c in cols), \
                f"Binding must not carry {forbidden}-shaped state"
        # T2.4: bindings routes relocated verbatim from main.py into the
        # packages router (pure relocation). Assertion unchanged; file moved.
        src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app", "routers", "packages.py")
        with open(src_path, encoding="utf-8") as f:
            src = f.read()
        assert '@router.post("/api/packages/{package_id}/bindings"' in src
        assert '@router.get("/api/packages/{package_id}/bindings"' in src
        for verb in ("put", "patch", "delete"):
            assert f'@router.{verb}("/api/packages/{{package_id}}/bindings' not in src, \
                "Bindings are append-only at the API boundary"
        post_route = src.split('@router.post("/api/packages/{package_id}/bindings"')[1].split("@router.")[0]
        assert 'require_perm("assets:approve")' in post_route
        print("Part 4 passed: snapshot columns only; POST+GET only; approval-tier write.")
    finally:
        llm.ADAPTERS.clear()
        llm.ADAPTERS.update(saved_adapters)

    print("\n=== All Expert Agent Binding (WS4) tests passed successfully! ===")


if __name__ == "__main__":
    main()
