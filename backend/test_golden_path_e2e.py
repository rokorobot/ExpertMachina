import os
import sys
import hashlib
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ.setdefault("OPENAI_API_KEY", "mock-key")
os.environ["EM_PACKAGE_DIR"] = tempfile.mkdtemp(prefix="empkg_golden_path_")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database as db
from app import schemas
from app import crud
from app import ingestion
from app import extraction
from app import package_consumer
from app import llm
import test_support


class GoldenPathFakeEngine:
    def __call__(self, model, system, user, max_tokens):
        assert "remote work" in user.lower()
        return "The remote work policy allows employees to work remotely up to three days per week. Per asset_id 1."


def test_golden_path_e2e_approved_package_answer_and_governance_block():
    """
    Consolidated Golden Path Acceptance Test.

    Proves:
    Document
      -> Ingested
      -> Parsed / Indexed
      -> Assets Extracted
      -> Approved
      -> Expert Model Created
      -> Package Compiled
      -> Package Consumed
      -> Question Answered
      -> Evidence Returned
      -> Audit Events Exist

    Also proves:
    Candidate / unapproved knowledge cannot be transferred into an Expert Model.
    """

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    db.Base.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db.SessionLocal = TestingSessionLocal
    session = TestingSessionLocal()

    saved_adapters = dict(llm.ADAPTERS)
    llm.ADAPTERS["OPENAI"] = GoldenPathFakeEngine()

    try:
        actor = test_support.governed_actor(session, "Golden Path Auditor")
        customer = crud.get_or_create_default_customer(session)

        project = crud.create_project(
            session,
            schemas.ProjectCreate(
                name="Golden Path Validation Project",
                description="End-to-end governed workflow proof.",
                customer_id=customer.id,
            ),
            actor=actor,
        )

        # Stage 1 — Document created / ingested
        os.makedirs("./uploads", exist_ok=True)
        sample_path = "./uploads/golden_remote_work_policy.txt"

        content = (
            "Remote Work Policy.\n"
            "Employees may work remotely up to three days per week.\n"
            "Remote work requires manager approval.\n"
            "All remote work must comply with company security rules."
        )

        with open(sample_path, "w", encoding="utf-8") as f:
            f.write(content)

        document = crud.create_document(
            session,
            project_id=project.id,
            filename="Remote_Work_Policy.txt",
            file_path=sample_path,
            department="HR",
            owner="People Operations",
            actor=actor,
        )

        assert document.status == "INGESTED"

        # Stage 2 — Parse / index
        parsed = ingestion.parse_and_index_document(session, document.id)
        assert parsed is True

        session.refresh(document)
        assert document.status == "PARSED"

        chunks = crud.get_document_chunks(session, document.id)
        assert len(chunks) > 0

        # Stage 3 — Extract candidate assets
        extracted = extraction.extract_knowledge_assets_from_project(session, project.id)
        assert extracted is True

        session.refresh(document)
        assert document.status == "ASSETS_EXTRACTED"

        assets = [
            a for a in crud.get_knowledge_assets(session, project.id)
            if a.document_id == document.id
        ]

        assert len(assets) > 0
        assert assets[0].status == "CANDIDATE"

        # Path B — Governance block: candidate asset must not enter Expert Model
        candidate_model_in = schemas.ExpertModelCreate(
            name="Blocked Candidate Model",
            description="Should fail because asset is not approved.",
            project_id=project.id,
            asset_ids=[assets[0].id],
        )

        try:
            crud.create_expert_model(session, candidate_model_in, actor=actor)
            raise AssertionError("Candidate asset was allowed into Expert Model")
        except ValueError:
            pass

        # Stage 4 — Approve all assets
        for asset in assets:
            crud.update_knowledge_asset(
                session,
                asset_id=asset.id,
                update=schemas.KnowledgeAssetUpdate(status="APPROVED"),
                actor=actor,
            )

        session.refresh(document)
        assert document.status == "APPROVED"

        approved_assets = [
            a for a in crud.get_knowledge_assets(session, project.id)
            if a.document_id == document.id and a.status == "APPROVED"
        ]

        assert len(approved_assets) == len(assets)

        # Stage 5 — Expert Model
        model = crud.create_expert_model(
            session,
            schemas.ExpertModelCreate(
                name="Golden Remote Work Expert",
                description="Approved HR policy knowledge.",
                project_id=project.id,
                asset_ids=[a.id for a in approved_assets],
            ),
            actor=actor,
        )

        assert model.id is not None
        assert model.asset_count > 0

        # Stage 6 — Compile Package
        package = crud.create_agent_package(
            session,
            schemas.AgentPackageCreate(
                name="Golden Remote Work Package",
                project_id=project.id,
                expert_model_id=model.id,
                governance_version="golden-path-1.0",
                clearance_level="INTERNAL",
            ),
            actor=actor,
        )

        assert package.id is not None
        assert package.file_path
        assert os.path.exists(package.file_path)
        assert package.package_hash is not None
        assert package.manifest is not None

        # Stage 7 — Consume Package / Ask Question
        question = "What is the remote work policy?"

        result = package_consumer.consume(
            package.file_path,
            question,
            session=session,
        )

        assert result["answer"]
        assert "remote" in result["answer"].lower()
        assert result["evidence"]
        assert len(result["evidence"]) > 0
        assert result["package"]["package_hash"] == package.package_hash

        # Stage 8 — Evidence / provenance
        first_evidence = result["evidence"][0]

        assert first_evidence["asset_id"] in [a.id for a in approved_assets]
        assert first_evidence["provenance"]
        assert first_evidence["provenance"]["source_document"] == "Remote_Work_Policy.txt"

        # Stage 8b — D30 source class travels through the consumer channel.
        # This is a manually-uploaded primary document, so its evidence must be
        # classified PRIMARY and must never surface as DERIVED. (v1.4.0 WS2 /
        # D30: class travels into every consumer channel.)
        assert "source_class" in first_evidence
        assert first_evidence["source_class"] == "PRIMARY"

        # Stage 9 — Audit ledger exists
        audit_events = crud.get_audit_events(session, limit=100)

        assert len(audit_events) > 0

        event_text = "\n".join(
            f"{e.event_type} {e.details}" for e in audit_events
        )

        assert "DOCUMENT" in event_text.upper()
        assert "ASSET" in event_text.upper() or "KNOWLEDGE" in event_text.upper()
        assert "PACKAGE" in event_text.upper()

    finally:
        llm.ADAPTERS.clear()
        llm.ADAPTERS.update(saved_adapters)
        session.close()


if __name__ == "__main__":
    # Script entry point: the CI harness runs each suite as `python
    # test_*.py` and judges by exit code, so failures must propagate.
    test_golden_path_e2e_approved_package_answer_and_governance_block()
    print("Golden Path E2E: PASSED")
