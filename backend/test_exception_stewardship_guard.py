"""v2.0 WS1 - the D32 Exception Stewardship guard (the SEVENTH permanent
guard family), built BEFORE the stewardship door exists.

The law (D32, ratified at the v2.0 WS0 gate):

    The exception never becomes a row; the human decisions about it do.

Exception existence is computed from governed facts at read time,
always. What persists is the human stewardship decision: an
identity-backed, append-only STEWARDSHIP_DECISION AuditEvent keyed to
the exception's stable computed identity. Decisions annotate the queue;
they never decide what is in it.

What this guard freezes, structurally and permanently:

  1. THE ROW SENTINEL - no exception or stewardship table exists; the
     D24 snapshot holds; within backend/app the STEWARDSHIP_DECISION
     event type is written by at most ONE module, only through the one
     governed audit writer, and NOTHING in app/ ever deletes or mutates
     an AuditEvent (append-only is load-bearing, not convention).
  2. THE VOCABULARY SPEC - the seven ratified decision kinds and their
     required fields live HERE as the spec; if/when app/stewardship.py
     exists its vocabulary must equal this spec exactly.
  3. THE KEY-STABILITY PRECONDITION - over a real computed inbox, the
     exception identity (the inbox item id, key_version inbox-item-v1)
     is byte-stable across recomputes and derives from the governed
     fact that produces the exception.
  4. THE EXISTENCE SENTINEL (the D1 drift plant) - the computed item
     set is IDENTICAL with all STEWARDSHIP_DECISION events present vs
     absent (ids, severities, buckets - everything except the future
     `stewardship` annotation); the compile gate verdict is identical
     too (THE SILENT VETO refused: a risk-accepted HIGH still blocks).
  5. THE KNOWLEDGE FINGERPRINT - stewardship writes change zero bytes
     in every governed table except the ledger itself.
  6. STRUCTURAL AGENT REFUSAL - no role an AGENT principal may hold
     carries the stewardship permission (assets:review); the Guard 5
     write-route grid enumerates app.routes dynamically, so the future
     door is swept by construction; the MCP gateway mentions no
     stewardship (agent visibility of stewardship state is the [PMD]
     question, unminted); and THE DOOR-AWARE PART: the moment a
     stewardship route exists, this guard live-refuses an AGENT bearer
     on it with zero guard edits - the guard is waiting for the door.

Adversarially self-proven: a planted stewardship table, a planted
direct event construction (bypassing the audit writer), a planted
AuditEvent mutation/delete, and a planted existence filter (dropping
DISMISSED-decided items) must each be caught - or the guard itself
fails.
"""
import copy
import json
import os
import re
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ.setdefault("OPENAI_API_KEY", "mock-key")

from sqlalchemy import create_engine          # noqa: E402
from sqlalchemy.orm import sessionmaker       # noqa: E402
from app import database as db                # noqa: E402

_tmpdir = tempfile.mkdtemp(prefix="em_guard7_")
db.engine = create_engine(
    f"sqlite:///{os.path.join(_tmpdir, 'guard7.db')}",
    connect_args={"check_same_thread": False})
db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)

from app import ingestion                     # noqa: E402
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_guard7_qdrant_")

from app import schemas, crud, identity, governance_inbox  # noqa: E402
from app import conflict_engine               # noqa: E402
from app.audit import log_audit_event         # noqa: E402
import test_support                           # noqa: E402
import test_workbench_projection              # noqa: E402

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(BACKEND_DIR, "app")

EVENT_TYPE = "STEWARDSHIP_DECISION"
KEY_VERSION = "inbox-item-v1"

# ---------------------------------------------------------------- the spec
# THE RATIFIED DECISION VOCABULARY (D32 companion ruling; v2.0 WS0).
# Closed at seven kinds; kind-specific required fields beside the
# always-required exception_key/exception_type/kind. CLEARED is the
# append-only undo. Current state = latest event per (key, kind).
STEWARDSHIP_KINDS = {
    "ACKNOWLEDGED": (),
    "RISK_ACCEPTED": ("reason",),
    "DISMISSED": ("reason",),
    "ESCALATED": ("reason", "escalated_to"),
    "OWNER_ASSIGNED": ("owner_label",),   # owner_principal_id optional
    "DUE_DATE_SET": ("due_date",),        # YYYY-MM-DD; overdue COMPUTED
    "CLEARED": ("reason", "clears_kind"),
}

# The one module permitted to WRITE the event type (through the audit
# writer only), and the modules permitted to MENTION it read-side (the
# queue join). The router that mounts the door imports the writer
# module; it does not spell the event type itself.
WRITER_MODULE = "stewardship.py"
READ_MODULES = {"stewardship.py", "governance_inbox.py"}

# Tables outside the fingerprint: the ledger is where decisions land BY
# DESIGN; identity_facts because Actor.fact() mints evidence lazily on
# first governed write (pre-minted in the fixture, asserted unchanged
# during stewardship anyway via the count check below).
LEDGER_TABLES = {"audit_events"}


def _iter_app_modules():
    for root, _dirs, files in os.walk(APP_DIR):
        for name in files:
            if name.endswith(".py"):
                path = os.path.join(root, name)
                with open(path, "r", encoding="utf-8") as f:
                    yield os.path.relpath(path, APP_DIR).replace(os.sep, "/"), f.read()


# ----------------------------------------------------------- the checkers
# Pure functions over (relative path, source text) so the adversarial
# plants below can prove each checker catches its violation.

def row_sentinel_violations(rel_path, source):
    """No module may declare an exception/stewardship TABLE, construct a
    STEWARDSHIP_DECISION AuditEvent directly (the audit writer is the
    only pen), or spell the event type outside the ruled modules."""
    findings = []
    base = rel_path.split("/")[-1]
    for match in re.finditer(r"class\s+(\w+)\s*\(\s*(?:db\.)?Base\s*\)", source):
        name = match.group(1).lower()
        if "exception" in name or "stewardship" in name:
            findings.append(f"{rel_path}: governed table '{match.group(1)}' - "
                            f"the exception never becomes a row (D32)")
    if EVENT_TYPE in source:
        if base not in (READ_MODULES | {WRITER_MODULE}):
            findings.append(f"{rel_path}: mentions {EVENT_TYPE} outside the "
                            f"ruled modules {sorted(READ_MODULES)}")
        if "AuditEvent(" in source:
            findings.append(f"{rel_path}: constructs AuditEvent directly "
                            f"beside {EVENT_TYPE} - decisions flow through "
                            f"log_audit_event only")
    return findings


def append_only_violations(rel_path, source):
    """Nothing in app/ deletes or bulk-updates ledger rows. The ledger is
    append-only by LAW now, not by convention - a stewardship 'edit' or
    'retraction' is a new CLEARED event, never a mutation."""
    findings = []
    for pattern, label in ((r"AuditEvent\s*\)\s*\.\s*filter[^\n]*\n?[^\n]*\.delete\s*\(",
                            "deletes AuditEvent rows"),
                           (r"query\s*\(\s*(?:db\.)?AuditEvent[^\n]*\n?[^\n]*\.update\s*\(",
                            "bulk-updates AuditEvent rows")):
        if re.search(pattern, source):
            findings.append(f"{rel_path}: {label} - the ledger is append-only (D32)")
    return findings


def existence_difference(items_a, items_b):
    """The existence comparator: two computed inboxes must present the
    SAME exceptions - same keys, severities, buckets, types - regardless
    of stewardship state. Only the (future) `stewardship` annotation may
    differ. Returns a list of differences (empty = identical)."""
    def strip(items):
        out = []
        for item in items:
            item = {k: v for k, v in item.items() if k != "stewardship"}
            out.append(item)
        return sorted(out, key=lambda i: i["id"])
    a, b = strip(copy.deepcopy(items_a)), strip(copy.deepcopy(items_b))
    diffs = []
    ids_a, ids_b = {i["id"] for i in a}, {i["id"] for i in b}
    for missing in sorted(ids_a - ids_b):
        diffs.append(f"exception {missing} vanished - decisions must never "
                     f"extinguish existence (THE SILENT VETO)")
    for extra in sorted(ids_b - ids_a):
        diffs.append(f"exception {extra} appeared - decisions must never "
                     f"create existence")
    by_a = {i["id"]: i for i in a}
    for item in b:
        if item["id"] in by_a and by_a[item["id"]] != item:
            changed = [k for k in item if by_a[item["id"]].get(k) != item.get(k)]
            diffs.append(f"exception {item['id']} changed {changed} - "
                         f"severity/bucket/facts must not move with stewardship")
    return diffs


def validate_decision(details):
    """The vocabulary spec, enforced: unknown kinds fail loudly; required
    fields are required; the key travels with its version."""
    problems = []
    kind = details.get("kind")
    if kind not in STEWARDSHIP_KINDS:
        problems.append(f"unknown decision kind: {kind!r}")
        return problems
    for field in ("exception_key", "exception_type"):
        if not details.get(field):
            problems.append(f"{kind}: missing {field}")
    if details.get("key_version") != KEY_VERSION:
        problems.append(f"{kind}: key_version must be {KEY_VERSION!r}")
    for field in STEWARDSHIP_KINDS[kind]:
        if not details.get(field):
            problems.append(f"{kind}: missing required field {field!r}")
    if kind == "DUE_DATE_SET" and details.get("due_date"):
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(details["due_date"])):
            problems.append("DUE_DATE_SET: due_date must be YYYY-MM-DD (declared, "
                            "never computed)")
    if kind == "CLEARED" and details.get("clears_kind") not in STEWARDSHIP_KINDS:
        problems.append(f"CLEARED: clears_kind must name a ruled kind")
    return problems


def fingerprint(session, exclude=LEDGER_TABLES):
    """A byte-level fingerprint of every governed table except the ledger:
    stewardship must change NOTHING it is not (the D24-family instrument,
    applied to writes instead of schema)."""
    import hashlib
    h = hashlib.sha256()
    for table in db.Base.metadata.sorted_tables:
        if table.name in exclude:
            continue
        h.update(table.name.encode())
        for row in session.execute(table.select().order_by(*table.primary_key.columns)):
            h.update(repr(tuple(row)).encode())
    return h.hexdigest()


def write_decision(session, actor, fact_id, exception_key, exception_type,
                   kind, **fields):
    """The ratified event shape - what the WS2 door will emit. The guard
    writes it raw at WS1 (the door does not exist yet) to prove the
    sentinels against real ledger bytes."""
    details = {"key_version": KEY_VERSION, "exception_key": exception_key,
               "exception_type": exception_type, "kind": kind, **fields}
    problems = validate_decision(details)
    assert not problems, problems
    return log_audit_event(session, actor=actor, event_type=EVENT_TYPE,
                           target_id=exception_key,
                           details=json.dumps(details),
                           identity_fact_id=fact_id)


# ------------------------------------------------------------- the fixture

def build_fixture(session):
    """A compact REAL computed queue: an unreviewed DIRECT_CONTRADICTION
    (HIGH - blocks the gate), a pending candidate revision (MEDIUM), an
    uncovered CANDIDATE (NOT_COVERED), and a model without evaluations
    (WARNING) - four exception species, four key grammars."""
    officer = test_support.governed_actor(session, "Guard7Officer")
    reviewer = test_support.governed_actor(session, "Guard7Reviewer")
    customer = crud.get_or_create_default_customer(session)
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Guard7", description="the stewardship guard fixture",
        customer_id=customer.id), actor=officer)

    def make_asset(name, content, status="APPROVED"):
        asset = db.KnowledgeAsset(project_id=project.id, name=name,
                                  content=content, type="POLICY",
                                  status=status)
        session.add(asset)
        session.commit()
        session.refresh(asset)
        return asset

    a1 = make_asset("Retention", "Customer contract records must be retained "
                                 "for ten years after contract termination.")
    a2 = make_asset("Disposal", "Customer contract records must be destroyed "
                                "three years after contract termination.")
    held = make_asset("Uncovered candidate", "New supplier onboarding must "
                                             "follow the sourcing process.",
                      status="CANDIDATE")
    model = db.ExpertModel(project_id=project.id, name="Guard7 Expert",
                           asset_ids_json=json.dumps([a1.id, a2.id]),
                           asset_count=2)
    session.add(model)
    session.commit()
    session.refresh(model)
    session.add(db.AssetRelationship(
        project_id=project.id, expert_model_id=model.id,
        source_asset_id=a1.id, target_asset_id=a2.id,
        relationship_type="CONFLICTS_WITH",
        classification="DIRECT_CONTRADICTION", confidence=0.99,
        status="DETECTED", verifier_json=json.dumps({"method": "GUARD_FIXTURE"})))
    session.commit()
    # a pending candidate revision on an approved asset (the divert path)
    crud.update_knowledge_asset(
        session, a1.id,
        schemas.KnowledgeAssetUpdate(
            content="Customer contract records must be retained for eleven "
                    "years after contract termination."),
        actor=reviewer, review_notes="guard7: candidate revision")
    return project, model, reviewer


def main():
    db.init_db()
    session = db.SessionLocal()

    # ------------------------------------------------------------ Part 1
    print("\n--- Part 1: THE ROW SENTINEL (structural, adversarially proven) ---")
    live = {t.name: sorted(c.name for c in t.columns)
            for t in db.Base.metadata.sorted_tables}
    assert live == test_workbench_projection.FROZEN_SCHEMA, \
        "schema drifted - D32 adds NO table, NO column"
    tables, columns = len(live), sum(len(c) for c in live.values())
    assert (tables, columns) == (28, 305), (tables, columns)
    for name in live:
        low = name.lower()
        assert "exception" not in low and "stewardship" not in low, \
            f"table {name}: the exception never becomes a row"
    swept = 0
    for rel_path, source in _iter_app_modules():
        v = row_sentinel_violations(rel_path, source)
        assert not v, "\n".join(v)
        swept += 1
    assert swept >= 40, f"module sweep looks broken: {swept} modules"
    # the checker catches its plants - or this guard is decoration:
    plant_table = "class StewardshipException(Base):\n    __tablename__ = 'x'\n"
    assert row_sentinel_violations("app/plant.py", plant_table), \
        "self-proof FAILED: planted stewardship table not caught"
    plant_direct = (f"event = db.AuditEvent(event_type='{EVENT_TYPE}')\n")
    assert row_sentinel_violations("app/stewardship.py", plant_direct), \
        "self-proof FAILED: planted direct event construction not caught"
    assert row_sentinel_violations("app/rogue.py", f"x = '{EVENT_TYPE}'"), \
        "self-proof FAILED: planted out-of-module mention not caught"
    print(f"Part 1 passed: D24 at {tables}/{columns}, no exception-shaped "
          f"table; {swept} app modules swept; all three row-sentinel plants "
          f"caught.")

    # ------------------------------------------------------------ Part 2
    print("\n--- Part 2: append-only is law, not convention ---")
    for rel_path, source in _iter_app_modules():
        v = append_only_violations(rel_path, source)
        assert not v, "\n".join(v)
    plant_delete = ("session.query(db.AuditEvent).filter(\n"
                    "    db.AuditEvent.event_type == 'X').delete()\n")
    assert append_only_violations("app/plant.py", plant_delete), \
        "self-proof FAILED: planted ledger delete not caught"
    plant_update = ("session.query(db.AuditEvent).filter(x)\\\n"
                    "    .update({'details': 'rewritten'})\n")
    assert append_only_violations("app/plant.py", plant_update), \
        "self-proof FAILED: planted ledger update not caught"
    # the vocabulary spec is enforceable and closed:
    assert len(STEWARDSHIP_KINDS) == 7
    assert validate_decision({"kind": "INVENTED"}), "unknown kind must fail"
    assert validate_decision({"kind": "RISK_ACCEPTED", "exception_key": "K",
                              "exception_type": "T", "key_version": KEY_VERSION}), \
        "missing reason must fail"
    assert not validate_decision({"kind": "DUE_DATE_SET", "exception_key": "K",
                                  "exception_type": "T",
                                  "key_version": KEY_VERSION,
                                  "due_date": "2026-08-01"})
    stew_path = os.path.join(APP_DIR, "stewardship.py")
    if os.path.isfile(stew_path):
        from app import stewardship as stew_mod
        assert {k: tuple(v) for k, v in stew_mod.STEWARDSHIP_KINDS.items()} == \
            {k: tuple(v) for k, v in STEWARDSHIP_KINDS.items()}, \
            "app/stewardship.py vocabulary drifted from the ratified spec"
        mode = "module present - vocabulary equals the ratified spec"
    else:
        mode = "the door does not exist yet (WS1) - this guard IS the spec"
    print(f"Part 2 passed: no ledger mutation anywhere in app/; both "
          f"append-only plants caught; the seven-kind vocabulary closed and "
          f"enforced ({mode}).")

    # ------------------------------------------------------------ Part 3
    print("\n--- Part 3: THE KEY-STABILITY PRECONDITION (real inbox) ---")
    project, model, reviewer = build_fixture(session)
    runs = [governance_inbox.build_inbox(session, project.id) for _ in range(3)]
    id_sets = [[i["id"] for i in sorted(r["items"], key=lambda x: x["id"])]
               for r in runs]
    assert id_sets[0] == id_sets[1] == id_sets[2], \
        "exception identity must be byte-stable across recomputes"
    keys = set(id_sets[0])
    grammars = {k.split("-", 1)[0] for k in keys}
    assert {"CONFLICT", "REVISION", "INGESTION_EXCEPTION", "WARNING"} <= grammars, \
        f"the fixture must exercise four key grammars: {grammars}"
    for key in keys:
        assert re.fullmatch(r"[A-Z_]+-[A-Za-z0-9_.-]+", key), \
            f"key {key!r} breaks the inbox-item-v1 grammar"
    rel = session.query(db.AssetRelationship).filter_by(
        project_id=project.id).first()
    assert f"CONFLICT-{rel.id}" in keys, \
        "the key must derive from the governed fact that produces the exception"
    print(f"Part 3 passed: {len(keys)} computed exceptions, identical ids "
          f"across 3 recomputes, four key grammars, keys derived from "
          f"governed identities ({KEY_VERSION}).")

    # ------------------------------------------------------------ Part 4
    print("\n--- Part 4: THE EXISTENCE SENTINEL + D2 severity honesty ---")
    fact_id = reviewer.fact(session).id      # minted BEFORE the fingerprint
    before_items = governance_inbox.build_inbox(session, project.id)["items"]
    gate_before = conflict_engine.evaluate_compile_gate(session, model.id)
    assert not gate_before["allowed"], \
        "the fixture's unreviewed contradiction must block the gate"
    high_key = next(i["id"] for i in before_items if i["severity"] == "HIGH")
    held_key = next(i["id"] for i in before_items
                    if i["type"] == "INGESTION_EXCEPTION")
    fp_before = fingerprint(session)
    facts_before = session.query(db.IdentityFact).count()

    actor_name = reviewer.principal.name
    write_decision(session, actor_name, fact_id, high_key, "CONFLICT",
                   "ACKNOWLEDGED")
    write_decision(session, actor_name, fact_id, high_key, "CONFLICT",
                   "RISK_ACCEPTED", reason="Accepted until the retention "
                   "policy harmonization lands next quarter.")
    write_decision(session, actor_name, fact_id, high_key, "CONFLICT",
                   "OWNER_ASSIGNED", owner_label="Records Management")
    write_decision(session, actor_name, fact_id, high_key, "CONFLICT",
                   "DUE_DATE_SET", due_date="2026-09-30")
    write_decision(session, actor_name, fact_id, held_key,
                   "INGESTION_EXCEPTION", "DISMISSED",
                   reason="Duplicate of the sourcing-process candidate.")
    write_decision(session, actor_name, fact_id, held_key,
                   "INGESTION_EXCEPTION", "ESCALATED",
                   reason="Owner unresponsive.", escalated_to="Procurement lead")
    write_decision(session, actor_name, fact_id, held_key,
                   "INGESTION_EXCEPTION", "CLEARED",
                   reason="Escalation resolved at standup.",
                   clears_kind="ESCALATED")
    written = session.query(db.AuditEvent).filter_by(
        event_type=EVENT_TYPE).count()
    assert written == 7, "all seven ratified kinds exercised on the ledger"

    after_items = governance_inbox.build_inbox(session, project.id)["items"]
    diffs = existence_difference(before_items, after_items)
    assert not diffs, "THE EXISTENCE SENTINEL:\n" + "\n".join(diffs)
    gate_after = conflict_engine.evaluate_compile_gate(session, model.id)
    assert gate_after == gate_before, \
        "THE SILENT VETO: a risk-accepted HIGH must still block the gate"
    sev_after = {i["id"]: i["severity"] for i in after_items}
    assert sev_after[high_key] == "HIGH", "severity must not move (D2)"
    # the comparator catches its plant - a 'dismiss filter' is the drift bug:
    filtered = [i for i in after_items if i["id"] != held_key]
    assert existence_difference(before_items, filtered), \
        "self-proof FAILED: the existence comparator missed a dropped item"
    print(f"Part 4 passed: 7 decisions (all kinds) on the ledger; the "
          f"computed queue is IDENTICAL with decisions present vs absent; "
          f"the gate verdict unchanged; severity unchanged; the planted "
          f"existence filter caught.")

    # ------------------------------------------------------------ Part 5
    print("\n--- Part 5: THE KNOWLEDGE FINGERPRINT ---")
    fp_after = fingerprint(session)
    assert fp_after == fp_before, \
        "stewardship wrote outside the ledger - D32 violated"
    assert session.query(db.IdentityFact).count() == facts_before, \
        "stewardship must reuse the actor's minted fact, not fabricate more"
    for event in session.query(db.AuditEvent).filter_by(
            event_type=EVENT_TYPE).all():
        assert event.identity_fact_id == fact_id, \
            "every decision carries the deciding human's identity fact"
        details = json.loads(event.details)
        assert not validate_decision(details), "ledger bytes obey the spec"
        assert event.target_id == details["exception_key"]
    print("Part 5 passed: every governed table byte-identical through 7 "
          "stewardship writes; every decision identity-backed and "
          "spec-valid on its ledger bytes.")

    # ------------------------------------------------------------ Part 6
    print("\n--- Part 6: STRUCTURAL AGENT REFUSAL (door-aware) ---")
    for role in identity.ALLOWED_ROLES_BY_KIND["AGENT"]:
        perms = identity.ROLE_PERMISSIONS[role]
        assert "assets:review" not in perms, \
            f"AGENT-permitted role {role} holds the stewardship permission"
        assert perms == frozenset({"mcp:consume"}), \
            f"AGENT-permitted role {role} grew beyond mcp:consume: {perms}"
    with open(os.path.join(APP_DIR, "mcp_gateway.py"), encoding="utf-8") as f:
        gateway_src = f.read()
    assert "STEWARDSHIP" not in gateway_src.upper(), \
        "the MCP gateway mentions stewardship - agent visibility is [PMD], unminted"
    import test_route_manifest as route_guard
    assert route_guard.digest(route_guard.build_manifest()) == \
        route_guard.FROZEN_DIGEST, "route manifest drifted outside its guard"
    from app import main
    stewardship_routes = [
        (m, r.path) for r in main.app.routes
        if "stewardship" in getattr(r, "path", "")
        for m in (getattr(r, "methods", None) or ())]
    if not stewardship_routes:
        door = ("the door does not exist yet (WS1) - Guard 5's grid "
                "enumerates app.routes dynamically and will sweep it the "
                "moment WS2 mounts it")
    else:
        from fastapi.testclient import TestClient
        agent = identity.create_principal(session, name="guard7-agent",
                                          display_name="Guard7 Agent",
                                          kind="AGENT", clearance="INTERNAL",
                                          created_by="guard7")
        token, _c = identity.issue_token(session, agent, kind="API_TOKEN",
                                         label="guard7", actor="guard7")
        client = TestClient(main.app)
        for method, path in stewardship_routes:
            if method in ("GET", "HEAD", "OPTIONS"):
                continue
            live_path = re.sub(r"\{[^}]+\}", "1", path)
            resp = client.request(method, live_path,
                                  headers={"Authorization": f"Bearer {token}"},
                                  json={})
            assert resp.status_code == 403, \
                f"AGENT not refused on {method} {live_path}: {resp.status_code}"
        door = (f"{len(stewardship_routes)} stewardship route(s) present - "
                f"AGENT bearer refused 403 on every write, live")
    print(f"Part 6 passed: no AGENT-permitted role can hold assets:review; "
          f"the gateway is stewardship-silent (9 frozen tools untouched); "
          f"route manifest matches its guard; {door}.")

    session.close()
    print("\n=== All D32 exception-stewardship guard checks passed: the "
          "exception never becomes a row (no table, no column, no second "
          "state machine), the human decisions about it do (append-only, "
          "identity-backed, spec-valid ledger events), existence and "
          "severity move ONLY with governed facts, and no agent can hold "
          "the stewardship pen - all adversarially self-proven, before the "
          "door exists. ===")


if __name__ == "__main__":
    main()
