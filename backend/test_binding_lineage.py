import os
import sys
import json
import hashlib
import re
import tempfile
import inspect

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ.setdefault("OPENAI_API_KEY", "mock-key")
os.environ.pop("OPENAI_MODEL", None)
os.environ["EM_PACKAGE_DIR"] = tempfile.mkdtemp(prefix="empkg_lineage_test_")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database as db
from app import schemas
from app import crud
from app import llm
from app import evaluation
from app import identity
from app import binding_lineage
from app.main import update_llm_setting
import test_support

# v1.1.x WS3 acceptance suite (docs/workbench-v1.1x.md). The gate: a
# server-composed lineage projection walking backwards (binding -> package
# -> family status -> model -> evidence -> runs -> assets -> source
# documents) and sideways (principal -> credentials -> audit), in which
# EVERY expected hop either resolves or is explicitly declared missing -
# no silent gaps. The chain is a product claim: this suite tests it as
# one artifact, including under adversarial fact deletion, and proves the
# lineage stays answerable when the issuing human is renamed or demoted
# (the Alice test applied to issuance evidence).


class FakeConsumerEngine:
    def __call__(self, model, system, user, max_tokens):
        match = re.search(r"\[asset_id (\d+)\][^\n]*\n  Content: ([^\n]+)", system)
        return match.group(2).strip() if match else "No evidence."


def make_asset(session, project, doc, name, text, idx, qa):
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
                                actor=qa)
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


def all_missing(lineage):
    out = []
    for key in ("issued_by", "package", "family_status", "model",
                "selection_evidence", "principal", "credentials", "audit"):
        out += lineage[key]["missing"]
    out += lineage["evaluation_runs"]["missing"]
    out += lineage["assets"]["missing"]
    out += lineage["source_documents"]["missing"]
    return out


def row_counts(session):
    return {t.name: len(session.execute(t.select()).fetchall())
            for t in db.Base.metadata.sorted_tables}


def main():
    print("\nInitializing test database for Binding Lineage (WS3) checks...")
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    db.Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db.SessionLocal = TestingSessionLocal
    session = TestingSessionLocal()

    customer = crud.get_or_create_default_customer(session)
    qa = test_support.governed_actor(session, "qa")
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Lineage Test", description="WS3", customer_id=customer.id), actor=qa)
    doc = crud.create_document(session, project_id=project.id, filename="Safety.txt",
                               file_path="uploads/s.txt", actor=qa)
    a1 = make_asset(session, project, doc, "Evacuation Protocol",
                    "During thermal runaway, evacuate the battery hall immediately.", 0, qa)
    a2 = make_asset(session, project, doc, "Training Policy",
                    "All operators must complete safety training before access.", 1, qa)
    model = crud.create_expert_model(session, schemas.ExpertModelCreate(
        name="Facility Safety Expert", description="", project_id=project.id,
        asset_ids=[a1.id, a2.id]), actor=qa)
    pkg = crud.create_agent_package(session, schemas.AgentPackageCreate(
        name="Facility Safety Expert", project_id=project.id,
        expert_model_id=model.id, governance_version="1.0",
        clearance_level="INTERNAL"), actor=qa)
    session.add(db.BenchmarkQuestion(
        project_id=project.id,
        question="What must staff do during thermal runaway in the battery hall?",
        expected_claims_json=json.dumps([]), expected_answer_type="FACTUAL",
        required_citation_count=1, min_required_coverage=0.5))
    session.commit()

    saved_adapters = dict(llm.ADAPTERS)
    llm.ADAPTERS["OPENAI"] = FakeConsumerEngine()
    llm.ADAPTERS["ANTHROPIC"] = FakeConsumerEngine()
    try:
        run1 = run_package_eval(session, qa, project, model, pkg, "gpt-4o-mini", "OPENAI")
        run2 = run_package_eval(session, qa, project, model, pkg, "claude-sonnet-4-6", "ANTHROPIC")
        crud.set_package_model_selection(session, pkg.id, schemas.PackageModelSelectionUpdate(
            provider="OPENAI", model="gpt-4o-mini",
            supporting_evaluation_run_ids=[run1.id, run2.id],
            rationale="Cheapest model at pass parity across the comparative set."), actor=qa)
        agent = identity.create_principal(session, "agent-hall", "Battery Hall Agent",
                                          kind="AGENT", clearance="RESTRICTED")
        identity.issue_token(session, agent, label="hall", actor="qa")
        binding = crud.create_expert_agent_binding(session, pkg.id,
            schemas.ExpertAgentBindingCreate(agent_principal_id=agent.id), actor=qa)

        # --- Part 1: the healthy chain - every hop resolves, zero gaps ---
        print("\n--- Part 1: full chain resolves with zero declared gaps ---")
        lineage = binding_lineage.build_lineage(session, binding.id)
        assert lineage["declared_missing_total"] == 0, all_missing(lineage)
        assert all_missing(lineage) == []

        assert lineage["binding"]["package_hash"] == pkg.package_hash
        assert lineage["package"]["hash"] == pkg.package_hash
        assert lineage["package"]["compiled_at"], "manifest snapshot must surface compiled_at"
        assert lineage["family_status"]["superseded"] is False
        assert lineage["model"]["matches_current_selection"] is True
        assert lineage["selection_evidence"]["rationale"].startswith("Cheapest model")
        assert lineage["selection_evidence"]["selected_by"] == "qa"
        run_ids = {r["run_id"] for r in lineage["evaluation_runs"]["runs"]}
        assert run_ids == {run1.id, run2.id}
        assert all(r["evaluates_bound_artifact"] for r in lineage["evaluation_runs"]["runs"])
        asset_names = {a["name"] for a in lineage["assets"]["assets"]}
        assert asset_names == {"Evacuation Protocol", "Training Policy"}
        docs = lineage["source_documents"]["documents"]
        assert len(docs) == 1 and docs[0]["filename"] == "Safety.txt"
        assert "content_hash" in docs[0], \
            "provenance fields are reported (None when honestly absent, never omitted)"
        assert lineage["principal"]["name"] == "agent-hall"
        assert lineage["principal"]["clearance_now"] == "RESTRICTED"
        assert lineage["binding"]["principal_clearance_at_issue"] == "RESTRICTED"
        assert lineage["credentials"]["active_count"] == 1
        assert lineage["credentials"]["kinds"] == ["API_TOKEN"]
        events = {e["event_type"] for e in lineage["audit"]["events"]}
        assert {"EXPERT_AGENT_BINDING_CREATED", "PACKAGE_MODEL_SELECTED",
                "AGENT_PACKAGE_CREATED"} <= events
        assert lineage["warnings"] == [], "a healthy binding carries no warnings"
        print("Part 1 passed: binding -> package -> model -> evidence -> runs -> assets -> "
              "documents and sideways to identity, every hop resolved.")

        # --- Part 2: issued-by survives rename and demotion (the Alice test) ---
        print("\n--- Part 2: issuance evidence is immutable (D20) ---")
        issued = lineage["issued_by"]
        assert issued["principal_name"] == "qa" and issued["role_at_issue"] == "GOVERNANCE_REVIEWER"
        qa_principal = identity.get_principal(session, "qa")
        qa_principal.display_name = "Renamed Reviewer"
        qa_principal.role = "READ_ONLY"  # demoted after the fact
        session.commit()
        lineage2 = binding_lineage.build_lineage(session, binding.id)
        assert lineage2["issued_by"]["role_at_issue"] == "GOVERNANCE_REVIEWER", \
            "Demotion must never rewrite who issued the binding and as what role"
        assert lineage2["issued_by"]["principal_name"] == "qa"
        print("Part 2 passed: rename and demotion cannot change what the issuance fact answers.")

        # --- Part 3: recompile -> superseded + warnings from THE shared function ---
        print("\n--- Part 3: family supersession surfaces as warnings ---")
        pkg2 = crud.create_agent_package(session, schemas.AgentPackageCreate(
            name="Facility Safety Expert", project_id=project.id,
            expert_model_id=model.id, governance_version="2.0",
            clearance_level="INTERNAL"), actor=qa)
        assert pkg2.package_hash != pkg.package_hash
        lineage3 = binding_lineage.build_lineage(session, binding.id)
        fam = lineage3["family_status"]
        assert fam["superseded"] is True and fam["current_package_id"] == pkg2.id
        warn_conditions = {w["condition"] for w in lineage3["warnings"]}
        assert "BINDING_PACKAGE_HASH_DRIFT" in warn_conditions
        assert "SELECTION_PACKAGE_HASH_DRIFT" in warn_conditions
        from app import consumption_inbox
        for w in lineage3["warnings"]:
            assert w["severity"] == consumption_inbox.severity_of(w["condition"]), \
                "Explorer warnings must come from THE shared severity function"
        print("Part 3 passed: superseded artifact -> inbox-identical warnings on the lineage.")

        # --- Part 4: adversarial deletion -> declared gaps, never silence ---
        print("\n--- Part 4: every severed hop is declared (D12) ---")
        # Sever a supporting run, a packaged asset, and the principal - raw
        # SQL past the ORM, the way real corruption arrives. (Ids captured
        # first: the ORM instances expire once their rows are gone.)
        run1_id, run2_id, a1_id, agent_id, binding_id = \
            run1.id, run2.id, a1.id, agent.id, binding.id
        session.execute(db.EvaluationRun.__table__.delete().where(
            db.EvaluationRun.__table__.c.id == run2_id))
        session.execute(db.KnowledgeAsset.__table__.delete().where(
            db.KnowledgeAsset.__table__.c.id == a1_id))
        session.execute(db.Principal.__table__.delete().where(
            db.Principal.__table__.c.id == agent_id))
        session.commit()
        session.expire_all()

        lineage4 = binding_lineage.build_lineage(session, binding_id)
        gaps = all_missing(lineage4)
        assert lineage4["declared_missing_total"] == len(gaps) >= 3
        assert any(f"supporting evaluation run {run2_id} not found" in g for g in gaps)
        assert any("no longer exists in the knowledge base" in g for g in gaps)
        assert any("not found in the registry" in g for g in gaps)
        # The surviving structure still resolves: one run, one asset, the doc.
        assert [r["run_id"] for r in lineage4["evaluation_runs"]["runs"]] == [run1_id]
        assert len(lineage4["assets"]["assets"]) == 2, \
            "the package snapshot still lists BOTH compiled assets - the snapshot is the evidence"
        assert len(lineage4["source_documents"]["documents"]) == 1
        print("Part 4 passed: severed hops are named one by one; the snapshot remains the evidence.")

        # --- Part 5: unknown binding is a LookupError, not an empty chain ---
        print("\n--- Part 5: missing binding refuses loudly ---")
        try:
            binding_lineage.build_lineage(session, 99999)
            raise AssertionError("Unknown binding must raise, never return a hollow lineage")
        except LookupError:
            pass
        print("Part 5 passed: no lineage fabricated for a binding that does not exist.")

        # --- Part 6: pure projection - zero writes, GET-only surface ---
        print("\n--- Part 6: no writes, no lifecycle, read-only routes ---")
        before = row_counts(session)
        for _ in range(3):
            binding_lineage.build_lineage(session, binding_id)
        assert row_counts(session) == before, \
            "build_lineage must not create, update, or delete any row"
        source = inspect.getsource(binding_lineage)
        code_only = "\n".join(line.split("#", 1)[0] for line in source.splitlines())
        # (A binding *status field* is impossible by the D24 schema guard;
        # here we forbid the write machinery itself.)
        for forbidden in ("session.add", ".commit(", "session.delete",
                          "log_audit_event"):
            assert forbidden not in code_only, \
                f"binding_lineage must stay a pure projection: found '{forbidden}'"
        from app.main import app as fastapi_app
        binding_routes = [r for r in fastapi_app.routes
                          if getattr(r, "path", "").startswith("/api/bindings/")]
        assert sorted(r.path for r in binding_routes) == \
            ["/api/bindings/{binding_id}", "/api/bindings/{binding_id}/lineage"], \
            "Exactly the TWO ratified binding endpoints"
        for r in binding_routes:
            assert r.methods == {"GET"}, \
                "No withdrawal, deactivate, revoke, runtime, or deploy surface on bindings"
        print("Part 6 passed: the lineage is a pure projection; /api/bindings/* answers GET only.")

    finally:
        llm.ADAPTERS.clear()
        llm.ADAPTERS.update(saved_adapters)

    print("\nAll Binding Lineage (WS3) checks passed - the chain is a tested product "
          "claim: every hop resolves or is declared, and history stays answerable.")


if __name__ == "__main__":
    main()
