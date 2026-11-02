"""v2.5.0 WS1 - D33 The Structured Refusal: the contract, the format rule,
and the adversarial fixtures (no runner change).

Part 1: parse_answer_status over adversarial fixtures - including the
        real-model shapes that broke lexical detection (a scoped refusal
        with the marker mid-text, a refusal with no marker at all, an
        answer that merely mentions the marker).
Part 2: a freshly built package declares empkg-v1.1 and compiles the
        status-line answering policy; its hash chain verifies.
Part 3: a legacy empkg-v1 package still loads and is read LEGACY_LEXICAL
        (D12 - no backfill).
"""
import os
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ.setdefault("OPENAI_API_KEY", "mock-key")
os.environ["EM_PACKAGE_DIR"] = tempfile.mkdtemp(prefix="empkg_d33_test_")

from sqlalchemy import create_engine          # noqa: E402
from sqlalchemy.orm import sessionmaker       # noqa: E402

from app import database as db                # noqa: E402
from app import schemas, crud, package_builder, package_consumer   # noqa: E402
import test_support                           # noqa: E402
from test_package_consumer import make_asset, make_handmade_package   # noqa: E402

V11 = "empkg-v1.1"
REFUSAL = ("INSUFFICIENT EVIDENCE - this question is outside the governed "
           "knowledge of this expert package.")

# The real-model shapes (v2.4.1 runs, Anthropic claude-opus-5-5),
# abridged verbatim from the recorded evidence.
REAL_SCOPED_REFUSAL = (  # run 5: context first, marker mid-text
    "# Enterprise Refund Exceptions\n\nThe governed assets require enterprise "
    "refund exceptions to follow a specific playbook, but **they do not "
    "contain the playbook's steps.**\n\nFor the step-by-step procedure:\n\n"
    "**" + REFUSAL + "**")
REAL_MARKERLESS_REFUSAL = (  # run 8: refused in substance, no marker
    "# Enterprise Refund Exceptions\n\nThe governed assets establish only "
    "that a playbook and documented approval are required. **They do not "
    "contain the playbook's actual steps.**")
REAL_MENTION = (  # run 1: answered, marker mentioned in a limitations note
    "Enterprise refund exceptions are governed by the **enterprise refund "
    "exception playbook** [asset_id 37]. For its steps: " + REFUSAL)


def status(answer, fmt=V11):
    return package_consumer.parse_answer_status(answer, fmt)


def expect(answer, want_status, want_source, want_scope=None, fmt=V11):
    got = status(answer, fmt)
    assert got["answer_status"] == want_status, (answer[:80], got)
    assert got["status_source"] == want_source, (answer[:80], got)
    assert got["refused_scope"] == want_scope, (answer[:80], got)


def part1():
    print("\n--- Part 1: the status line, over the adversarial fixtures ---")
    # The three declared statuses.
    expect("STATUS: ANSWERED\nStaff evacuate immediately [asset_id 1].",
           "ANSWERED", "HEADER")
    expect("STATUS: REFUSED\n" + REFUSAL, "REFUSED", "HEADER")
    expect("STATUS: PARTIAL\nREFUSED_SCOPE: the playbook's steps and who "
           "approves\nThe playbook is named [asset_id 37].",
           "PARTIAL", "HEADER", "the playbook's steps and who approves")
    # Markdown dressing and case are not content.
    expect("  **STATUS: refused**\n\n" + REFUSAL, "REFUSED", "HEADER")
    expect("# STATUS: PARTIAL\n\n**REFUSED_SCOPE:** the steps\nNamed only.",
           "PARTIAL", "HEADER", "the steps")
    # D33: the header decides, never the prose. An ANSWERED header with a
    # mid-text marker is an answer; a REFUSED header needs no marker.
    expect("STATUS: ANSWERED\n" + REAL_MENTION, "ANSWERED", "HEADER")
    expect("STATUS: REFUSED\nThe assets do not cover this.", "REFUSED", "HEADER")
    # Missing or malformed header => UNDETERMINED, never guessed - this
    # includes every real-model shape that has no status line.
    for bad in (REAL_SCOPED_REFUSAL, REAL_MARKERLESS_REFUSAL, REAL_MENTION,
                REFUSAL, "", None,
                "STATUS: MAYBE\nunclear",                  # unknown status
                "STATUS: PARTIAL\nThe playbook is named.",  # PARTIAL, no scope
                "STATUS: PARTIAL\nREFUSED_SCOPE:   \nx",     # empty scope
                "Preamble first.\nSTATUS: ANSWERED\nx",      # not the first line
                "STATUS: ANSWERED and also REFUSED\nx"):     # not a clean line
        expect(bad, "UNDETERMINED", "UNDETERMINED")
    # Legacy packages keep the shipped substring rule, labelled - this is
    # exactly the behavior D33 retires for v1.1 (documented, not fixed).
    expect(REAL_SCOPED_REFUSAL, "REFUSED", "LEGACY_LEXICAL", fmt="empkg-v1")
    expect(REAL_MENTION, "REFUSED", "LEGACY_LEXICAL", fmt="empkg-v1")
    expect(REAL_MARKERLESS_REFUSAL, "ANSWERED", "LEGACY_LEXICAL", fmt="empkg-v1")
    expect("STATUS: REFUSED\n" + REFUSAL, "REFUSED", "LEGACY_LEXICAL", fmt=None)
    print("Part 1 passed: 3 declared statuses + dressing; the header decides, "
          "never the prose; 11 malformed/missing shapes (incl. the three "
          "real-model ones) UNDETERMINED; legacy read LEGACY_LEXICAL.")


def part2_and_3():
    print("\n--- Part 2: a fresh package declares empkg-v1.1 + the status-line policy ---")
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    db.Base.metadata.create_all(bind=engine)
    db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = db.SessionLocal()
    customer = crud.get_or_create_default_customer(session)
    qa = test_support.governed_actor(session, "qa")
    project = crud.create_project(session, schemas.ProjectCreate(
        name="D33", description="WS1", customer_id=customer.id), actor=qa)
    doc = crud.create_document(session, project_id=project.id, filename="S.txt",
                               file_path="uploads/s.txt", actor=qa)
    a = make_asset(session, project, doc, "Evacuation Protocol",
                   "During thermal runaway, evacuate the battery hall immediately.", 0)
    model = crud.create_expert_model(session, schemas.ExpertModelCreate(
        name="D33 Expert", description="", project_id=project.id,
        asset_ids=[a.id]), actor=qa)
    pkg = crud.create_agent_package(session, schemas.AgentPackageCreate(
        name="D33 Expert", project_id=project.id, expert_model_id=model.id,
        governance_version="1.0", clearance_level="INTERNAL"), actor=qa)
    loaded = package_consumer.load_package(pkg.file_path)
    assert package_builder.PACKAGE_FORMAT_VERSION == V11
    assert loaded["manifest"]["package_format"] == V11, loaded["manifest"]
    policy = loaded["instructions"]
    for required in ("STATUS: ANSWERED", "STATUS: REFUSED", "STATUS: PARTIAL",
                     "REFUSED_SCOPE: ", "D33", REFUSAL.split(" - ")[0]):
        assert required in policy, required
    assert "reply exactly" not in policy, "the v1 rule 3 wording must be gone"
    print("Part 2 passed: built package declares empkg-v1.1, its hash chain "
          "verifies, and the compiled policy carries the three-status line.")

    print("\n--- Part 3: a legacy empkg-v1 package still loads, read LEGACY_LEXICAL ---")
    legacy = make_handmade_package(os.path.join(tempfile.mkdtemp(), "legacy.empkg"),
                                   gate="PASSED")
    old = package_consumer.load_package(legacy)
    fmt = old["manifest"]["package_format"]
    assert fmt == "empkg-v1", fmt
    assert status(REFUSAL, fmt)["status_source"] == "LEGACY_LEXICAL"
    session.close()
    print("Part 3 passed: the empkg-v1 package verifies unchanged and its "
          "answers are labelled LEGACY_LEXICAL - no backfill.")


def main():
    part1()
    part2_and_3()
    print("\n=== v2.5.0 WS1 passed: D33's contract, format rule, and "
          "adversarial fixtures hold - before any runner change. ===")


if __name__ == "__main__":
    main()
