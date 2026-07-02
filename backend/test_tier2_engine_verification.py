"""v1.2.1 WS3 gate suite (docs/ingestion-automation-v1.2.1.md): Tier-2
engine-verified auto-approval (D26).

The gate: a candidate asset is checked ASYNCHRONOUSLY against the
approved corpus under a Tier-2 engine-verified policy, with domain-scoped
comparison when configured, pair-cap/dropped-pair declarations, and
event-only verifier provenance. A non-contradicted candidate may be
auto-approved through the governed policy path; a contradicted candidate
is HELD as a declared exception naming the contradicting approved asset,
without creating AssetRelationship rows, changing conflict scores, or
polluting approved-conflict surfaces. Ingestion records scheduling only,
the background task owns its session, and draining is deterministic.

The guardrail: Tier-2 verification is a refusal-to-approve mechanism,
never a rejection mechanism - the engine may say "do not auto-approve";
only humans refuse content.

The verifier seam: a deterministic fake (explicit, auditable - its
identity lands in provenance), the fake-Graph pattern applied to NLI.
Real NLI stays behind the EM_NLI_* environment knobs; CI proves the
policy machinery deterministically.
"""
import os
import sys
import json
import tempfile
import threading

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ.setdefault("OPENAI_API_KEY", "mock-key")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database as db
from app import ingestion
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_tier2_qdrant_")

from app import crud
from app import schemas
from app import connectors
from app import policy
from app import tier2
from app.main import create_approval_policy, update_approval_policy, \
    create_classification_policy
import test_support

MARKER = "five days weekly"

CORPUS_OFFICE = "Employees must work from the office five days weekly."
CLEAN_CANDIDATE = "Suppliers must submit invoices through the procurement portal."
CONTRA_CANDIDATE = "Employees must work remotely five days weekly."
FIN_CORPUS = "Budget owners must reconcile ledgers before month-end closing."
HR_CORPUS = "Managers must approve leave requests within five business days."
FIN_CANDIDATE = "Treasury staff must log wire transfers in the payments register."
HR_CANDIDATE = "Recruiters must archive interview notes after each hiring round."
LATE_CANDIDATE = "Auditors must retain working papers for the full engagement cycle."


class FakeVerifier:
    """Deterministic and auditable: a contradiction exists iff candidate
    and approved asset share the marker phrase. `release` gates check()
    so the suite can PROVE the pass is asynchronous; `max_pairs`
    simulates the pre-filter cap with declared drops."""
    identity = {"method": "FAKE_DETERMINISTIC_V1", "marker": MARKER,
                "note": "WS3 test seam - identity recorded in provenance"}

    def __init__(self):
        self.release = threading.Event()
        self.release.set()
        self.calls = []
        self.max_pairs = None

    def check(self, candidate, corpus):
        assert self.release.wait(timeout=30), "verifier gate never released"
        kept, dropped = corpus, 0
        if self.max_pairs is not None and len(corpus) > self.max_pairs:
            kept, dropped = corpus[:self.max_pairs], len(corpus) - self.max_pairs
        self.calls.append({"candidate": candidate.id,
                           "corpus": [a.id for a in kept]})
        contradictions = [
            {"asset_id": a.id, "score": 0.99}
            for a in kept if MARKER in candidate.content and MARKER in a.content]
        return {"pairs_checked": len(kept), "pairs_dropped": dropped,
                "contradictions": contradictions}


def write_file(folder, name, sentence):
    path = os.path.join(folder, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(sentence + "\n")


def events_of(session, event_type):
    return session.query(db.AuditEvent).filter(
        db.AuditEvent.event_type == event_type).order_by(db.AuditEvent.id).all()


def asset_with(session, project_id, sentence):
    asset = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.project_id == project_id,
        db.KnowledgeAsset.content == sentence).first()
    assert asset, f"No asset extracted for: {sentence[:40]}..."
    return asset


def main():
    print("\nInitializing test database for Tier-2 Engine Verification (D26) checks...")
    tmp = tempfile.mkdtemp(prefix="em_tier2_test_")
    db.engine = create_engine(f"sqlite:///{os.path.join(tmp, 'tier2.db')}",
                              connect_args={"check_same_thread": False})
    db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)
    db.Base.metadata.create_all(db.engine)
    session = db.SessionLocal()

    fake = FakeVerifier()
    tier2.verifier_factory = lambda: fake

    officer = test_support.governed_actor(session, "GovernanceOfficer")
    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Tier2", description="D26 gate", customer_id=customer.id), actor=officer)
    folder = tempfile.mkdtemp(prefix="em_tier2_src_")
    connector = db.SourceConnector(project_id=project.id, name="Tier2 Share",
                                   type="LOCAL_FOLDER", root_path=folder,
                                   include_extensions=".txt")
    session.add(connector)
    session.commit()
    session.refresh(connector)

    def scan(drain=True):
        job = db.IngestionJob(project_id=project.id, connector_id=connector.id,
                              status="PENDING")
        session.add(job)
        session.commit()
        session.refresh(job)
        connectors.execute_ingestion_job(session, job.id)
        if drain:
            tier2.drain()
        session.refresh(job)
        assert job.status == "COMPLETED", f"{job.status} / {job.error}"
        return job

    # Part 1: engine_conditions and domains are validated, loud;
    # empty objects normalize to NULL (not a Tier-2 policy).
    print("\n--- Part 1: engine condition validation ---")
    for bad, why in [
        ({"contradiction_check": "MAYBE"}, "unknown mode"),
        ({"other": 1}, "unknown field"),
    ]:
        try:
            create_approval_policy(project.id, schemas.ApprovalPolicyCreate(
                name="Bad", asset_types=["POLICY"], engine_conditions=bad),
                db_session=session, actor=officer)
            raise AssertionError(f"Must reject: {why}")
        except Exception as e:
            assert getattr(e, "status_code", None) == 400, f"{why}: {e}"
    try:
        create_approval_policy(project.id, schemas.ApprovalPolicyCreate(
            name="BadDomains", asset_types=["POLICY"], domains=["/bad/"]),
            db_session=session, actor=officer)
        raise AssertionError("Malformed domain prefix must be rejected")
    except Exception as e:
        assert getattr(e, "status_code", None) == 400, e
    empty = create_approval_policy(project.id, schemas.ApprovalPolicyCreate(
        name="Empty engine object", asset_types=["DEPARTMENT"],
        engine_conditions={}),
        db_session=session, actor=officer)
    assert empty.engine_conditions is None and not tier2.is_tier2(empty), \
        "An empty engine object is NULL - not a Tier-2 policy (D19 invariant)"
    print("Part 1 passed: malformed shapes rejected; empty object "
          "normalizes to NULL.")

    # Build the approved corpus: one human-approved office policy.
    write_file(folder, "office.txt", CORPUS_OFFICE)
    scan()
    corpus_office = asset_with(session, project.id, CORPUS_OFFICE)
    crud.update_knowledge_asset(session, corpus_office.id,
                                schemas.KnowledgeAssetUpdate(status="APPROVED"),
                                actor=officer)

    # Part 2: async discipline + the clean approval path.
    print("\n--- Part 2: async pass - scheduled only, then engine-verified approval ---")
    tier2_pol = create_approval_policy(project.id, schemas.ApprovalPolicyCreate(
        name="Engine verified", asset_types=sorted(policy.ALLOWED_ASSET_TYPES),
        engine_conditions={"contradiction_check": "CLEAN_REQUIRED"}),
        db_session=session, actor=officer)
    assert tier2.is_tier2(tier2_pol)

    write_file(folder, "procurement.txt", CLEAN_CANDIDATE)
    fake.release.clear()  # gate the verifier: the pass cannot finish yet
    job = scan(drain=False)

    # The job is COMPLETE while the verifier is still gated: ingestion
    # returned immediately and recorded scheduling ONLY (D4).
    candidate = asset_with(session, project.id, CLEAN_CANDIDATE)
    assert candidate.status == "CANDIDATE", \
        "The job must complete BEFORE the engine verdict exists"
    job_event = events_of(session, "INGESTION_JOB_COMPLETED")[-1]
    job_details = json.loads(job_event.details)
    assert job_details["tier2_scheduled"] is True
    assert "engine_verdict" not in json.dumps(job_details) and \
        "held" not in job_details, \
        "The ingestion summary must not claim results it does not have"
    assert job_details["auto_approval"]["deferred_to_tier2"] >= 1, \
        "Sync pass declares the deferral honestly"

    fake.release.set()
    tier2.drain()
    session.refresh(candidate)
    assert candidate.status == "APPROVED", \
        "A clean candidate under a satisfied Tier-2 policy is auto-approved"

    prov = json.loads(events_of(session, "ASSET_AUTO_APPROVED")[-1].details)
    assert prov["tier"] == "TIER2"
    assert prov["policy_snapshot"]["engine_conditions"] == \
        {"contradiction_check": "CLEAN_REQUIRED"}
    verdict = prov["engine_verdict"]
    assert verdict["verifier"]["method"] == "FAKE_DETERMINISTIC_V1", \
        "The verifier seam identity is recorded in provenance - explicit, auditable"
    assert verdict["pairs_checked"] == 1 and verdict["pairs_dropped"] == 0
    assert verdict["domain_scope"] == "PROJECT" and verdict["contradictions"] == []

    summary_event = events_of(session, "POLICY_TIER2_COMPLETED")[-1]
    assert summary_event.id > job_event.id, \
        "The pass reports itself AFTER the job completed (ledger ordering)"
    print("Part 2 passed: job completed with scheduling only; engine "
          "verdict arrived asynchronously; provenance carries the seam "
          "identity, pair counts, and domain scope.")

    # Part 3: a contradicted candidate is HELD, naming the contradicting
    # asset - no AssetRelationship rows, no conflict-surface pollution.
    print("\n--- Part 3: contradicted candidate held (refusal, never rejection) ---")
    rel_count_before = session.query(db.AssetRelationship).count()
    write_file(folder, "remote.txt", CONTRA_CANDIDATE)
    scan()
    contra = asset_with(session, project.id, CONTRA_CANDIDATE)
    assert contra.status == "CANDIDATE", \
        "Engines refuse to approve; only humans refuse content"
    summary = json.loads(events_of(session, "POLICY_TIER2_COMPLETED")[-1].details)
    assert summary["held_contradicted"] == 1
    held = summary["held"][0]
    assert held["asset_id"] == contra.id
    assert held["contradictions"][0]["asset_id"] == corpus_office.id, \
        "The held result must NAME the contradicting approved asset"
    assert held["contradictions"][0]["score"] == 0.99
    assert session.query(db.AssetRelationship).count() == rel_count_before, \
        "Candidate verdicts live in event provenance ONLY - never " \
        "AssetRelationship rows (conflict surfaces stay clean)"
    print("Part 3 passed: candidate held with the contradicting asset "
          "named; zero relationship rows created.")

    # Part 4: domain-scoped comparison (WS1 taxonomy consumed).
    print("\n--- Part 4: domain coverage narrows candidate AND corpus ---")
    create_classification_policy(project.id, schemas.ClassificationPolicyCreate(
        name="By folder",
        rules=[{"domain": "finances", "match": {"uri_prefix": os.path.join(
            os.path.abspath(folder), "fin") + os.sep}},
               {"domain": "hr", "match": {"uri_prefix": os.path.join(
                   os.path.abspath(folder), "hr") + os.sep}}]),
        db_session=session, actor=officer)
    write_file(folder, os.path.join("fin", "ledgers.txt"), FIN_CORPUS)
    write_file(folder, os.path.join("hr", "leave.txt"), HR_CORPUS)
    scan()
    fin_corpus = asset_with(session, project.id, FIN_CORPUS)
    hr_corpus = asset_with(session, project.id, HR_CORPUS)
    assert fin_corpus.domain == "finances" and hr_corpus.domain == "hr"
    for a in (fin_corpus, hr_corpus):
        crud.update_knowledge_asset(session, a.id,
                                    schemas.KnowledgeAssetUpdate(status="APPROVED"),
                                    actor=officer)

    # Narrow the Tier-2 policy to finances (a definition change).
    tier2_pol = update_approval_policy(tier2_pol.id, schemas.ApprovalPolicyUpdate(
        domains=["finances"]), db_session=session, actor=officer)
    assert tier2_pol.version == 2 and tier2_pol.domains == ["finances"]

    write_file(folder, os.path.join("fin", "wires.txt"), FIN_CANDIDATE)
    write_file(folder, os.path.join("hr", "notes.txt"), HR_CANDIDATE)
    scan()
    fin_candidate = asset_with(session, project.id, FIN_CANDIDATE)
    hr_candidate = asset_with(session, project.id, HR_CANDIDATE)
    assert fin_candidate.status == "APPROVED", \
        "A finances candidate is covered and clean -> approved"
    assert hr_candidate.status == "CANDIDATE", \
        "An hr candidate is outside the policy's domain coverage (deny-by-default)"
    # The comparison corpus was scoped: ONLY the finances-approved asset,
    # never the hr or unclassified approved assets.
    fin_call = next(c for c in fake.calls if c["candidate"] == fin_candidate.id)
    assert fin_call["corpus"] == [fin_corpus.id], fin_call
    prov = json.loads(events_of(session, "ASSET_AUTO_APPROVED")[-1].details)
    assert prov["engine_verdict"]["domain_scope"] == ["finances"]
    summary = json.loads(events_of(session, "POLICY_TIER2_COMPLETED")[-1].details)
    assert summary["skipped_not_covered"] >= 1, \
        "The uncovered candidate is declared, not silently ignored"
    print("Part 4 passed: candidate and corpus both scoped by domain "
          "prefix; uncovered candidates declared.")

    # Part 5: the pair cap - drops are DECLARED (D12).
    print("\n--- Part 5: pair cap with declared drops ---")
    tier2_pol = update_approval_policy(tier2_pol.id, schemas.ApprovalPolicyUpdate(
        domains=None), db_session=session, actor=officer)  # whole project again
    fake.max_pairs = 1
    write_file(folder, "audit.txt", LATE_CANDIDATE)
    scan()
    late = asset_with(session, project.id, LATE_CANDIDATE)
    assert late.status == "APPROVED"
    prov = json.loads(events_of(session, "ASSET_AUTO_APPROVED")[-1].details)
    assert prov["engine_verdict"]["pairs_checked"] == 1
    assert prov["engine_verdict"]["pairs_dropped"] >= 1, \
        "Capped comparisons must declare their drops (D12)"
    summary = json.loads(events_of(session, "POLICY_TIER2_COMPLETED")[-1].details)
    assert summary["pairs_dropped_total"] >= 1
    fake.max_pairs = None
    print("Part 5 passed: cap applied, drops declared in provenance and "
          "the pass summary.")

    # Part 6: engine unavailable - refuse to approve, and say so.
    print("\n--- Part 6: engine unavailable = nothing approved, declared ---")
    tier2.verifier_factory = lambda: None
    write_file(folder, "unverified.txt",
               "Operators must escalate unresolved alarms to the duty manager.")
    scan()
    unverified = asset_with(
        session, project.id,
        "Operators must escalate unresolved alarms to the duty manager.")
    assert unverified.status == "CANDIDATE", \
        "No engine, no engine-verified approval - ever"
    summary = json.loads(events_of(session, "POLICY_TIER2_COMPLETED")[-1].details)
    assert summary["engine_available"] is False
    assert summary["auto_approved"] == 0 and summary["assets_considered"] >= 1
    tier2.verifier_factory = lambda: fake
    print("Part 6 passed: unavailable engine declared; nothing approved.")

    session.close()
    print("\nAll Tier-2 Engine Verification (D26) checks passed: the engine "
          "refuses to approve, never rejects; verdicts live in provenance "
          "only; the pass is genuinely asynchronous and always reports "
          "itself.")


if __name__ == "__main__":
    main()
