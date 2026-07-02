import ast
import json
import os
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ["EM_NLI_VERIFICATION"] = "off"
# Deterministic rule-based extraction: the sentinel depends on stable
# asset names and types, never on an LLM.
os.environ["OPENAI_API_KEY"] = "mock-key"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database as db

# GUARD 5 - the D29/D30 structural guard (v1.4.0 WS0,
# docs/diagnostic-workbench-v1.4.md). The fifth permanent guard family,
# built BEFORE any workbench code exists, guarding the way
# test_workbench_projection.py guards D24, test_credential_custody.py
# guards D25, test_ingestion_automation_guard.py guards D26, and
# test_projection_guard.py guards D28.
#
# D29 (The One-Way Valve): agent outputs cannot become canonical facts
# directly. No agent principal, workbench result, diagnostic output, or
# MCP/tool return can write APPROVED knowledge or any canonical fact
# state - agent findings re-enter ONLY through the proposal lane
# (PROPOSAL-lane connector -> CANDIDATE -> human gate). Proposal-lane
# candidates are never auto-approved: no policy tier applies to them;
# the human gate on agent-proposed knowledge is constitutional, not
# configurable. The valve constrains agents, not people.
#
# D30 (Derived Source Class): the source class is decided by the
# ingestion channel, never claimed by document content - the only
# permitted writer of KnowledgeAsset.source_class is the allowlisted
# channel-derivation path.
#
# The guard adversarially self-proves every checker: planted violations
# (a write-capable MCP tool, a widened AGENT role, an auto-approval of a
# proposal-lane candidate, a frontmatter-decided source class, a direct
# APPROVED write from workbench code, a proposal colliding with a
# PRIMARY asset's identity, fake provenance trusted without governed
# verification) must all be caught - or the guard itself fails.

# File-based DB with db.SessionLocal pointed at it BEFORE app imports:
# the async Tier-2 pass owns its own session (D4) and must see this
# data - never the dev database.
_tmpdir = tempfile.mkdtemp(prefix="em_authorship_")
db.engine = create_engine(f"sqlite:///{os.path.join(_tmpdir, 'guard.db')}",
                          connect_args={"check_same_thread": False})
db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db.engine)

from app import ingestion
ingestion.QDRANT_DIR = tempfile.mkdtemp(prefix="em_authorship_qdrant_")

from app import schemas  # noqa: E402
from app import crud  # noqa: E402
from app import connectors  # noqa: E402
from app import identity  # noqa: E402
from app import policy  # noqa: E402
from app import tier2  # noqa: E402
import test_support  # noqa: E402

APP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app")
REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKBENCH_DIR = os.path.join(REPO_DIR, "workbench")

# The only modules permitted to write KnowledgeAsset.source_class (D30:
# channel decides class). database.py holds the column default;
# proposals.py is WS1's channel-derivation module - named here BEFORE it
# exists so the sweep covers it the moment it lands. Any other writer is
# a second author of the class, whatever it calls itself.
SOURCE_CLASS_WRITERS = {"database.py", "proposals.py"}

# WS3's workbench modules may import ONLY the ruled doors: stdlib, the
# package consumer (itself purity-guarded: stdlib + the llm seam), the
# llm seam it rides on, and the MCP client SDK. A workbench that can
# reach the database, CRUD, routes, or identity is an internal
# privileged subsystem - exactly what D29 forbids it to become.
WORKBENCH_ALLOWED_IMPORTS = {"app.package_consumer", "app.llm", "mcp"}

# Write routes that must remain reachable WITHOUT an authorized actor:
# the authentication surface itself (D20: it is how identity is
# established, not a governed knowledge write).
AUTH_SURFACE = {"/api/auth/login", "/api/auth/logout", "/api/auth/change-password"}

SYSTEM_SENTENCE = "The scheduling platform stores shift rosters in a PostgreSQL database server."
SYSTEM_SENTENCE_VARIANT = "The scheduling platform stores shift rosters in a MariaDB database server."
POLICY_SENTENCE = "All contractors must sign the security addendum before badge issuance."


def _stdlib_names():
    return set(sys.stdlib_module_names)


def _parents(tree):
    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    return parents


def _call_name(node):
    if isinstance(node, ast.Call):
        f = node.func
        return f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None)
    return None


def _governed_model_names():
    """Discovered from the live registry (the D28 guard pattern): a class
    list that cannot go stale as the schema evolves."""
    return {mapper.class_.__name__ for mapper in db.Base.registry.mappers}


# ---------------------------------------------------------------- Part 1
# The frozen powerlessness: an agent's REST inertness is structure.

def powerlessness_violations(allowed_roles_by_kind, role_permissions):
    """AGENT principals are kind-locked to AGENT_CONSUMER, which holds
    exactly {mcp:consume}. Any widening is a second door opening."""
    violations = []
    agent_roles = set(allowed_roles_by_kind.get("AGENT", set()))
    if agent_roles != {"AGENT_CONSUMER"}:
        violations.append(
            f"AGENT kind may hold roles {sorted(agent_roles)} - the kind-role "
            f"lock must be exactly {{'AGENT_CONSUMER'}}")
    for role in agent_roles:
        perms = set(role_permissions.get(role, set()))
        if perms != {"mcp:consume"}:
            violations.append(
                f"role {role} holds {sorted(perms)} - an agent-reachable role "
                f"must hold exactly {{'mcp:consume'}}")
    return violations


def part_1_powerlessness():
    print("\n--- Part 1: AGENT powerlessness is frozen structure (D29) ---")
    violations = powerlessness_violations(
        identity.ALLOWED_ROLES_BY_KIND, identity.ROLE_PERMISSIONS)
    assert not violations, (
        "D29 violation - the agent's structural powerlessness has widened:\n  "
        + "\n  ".join(violations))
    print("Part 1 passed: AGENT -> AGENT_CONSUMER -> exactly {mcp:consume}.")


# ---------------------------------------------------------------- Part 2
# The MCP surface writes nothing (structural sweep + frozen tool list).

MCP_MODULES = ["mcp_gateway.py"]


def mcp_write_violations(module_name, source, governed_models):
    """Forbidden shapes in the agent-facing gateway: any hit is a write
    door opening on the consumption channel."""
    tree = ast.parse(source)
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Attribute) and target.attr in (
                        "status", "source_class", "lane", "domain"):
                    violations.append(
                        f"{module_name}:{node.lineno} writes governed "
                        f"attribute .{target.attr}")
        ctor = _call_name(node)
        if ctor in governed_models:
            violations.append(
                f"{module_name}:{node.lineno} constructs governed model {ctor}")
        if ctor == "update_knowledge_asset":
            violations.append(
                f"{module_name}:{node.lineno} calls the approval transition path")
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr in ("add", "add_all", "delete", "merge")
                and isinstance(node.func.value, ast.Name)
                and "session" in node.func.value.id.lower()):
            violations.append(
                f"{module_name}:{node.lineno} mutates the session "
                f"(.{node.func.attr})")
        if (isinstance(node, ast.keyword) and node.arg in ("event_type", "audit_event_type")
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
                and node.value.value.startswith(("ASSET_APPROVED", "ASSET_AUTO_APPROVED"))):
            violations.append(
                f"{module_name}:{node.lineno} emits an approval event family")
    return violations


def part_2_mcp_surface():
    print("\n--- Part 2: the MCP surface writes nothing (D29) ---")
    governed_models = _governed_model_names()
    for module_name in MCP_MODULES:
        with open(os.path.join(APP_DIR, module_name), "r", encoding="utf-8") as f:
            source = f.read()
        violations = mcp_write_violations(module_name, source, governed_models)
        assert not violations, (
            "D29 violation - the MCP surface is growing a write door:\n  "
            + "\n  ".join(violations))
    # The frozen tool surface: nine read-only tools (ratified at v1.3
    # WS3). This list changes ONLY alongside a ratified decision, in the
    # same commit - and never grows a write tool under any ruling short
    # of superseding D29 itself.
    import asyncio
    import mcp_server
    tools = asyncio.run(mcp_server.mcp.list_tools())
    names = sorted(t.name for t in tools)
    assert names == ["ask_expert", "check_gate_status", "get_conflicts",
                     "get_domain_subgraph", "get_graph_neighbors",
                     "get_lineage_path", "get_provenance",
                     "get_revision_history", "get_trust_score"], \
        f"Unexpected MCP tool surface: {names}"
    print(f"Part 2 passed: {MCP_MODULES} clean; tool surface frozen at "
          f"{len(names)} read-only tools.")


# ---------------------------------------------------------------- Part 3
# Every write route refuses an AGENT token, and the refusal is loud.

def part_3_rest_grid():
    print("\n--- Part 3: every write route refuses an AGENT token (D29) ---")
    from fastapi.testclient import TestClient
    from fastapi.routing import APIRoute
    from app import main

    with TestClient(main.app) as client:
        with db.SessionLocal() as boot:
            admin = identity.create_principal(
                boot, name="guard-admin", display_name="Guard Admin",
                kind="HUMAN", role="ADMIN", created_by="test-suite")
            identity.set_password(boot, admin, "guard-admin-password-1", actor="test-suite")
            agent = identity.create_principal(
                boot, name="workbench-agent", display_name="Workbench Agent",
                kind="AGENT", created_by="test-suite")
            agent_token, _cred = identity.issue_token(
                boot, agent, kind="API_TOKEN", label="guard", actor="test-suite")
        AGENT = {"Authorization": f"Bearer {agent_token}"}

        write_routes = []
        for route in main.app.routes:
            if not isinstance(route, APIRoute):
                continue
            methods = route.methods & {"POST", "PUT", "PATCH", "DELETE"}
            if not methods or route.path in AUTH_SURFACE:
                continue
            for method in sorted(methods):
                write_routes.append((method, route.path))
        assert len(write_routes) >= 25, (
            f"Sanity: the route sweep found only {len(write_routes)} write "
            f"routes - the enumeration itself may be broken")

        refused_403 = 0
        for method, path in write_routes:
            url = path
            for token in ("{id}", "{project_id}", "{asset_id}", "{revision_id}",
                          "{conflict_id}", "{policy_id}", "{connector_id}",
                          "{job_id}", "{document_id}", "{expert_id}",
                          "{package_id}", "{binding_id}", "{credential_id}",
                          "{question_id}", "{run_id}", "{principal_name}",
                          "{name}", "{token_id}"):
                url = url.replace(token, "1")
            # Any residual parameter placeholder becomes "1" as well.
            while "{" in url:
                start, end = url.index("{"), url.index("}")
                url = url[:start] + "1" + url[end + 1:]
            r = client.request(method, url, json={}, headers=AGENT)
            assert r.status_code < 200 or r.status_code >= 300, (
                f"D29 violation: {method} {url} returned {r.status_code} "
                f"to an AGENT token - a write route accepted an agent")
            if r.status_code == 403:
                refused_403 += 1
        # The refusal must be the boundary speaking (403 from the actor
        # resolver: AGENT tokens are MCP-only on REST), not accidental
        # 404/422 shielding.
        assert refused_403 == len(write_routes), (
            f"Only {refused_403}/{len(write_routes)} write routes refused "
            f"the AGENT with 403 - the rest got past the identity boundary "
            f"before being stopped by something weaker")
        print(f"Part 3 passed: {len(write_routes)} write routes, "
              f"{refused_403} explicit 403 refusals, zero 2xx.")


# ---------------------------------------------------------------- Part 4
# D30 structural: the only writer of source_class is the channel.

def source_class_violations(rel_name, source):
    """Any assignment of source_class outside the allowlisted
    channel-derivation path is a second author of the class - including
    the frontmatter-decided class D30 explicitly forbids."""
    tree = ast.parse(source)
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Attribute) and target.attr == "source_class":
                    violations.append(
                        f"{rel_name}:{node.lineno} assigns .source_class")
        if isinstance(node, ast.keyword) and node.arg == "source_class":
            violations.append(
                f"{rel_name}:{node.lineno} passes source_class= to a call")
    return violations


def write_schema_violations(source):
    """schemas.py: no write-shaped schema (Create/Update) may carry a
    source_class field - the class is never caller-supplied (D30)."""
    tree = ast.parse(source)
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name.endswith(("Create", "Update")):
            for item in node.body:
                target = None
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    target = item.target.id
                elif isinstance(item, ast.Assign) and isinstance(item.targets[0], ast.Name):
                    target = item.targets[0].id
                if target == "source_class":
                    violations.append(
                        f"schemas.py:{item.lineno} write schema {node.name} "
                        f"accepts source_class")
    return violations


def part_4_class_is_channel_decided():
    print("\n--- Part 4: only the channel writes source_class (D30) ---")
    all_violations = []
    for root, _dirs, files in os.walk(APP_DIR):
        for fname in files:
            if not fname.endswith(".py"):
                continue
            path = os.path.join(root, fname)
            rel = os.path.relpath(path, APP_DIR).replace(os.sep, "/")
            if rel in SOURCE_CLASS_WRITERS:
                continue
            with open(path, "r", encoding="utf-8") as f:
                all_violations.extend(source_class_violations(rel, f.read()))
    assert not all_violations, (
        "D30 violation - a second author of source_class:\n  "
        + "\n  ".join(all_violations))
    with open(os.path.join(APP_DIR, "schemas.py"), "r", encoding="utf-8") as f:
        schema_violations = write_schema_violations(f.read())
    assert not schema_violations, (
        "D30 violation - source_class is caller-suppliable:\n  "
        + "\n  ".join(schema_violations))
    print(f"Part 4 passed: no writer outside {sorted(SOURCE_CLASS_WRITERS)}; "
          f"no write schema accepts the class.")


# ---------------------------------------------------------------- Part 5
# Workbench isolation: a reference consumer, never a subsystem.

def workbench_import_violations(rel_name, source):
    """Workbench modules may import only the ruled doors. Reaching the
    database, CRUD, routes, or identity makes the workbench an internal
    privileged subsystem - D29 forbids exactly that."""
    stdlib = _stdlib_names()
    tree = ast.parse(source)
    violations = []

    def check(module_path, lineno):
        if not module_path:
            return
        top = module_path.split(".")[0]
        if top in stdlib:
            return
        if module_path in WORKBENCH_ALLOWED_IMPORTS:
            return
        if any(module_path.startswith(allowed + ".")
               for allowed in WORKBENCH_ALLOWED_IMPORTS):
            return
        violations.append(
            f"{rel_name}:{lineno} imports {module_path} - workbench doors "
            f"are {sorted(WORKBENCH_ALLOWED_IMPORTS)} + stdlib only")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                check(alias.name, node.lineno)
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                continue  # relative imports stay inside workbench/
            module = node.module or ""
            if module == "app":
                # `from app import X` resolves per name: only the ruled
                # doors may come through the bare package.
                for alias in node.names:
                    check(f"app.{alias.name}", node.lineno)
            else:
                check(module, node.lineno)
    return violations


def part_5_workbench_isolation():
    print("\n--- Part 5: workbench is a consumer, never a subsystem (D29) ---")
    # Direction one: the governed app never imports workbench code.
    offenders = []
    for root, _dirs, files in os.walk(APP_DIR):
        for fname in files:
            if not fname.endswith(".py"):
                continue
            path = os.path.join(root, fname)
            rel = os.path.relpath(path, APP_DIR).replace(os.sep, "/")
            with open(path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""]
                for name in names:
                    if name == "workbench" or name.startswith("workbench."):
                        offenders.append(f"{rel}:{node.lineno} imports {name}")
    assert not offenders, (
        "D29 violation - the governed app depends on workbench code:\n  "
        + "\n  ".join(offenders))
    # Direction two: workbench modules (the moment they exist) import
    # only the ruled doors.
    swept = 0
    if os.path.isdir(WORKBENCH_DIR):
        for root, _dirs, files in os.walk(WORKBENCH_DIR):
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                path = os.path.join(root, fname)
                rel = os.path.relpath(path, REPO_DIR).replace(os.sep, "/")
                with open(path, "r", encoding="utf-8") as f:
                    violations = workbench_import_violations(rel, f.read())
                assert not violations, (
                    "D29 violation - the workbench reached past its doors:\n  "
                    + "\n  ".join(violations))
                swept += 1
    print(f"Part 5 passed: app imports no workbench code; "
          f"{swept} workbench module(s) swept against the ruled doors.")


# ---------------------------------------------------------------- Part 6
# Provenance is verified, never trusted (structural tripwire; the full
# functional proof is the WS1 gate).

def provenance_trust_violations(rel_name, source):
    """A module that marks proposal provenance verified must have
    consulted the governed record (ExpertAgentBinding). Marking it from
    content alone is 'the agent said so' - the exact shallowness the
    opening question forbids."""
    tree = ast.parse(source)
    marks_verified = False
    for node in ast.walk(tree):
        if (isinstance(node, ast.keyword) and node.arg == "provenance_verified"
                and isinstance(node.value, ast.Constant) and node.value.value is True):
            marks_verified = True
        if (isinstance(node, ast.Constant) and node.value == "provenance_verified"):
            marks_verified = True
    if marks_verified and "ExpertAgentBinding" not in source:
        return [f"{rel_name}: marks provenance verified without consulting "
                f"ExpertAgentBinding - provenance trusted from content"]
    return []


def part_6_provenance_tripwire():
    print("\n--- Part 6: provenance verified, never trusted (D30 tripwire) ---")
    all_violations = []
    for root, _dirs, files in os.walk(APP_DIR):
        for fname in files:
            if not fname.endswith(".py"):
                continue
            path = os.path.join(root, fname)
            rel = os.path.relpath(path, APP_DIR).replace(os.sep, "/")
            with open(path, "r", encoding="utf-8") as f:
                all_violations.extend(provenance_trust_violations(rel, f.read()))
    assert not all_violations, (
        "D30 violation - provenance trusted from the claim:\n  "
        + "\n  ".join(all_violations))
    print("Part 6 passed: no module marks provenance verified without the "
          "governed record (WS1's proposals.py is covered the moment it lands).")


# ---------------------------------------------------------------- Part 7
# THE LANE SENTINEL (end-to-end): under the most permissive policy
# environment constructible, a proposal-lane candidate still holds.

def write_file(folder, name, *sentences):
    path = os.path.join(folder, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(sentences) + "\n")
    return path


def run_scan(session, connector):
    job = db.IngestionJob(project_id=connector.project_id,
                          connector_id=connector.id, status="PENDING")
    session.add(job)
    session.commit()
    session.refresh(job)
    connectors.execute_ingestion_job(session, job.id)
    # The sentinel's guarantee is "after ALL background tasks complete" -
    # drain the async Tier-2 pass before judging anything.
    tier2.drain()
    session.refresh(job)
    assert job.status == "COMPLETED", f"{job.status} / {job.error}"
    return job


def lane_violations(session, project_id):
    """The sentinel's detector: every way an agent proposal could have
    become canonical without a human."""
    lane_doc_ids = policy.proposal_lane_document_ids(
        session, [d.id for d in session.query(db.Document).filter_by(
            project_id=project_id).all()])
    violations = []
    # (a) No auto-approval event may target a proposal-lane asset.
    for e in session.query(db.AuditEvent).filter_by(
            event_type="ASSET_AUTO_APPROVED").all():
        asset = session.query(db.KnowledgeAsset).filter_by(
            id=int(e.target_id)).first() if e.target_id else None
        if asset is not None and asset.document_id in lane_doc_ids:
            violations.append(
                f"ASSET_AUTO_APPROVED event {e.id} targets proposal-lane "
                f"asset {asset.id}")
    # (b) No APPROVED proposal-lane asset without a human review row.
    approved = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.project_id == project_id,
        db.KnowledgeAsset.status == "APPROVED",
        db.KnowledgeAsset.document_id.in_(lane_doc_ids or {-1})).all()
    for asset in approved:
        human_reviews = [r for r in asset.reviews
                         if r.approver and not r.approver.startswith("policy:")]
        if not human_reviews:
            violations.append(
                f"proposal-lane asset {asset.id} is APPROVED with no human "
                f"review row")
    return violations


class ApproveEverythingVerifier:
    """The most permissive engine constructible: it finds NO
    contradiction in anything. Even under it, a proposal-lane candidate
    must hold - a clean engine verdict cannot carry agent-proposed
    knowledge past the human gate (D29)."""
    identity = {"method": "GUARD_APPROVE_EVERYTHING",
                "note": "adversarial lane-sentinel seam"}

    def check(self, candidate, corpus):
        return {"pairs_checked": len(corpus), "pairs_dropped": 0,
                "contradictions": []}


def part_7_lane_sentinel():
    print("\n--- Part 7: THE LANE SENTINEL - the most permissive policy "
          "environment cannot approve a proposal (D29) ---")
    session = db.SessionLocal()
    tier2.verifier_factory = ApproveEverythingVerifier

    customer = crud.get_or_create_default_customer(session)
    officer = test_support.governed_actor(session, "GovernanceOfficer")
    project = crud.create_project(session, schemas.ProjectCreate(
        name="Lane Sentinel", description="D29 guard", customer_id=customer.id),
        actor=officer)

    primary_folder = tempfile.mkdtemp(prefix="em_authorship_primary_")
    proposal_folder = tempfile.mkdtemp(prefix="em_authorship_proposal_")
    primary = db.SourceConnector(project_id=project.id, name="Primary Share",
                                 type="LOCAL_FOLDER", root_path=primary_folder,
                                 include_extensions=".txt")
    proposal = db.SourceConnector(project_id=project.id, name="Proposal Lane",
                                  type="LOCAL_FOLDER", root_path=proposal_folder,
                                  include_extensions=".txt", lane="PROPOSAL")
    session.add_all([primary, proposal])
    session.commit()
    session.refresh(primary)
    session.refresh(proposal)

    # The most permissive policy set constructible - built as raw rows,
    # deliberately bypassing API validation (an adversary would too).
    # Critically: every policy is GLOBAL (connector_id NULL) - the exact
    # configuration hole D29's sentinel exists to close, since global
    # policies apply to every connector including the proposal lane.
    all_types = json.dumps(sorted(policy.ALLOWED_ASSET_TYPES))
    session.add_all([
        db.ApprovalPolicy(project_id=project.id, name="everything-tier1",
                          asset_types_json=all_types, enabled=True),
        db.ApprovalPolicy(project_id=project.id, name="everything-conditions",
                          asset_types_json=all_types, enabled=True,
                          source_conditions_json="[]",
                          engine_conditions_json="{}"),
        db.ApprovalPolicy(project_id=project.id, name="everything-tier2",
                          asset_types_json=all_types, enabled=True,
                          engine_conditions_json=json.dumps(
                              {"contradiction_check": "CLEAN_REQUIRED"})),
    ])
    session.commit()

    # Arm the sentinel: the permissive set must actually auto-approve on
    # the PRIMARY lane (a sentinel over machinery that approves nothing
    # proves nothing).
    write_file(primary_folder, "handbook.txt", SYSTEM_SENTENCE, POLICY_SENTENCE)
    run_scan(session, primary)
    armed = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.project_id == project.id,
        db.KnowledgeAsset.type == "SYSTEM",
        db.KnowledgeAsset.status == "APPROVED").first()
    assert armed is not None, \
        "Sentinel not armed: the permissive policy set must auto-approve PRIMARY"
    assert armed.source_class == "PRIMARY", \
        f"WS0 default must be PRIMARY, got {armed.source_class!r}"

    # The adversarial act: an agent-style finding lands in the proposal
    # lane - same content species the primary lane just auto-approved.
    write_file(proposal_folder, "finding-0001.txt",
               SYSTEM_SENTENCE_VARIANT, POLICY_SENTENCE)
    run_scan(session, proposal)

    lane_doc_ids = policy.proposal_lane_document_ids(
        session, [d.id for d in session.query(db.Document).filter_by(
            project_id=project.id).all()])
    assert lane_doc_ids, "The proposal scan must have produced lane documents"
    proposal_assets = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.project_id == project.id,
        db.KnowledgeAsset.document_id.in_(lane_doc_ids)).all()
    assert proposal_assets, "The proposal document must have produced candidates"
    for asset in proposal_assets:
        assert asset.status == "CANDIDATE", (
            f"D29 violation: proposal-lane asset {asset.id} is "
            f"{asset.status} after all background tasks - the human gate "
            f"was bypassed")

    violations = lane_violations(session, project.id)
    assert not violations, (
        "D29 violation - an agent proposal became canonical:\n  "
        + "\n  ".join(violations))

    # The hold is DECLARED, never silent (D12): both tiers' summary
    # events name the held candidates.
    held_ids = {a.id for a in proposal_assets}
    tier1_events = [json.loads(e.details) for e in session.query(db.AuditEvent)
                    .filter_by(event_type="POLICY_AUTOAPPROVAL_COMPLETED").all()]
    declared_tier1 = {i for d in tier1_events
                      for i in d.get("proposal_lane_held_ids", [])}
    assert held_ids <= declared_tier1, (
        f"Tier-1 hold not declared: {held_ids - declared_tier1}")
    tier2_events = [json.loads(e.details) for e in session.query(db.AuditEvent)
                    .filter_by(event_type="POLICY_TIER2_COMPLETED").all()]
    assert any(d.get("engine_available") for d in tier2_events), \
        "The Tier-2 pass must have run under the approve-everything engine"
    declared_tier2 = {i for d in tier2_events
                      for i in d.get("proposal_lane_held_ids", [])}
    assert held_ids <= declared_tier2, (
        f"Tier-2 hold not declared: {held_ids - declared_tier2}")

    # The valve constrains agents, not people: a HUMAN can approve the
    # held candidate through the ordinary governed gate. (The POLICY-type
    # candidate is chosen so Part 7c's SYSTEM-type collision set stays
    # entirely CANDIDATE.)
    target = next(a for a in proposal_assets if a.type != armed.type)
    reviewer = test_support.governed_actor(session, "LaneReviewer")
    crud.update_knowledge_asset(
        session, target.id, schemas.KnowledgeAssetUpdate(status="APPROVED"),
        actor=reviewer, review_notes="human accepted at the gate")
    session.refresh(target)
    assert target.status == "APPROVED", "The human gate must remain open to humans"
    assert not lane_violations(session, project.id), \
        "A human acceptance must not read as a valve violation"

    print(f"Part 7 passed: {len(proposal_assets)} proposal candidate(s) held "
          f"under 3 global policies + a live approve-everything Tier-2 "
          f"engine; holds declared by both tiers; the human gate stays open.")

    # Part 7b - sentinel self-proof: simulate the catastrophe (an
    # automation pass approves a proposal candidate) and assert the
    # detector fires; restore and re-assert clean.
    print("\n--- Part 7b: lane-sentinel self-proof (simulated auto-approved "
          "proposal) ---")
    victim = next(a for a in proposal_assets if a.id != target.id) \
        if len(proposal_assets) > 1 else target
    saved_status = victim.status
    victim.status = "APPROVED"
    session.commit()
    crud.log_audit_event(
        session, actor="policy:everything-tier1",
        event_type="ASSET_AUTO_APPROVED", target_id=str(victim.id),
        details=json.dumps({"simulated": "guard self-proof"}))
    caught = lane_violations(session, project.id)
    assert caught, ("Self-proof FAILED: the detector missed a simulated "
                    "auto-approved proposal")
    session.query(db.AuditEvent).filter_by(
        event_type="ASSET_AUTO_APPROVED",
        target_id=str(victim.id)).delete()
    victim.status = saved_status
    session.commit()
    assert not lane_violations(session, project.id)
    print(f"Part 7b passed: simulated violation caught ({len(caught)} "
          f"finding(s)), clean after restore.")

    # Part 7c - cross-lane identity collision: a proposal engineered to
    # collide by (type, name) with the approved PRIMARY asset must
    # become a NEW candidate, never a candidate revision of trusted
    # content (D7 reconciliation is connector-scoped - asserted, not
    # assumed).
    print("\n--- Part 7c: cross-lane identity collision (D29) ---")
    session.refresh(armed)
    primary_revisions_before = len(armed.revisions)
    primary_content_before = armed.content
    write_file(proposal_folder, "finding-0002.txt", SYSTEM_SENTENCE)
    run_scan(session, proposal)
    session.refresh(armed)
    assert armed.content == primary_content_before, \
        "D29 violation: a proposal changed trusted PRIMARY content"
    assert len(armed.revisions) == primary_revisions_before, \
        "D29 violation: a proposal reached the PRIMARY asset's revision machinery"
    colliding = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.project_id == project.id,
        db.KnowledgeAsset.type == armed.type,
        db.KnowledgeAsset.name == armed.name,
        db.KnowledgeAsset.id != armed.id).all()
    assert colliding and all(a.status == "CANDIDATE" for a in colliding), (
        "The colliding proposal must exist as its own held CANDIDATE")
    print(f"Part 7c passed: collision produced a new held candidate; the "
          f"PRIMARY asset's content and revision history are untouched.")
    session.close()


# ---------------------------------------------------------------- Part 8
# Adversarial self-proof: every structural checker catches its plant.

PLANT_MCP_WRITE_TOOL = """
def approve_asset(session, asset_id):
    asset = session.query(db.KnowledgeAsset).filter_by(id=asset_id).first()
    asset.status = "APPROVED"
    session.add(db.AssetReview(asset_id=asset_id, approver="agent:mcp"))
"""

PLANT_MCP_TRANSITION_CALL = """
def approve_asset(session, asset_id):
    crud.update_knowledge_asset(session, asset_id,
        schemas.KnowledgeAssetUpdate(status="APPROVED"), actor=actor)
"""

PLANT_FRONTMATTER_CLASS = """
def classify(asset, frontmatter):
    asset.source_class = frontmatter.get("source_class", "PRIMARY")
"""

PLANT_CLASS_KEYWORD = """
def build(session, doc):
    session.add(db.KnowledgeAsset(name="x", type="POLICY", content="y",
                                  source_class="PRIMARY"))
"""

PLANT_WRITE_SCHEMA = """
class KnowledgeAssetUpdate(BaseModel):
    status: str | None = None
    source_class: str | None = None
"""

PLANT_WORKBENCH_CRUD = """
import sys
from app import crud
from app import database as db

def finish(session, asset_id):
    crud.update_knowledge_asset(session, asset_id, status="APPROVED")
"""

PLANT_WORKBENCH_CLEAN = """
import json
import sys
from app import package_consumer
from mcp import ClientSession
"""

PLANT_PROVENANCE_TRUSTED = """
def verify(frontmatter):
    return {"provenance_verified": True, "binding_id": frontmatter["binding_id"]}
"""

PLANT_PROVENANCE_CLEAN = """
def verify(session, frontmatter):
    binding = session.query(db.ExpertAgentBinding).filter_by(
        id=frontmatter["binding_id"]).first()
    if binding is None:
        return {"provenance_verified": False}
    return {"provenance_verified": True}
"""


def part_8_self_proof():
    print("\n--- Part 8: adversarial self-proof (planted violations) ---")
    governed_models = _governed_model_names()

    # Plant 1-2: a write-capable MCP tool (direct write + transition call).
    assert mcp_write_violations("planted.py", PLANT_MCP_WRITE_TOOL, governed_models), \
        "Self-proof FAILED: the MCP sweep missed a write-capable tool"
    assert mcp_write_violations("planted.py", PLANT_MCP_TRANSITION_CALL, governed_models), \
        "Self-proof FAILED: the MCP sweep missed a transition-path call"

    # Plant 3: a widened AGENT role (both widening shapes).
    widened_kind = dict(identity.ALLOWED_ROLES_BY_KIND)
    widened_kind["AGENT"] = {"AGENT_CONSUMER", "KNOWLEDGE_OPERATOR"}
    assert powerlessness_violations(widened_kind, identity.ROLE_PERMISSIONS), \
        "Self-proof FAILED: a widened kind-role lock was missed"
    widened_perms = dict(identity.ROLE_PERMISSIONS)
    widened_perms["AGENT_CONSUMER"] = frozenset({"mcp:consume", "assets:approve"})
    assert powerlessness_violations(identity.ALLOWED_ROLES_BY_KIND, widened_perms), \
        "Self-proof FAILED: a widened permission set was missed"

    # Plant 4: the frontmatter-decided class + caller-supplied class.
    assert source_class_violations("planted.py", PLANT_FRONTMATTER_CLASS), \
        "Self-proof FAILED: a frontmatter-decided source class was missed"
    assert source_class_violations("planted.py", PLANT_CLASS_KEYWORD), \
        "Self-proof FAILED: a source_class constructor keyword was missed"
    assert write_schema_violations(PLANT_WRITE_SCHEMA), \
        "Self-proof FAILED: a caller-suppliable source_class field was missed"

    # Plant 5: a workbench module reaching past its doors; the canonical
    # clean shape passes.
    assert workbench_import_violations("workbench/planted.py", PLANT_WORKBENCH_CRUD), \
        "Self-proof FAILED: a workbench CRUD import was missed"
    assert not workbench_import_violations("workbench/planted.py", PLANT_WORKBENCH_CLEAN), \
        "Self-proof sanity: the ruled doors must pass the sweep"

    # Plant 6: provenance trusted from content; the governed-verification
    # shape passes.
    assert provenance_trust_violations("planted.py", PLANT_PROVENANCE_TRUSTED), \
        "Self-proof FAILED: content-trusted provenance was missed"
    assert not provenance_trust_violations("planted.py", PLANT_PROVENANCE_CLEAN), \
        "Self-proof sanity: governed verification must pass the sweep"

    # (Plant 7 - the auto-approved proposal and the PRIMARY-identity
    # collision - is functional and proven live in Parts 7b/7c.)
    print("Part 8 passed: every structural plant caught; canonical clean "
          "shapes stay clean.")


# ---------------------------------------------------------------- Part 9
# WS0 schema self-check: the atomic commit carries its own evidence.

def part_9_schema():
    print("\n--- Part 9: v1.4.0 WS0 schema present (D29/D30) ---")
    asset_col = db.KnowledgeAsset.__table__.c.source_class
    assert not asset_col.nullable and asset_col.server_default is not None, \
        "D30: source_class must be NOT NULL DEFAULT 'PRIMARY'"
    lane_col = db.SourceConnector.__table__.c.lane
    assert not lane_col.nullable and lane_col.server_default is not None, \
        "D29/D30: lane must be NOT NULL DEFAULT 'PRIMARY'"
    print("Part 9 passed: source_class and lane present, NOT NULL, "
          "defaulting to PRIMARY (snapshot updated to 28 tables / 305 "
          "columns in test_workbench_projection.py, same commit).")


def main():
    db.init_db()
    part_1_powerlessness()
    part_2_mcp_surface()
    part_3_rest_grid()
    part_4_class_is_channel_decided()
    part_5_workbench_isolation()
    part_6_provenance_tripwire()
    part_7_lane_sentinel()
    part_8_self_proof()
    part_9_schema()
    print("\nAll D29/D30 agent-authorship guard checks passed: agents are "
          "structurally powerless outside MCP, the MCP surface writes "
          "nothing, proposal-lane candidates hold under the most permissive "
          "policy environment constructible, the class is channel-decided, "
          "the workbench stays outside its doors - all adversarially "
          "self-proven.")


if __name__ == "__main__":
    main()
