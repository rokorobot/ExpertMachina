import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ["OPENAI_API_KEY"] = "mock-key"
os.environ.pop("OPENAI_MODEL", None)  # precedence tests own this variable

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database as db
from app import schemas
from app import crud
from app import llm
from app.main import list_llm_settings, update_llm_setting
import test_support

# v0.12.0 resolver precedence suite - the executable form of the central
# invariant (D19 candidate): DB config missing -> OPENAI_MODEL env ->
# gpt-4o-mini default. Empty configuration preserves prior behavior.


def main():
    print("\nInitializing test database for LLM Provider Settings checks...")
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    db.Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db.SessionLocal = TestingSessionLocal  # sessionless resolver calls use this
    session = TestingSessionLocal()
    crud.get_or_create_default_customer(session)
    officer = test_support.governed_actor(session, "GovernanceOfficer")

    # Part 1: empty config + no env = prior behavior, for every function.
    print("\n--- Part 1: Empty config -> gpt-4o-mini default ---")
    for fn in llm.FUNCTIONS:
        r = llm.resolve(fn, session)
        assert r["model"] == "gpt-4o-mini" and r["source"] == "DEFAULT", r
    assert llm.model_for("EXTRACTION") == "gpt-4o-mini", "sessionless path must agree"
    print(f"Part 1 passed: all {len(llm.FUNCTIONS)} functions default to gpt-4o-mini.")

    # Part 2: env var is the middle precedence tier.
    print("\n--- Part 2: OPENAI_MODEL env overrides the default ---")
    os.environ["OPENAI_MODEL"] = "gpt-4o"
    r = llm.resolve("ANSWER_GENERATION", session)
    assert r["model"] == "gpt-4o" and r["source"] == "ENV", r
    print("Part 2 passed: env tier resolves when no config row exists.")

    # Part 3: DB config wins over env; audited with old/new.
    print("\n--- Part 3: Config tier wins; LLM_CONFIG_UPDATED audited ---")
    resp = update_llm_setting("extraction", schemas.LLMFunctionSettingUpdate(
        model="gpt-4.1-mini"), db_session=session, actor=officer)
    assert resp.configured_model == "gpt-4.1-mini" and resp.source == "CONFIG"
    r = llm.resolve("EXTRACTION", session)
    assert r["model"] == "gpt-4.1-mini" and r["source"] == "CONFIG", r
    r2 = llm.resolve("CLAIM_JUDGE", session)
    assert r2["model"] == "gpt-4o" and r2["source"] == "ENV", "Other functions untouched"
    events = session.query(db.AuditEvent).filter(
        db.AuditEvent.event_type == "LLM_CONFIG_UPDATED").all()
    assert len(events) == 1 and events[0].actor == "GovernanceOfficer"
    assert '"old_model": null' in events[0].details and '"new_model": "gpt-4.1-mini"' in events[0].details
    print("Part 3 passed: config wins per-function, change audited with old/new.")

    # Part 4: clearing the model resets the function to env/default.
    print("\n--- Part 4: Clearing resets resolution ---")
    resp = update_llm_setting("EXTRACTION", schemas.LLMFunctionSettingUpdate(
        model=None), db_session=session, actor=officer)
    assert resp.configured_model is None and resp.source == "ENV" and resp.effective_model == "gpt-4o"
    os.environ.pop("OPENAI_MODEL", None)
    r = llm.resolve("EXTRACTION", session)
    assert r["model"] == "gpt-4o-mini" and r["source"] == "DEFAULT", r
    events = session.query(db.AuditEvent).filter(
        db.AuditEvent.event_type == "LLM_CONFIG_UPDATED").all()
    assert len(events) == 2, "Clearing is itself an audited change"
    print("Part 4 passed: clear -> env -> default fallthrough, clear audited.")

    # Part 5: hygiene - unknown function rejected, listing covers all four.
    print("\n--- Part 5: Validation and listing ---")
    try:
        update_llm_setting("SALARY_NEGOTIATION", schemas.LLMFunctionSettingUpdate(model="x"),
                           db_session=session, actor=officer)
        raise AssertionError("Unknown function must be rejected")
    except Exception as e:
        assert "Unknown LLM function" in str(e), str(e)
    listing = list_llm_settings(db_session=session)
    assert {s.function for s in listing} == set(llm.FUNCTIONS)
    assert all(s.provider == "OPENAI" for s in listing)
    print("Part 5 passed: unknown function 400s; listing covers all functions, OPENAI-only.")

    # Part 6: the rule itself - no credential fields anywhere in the model.
    print("\n--- Part 6: Store model selection, never credentials ---")
    columns = {c.name for c in db.LLMFunctionConfig.__table__.columns}
    forbidden = {c for c in columns if "key" in c.lower() or "secret" in c.lower() or "token" in c.lower()}
    assert not forbidden, f"Credential-shaped columns must not exist: {forbidden}"
    print(f"Part 6 passed: columns {sorted(columns)} contain no credential fields.")

    print("\nAll LLM Provider Settings checks passed.")


if __name__ == "__main__":
    main()
