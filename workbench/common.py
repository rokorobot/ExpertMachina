"""Shared workbench runner plumbing (v1.7 WS2, ruling 6 - the catalog's
first reuse moment).

The v1.6 Customer Operations runner proved the pattern: a workbench is a
consumer, never a subsystem (D22), reaching the governed system ONLY through
the doors - the .empkg via app.package_consumer, the MCP gateway as a real
client at a real AGENT token's clearance, and file writes into the vault.
This module extracts the parts that are workbench-AGNOSTIC so a second
workbench (Compliance & Obligation) reuses them instead of copying:

  - door setup (import_package_consumer);
  - contract loading + ACTIVE gating (load_skill_contract,
    load_active_contracts) - tags are gates, not preferences;
  - the inherited v1.6 evidence-rule helpers (same-subject discipline);
  - the MCP stdio door (StdioMcpGraphClient);
  - content-hashed, timestamp-free proposal writing (write_hashed).

Stdlib-ONLY and doors-only, under the Guard 5-swept `workbench/` root: Guard
5 Part 5 sweeps this module automatically the moment it exists (stdlib +
app.package_consumer + app.llm + mcp), with zero guard edits. Narration,
finding kinds, proposed actions, and the detection walk stay in each
runner - they are the workbench's product, not shared plumbing.
"""
import hashlib
import os
import re
import sys


def import_package_consumer(backend_dir=None):
    """The .empkg door. Locates app.package_consumer via EM_BACKEND_DIR when
    the runner executes outside the backend directory."""
    backend_dir = backend_dir or os.environ.get("EM_BACKEND_DIR")
    if backend_dir and backend_dir not in sys.path:
        sys.path.append(backend_dir)
    from app import package_consumer
    return package_consumer


# ------------------------------------------------------------- text helpers

def tokens(text):
    # Deliberately keeps 2-char tokens: the corpus lesson - numbers
    # ("30", "14", "24", "48") often carry the whole difference between
    # two policy statements.
    return {t for t in re.findall(r"[a-z0-9]+", (text or "").lower())
            if len(t) >= 2}


def overlap(a, b):
    return len(tokens(a) & tokens(b))


def excerpt(text, limit=200):
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[:limit].rstrip() + "..."


# ----------------------------------------------- the inherited evidence rules
# The declared same-subject rule (ratified at the v1.6 WS3 gate, inherited
# wholesale by v1.7 ruling 9): a cross-document contradiction requires the two
# statements to share SUBJECT MATTER, not merely parallel timeframe structure
# ("within N days/hours") - the NLI engine over-fires on different-topic
# timeframe sentences. Subject tokens are alphabetic, length >= 4, excluding
# the timeframe vocabulary. Governance vocabulary is not subject matter (every
# governed statement is approved).
TIMEFRAME_STOPWORDS = frozenset((
    "within", "business", "days", "hours", "must", "shall", "every",
    "each", "during", "receive", "request", "requests", "target",
    "response", "working", "calendar", "month", "months", "year",
    "approved", "approval",
))
SAME_SUBJECT_MINIMUM = 2


def subject_tokens(text):
    return {t for t in re.findall(r"[a-z]+", (text or "").lower())
            if len(t) >= 4 and t not in TIMEFRAME_STOPWORDS}


def shared_subject(a, b):
    return len(subject_tokens(a) & subject_tokens(b))


# ------------------------------------------------- contract loading + gating

def load_skill_contract(skills_dir, skill_id):
    """Minimal line-based read of one ratified contract (stdlib only - the
    doors allow no YAML library): skill_id, status, boundary tags, and the
    question_frame entries (with wrapped-line joining)."""
    path = os.path.join(skills_dir, f"{skill_id}.yaml")
    if not os.path.isfile(path):
        raise RuntimeError(f"Skill contract missing: {path}")
    contract = {"skill_id": None, "status": None, "boundary_tags": None,
                "questions": [], "path": path}
    with open(path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    in_frame = False
    current = None
    for line in lines:
        if line.startswith("skill_id:"):
            contract["skill_id"] = line.split(":", 1)[1].strip()
        elif line.startswith("status:"):
            contract["status"] = line.split(":", 1)[1].strip()
        elif line.startswith("boundary_tags:"):
            contract["boundary_tags"] = line.split(":", 1)[1].strip()
        elif line.startswith("question_frame:"):
            in_frame = True
        elif in_frame:
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if stripped.startswith("- "):
                if current is not None:
                    contract["questions"].append(current)
                current = stripped[2:].strip().strip('"')
            elif line.startswith("    ") and current is not None:
                current = current.rstrip('"') + " " + stripped.rstrip('"')
            else:
                if current is not None:
                    contract["questions"].append(current)
                    current = None
                in_frame = False
    if current is not None:
        contract["questions"].append(current)
    contract["questions"] = [" ".join(q.split()) for q in contract["questions"]]
    if contract["skill_id"] != skill_id:
        raise RuntimeError(f"{path}: skill_id mismatch ({contract['skill_id']})")
    return contract


def load_active_contracts(skills_dir, active_skills):
    """Load the declared ACTIVE skills, refusing any whose contract is not
    status: ACTIVE. Tags are gates, not preferences - a SEQUENCED or gated
    contract is refused at runtime, naming the unminted decision through its
    own status. Returns {skill_id: contract}."""
    contracts = {}
    for skill_id in active_skills:
        contract = load_skill_contract(skills_dir, skill_id)
        if contract["status"] != "ACTIVE":
            raise RuntimeError(
                f"Skill {skill_id} is {contract['status']}, not ACTIVE - "
                f"tags are gates, not preferences; the runner refuses.")
        contracts[skill_id] = contract
    return contracts


# ------------------------------------------------------------- the MCP door

class StdioMcpGraphClient:
    """The real MCP door: a stdio client session against
    backend/mcp_server.py authenticated by EM_AGENT_TOKEN in the server's
    environment. The CI gate injects an in-process substitute that resolves
    the same token through the same gateway functions."""

    def __init__(self, python_exe, server_path, env=None, cwd=None):
        self._params = dict(command=python_exe, args=[server_path],
                            env=env, cwd=cwd)

    def _call(self, tool, arguments):
        import asyncio
        import json
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        async def _run():
            server = StdioServerParameters(**self._params)
            async with stdio_client(server) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool, arguments)
                    return json.loads(result.content[0].text)
        return asyncio.run(_run())

    def get_conflicts(self, expert_model_id):
        return self._call("get_conflicts", {"expert_model_id": expert_model_id})

    def get_revision_history(self, asset_id):
        return self._call("get_revision_history", {"asset_id": asset_id})

    def get_domain_subgraph(self, project_id, domain_prefix):
        return self._call("get_domain_subgraph",
                          {"project_id": project_id,
                           "domain_prefix": domain_prefix})


# ------------------------------------------------- content-hashed vault write

def write_hashed(path_dir, name_stub, content):
    """Write `content` to a content-hash-named, timestamp-free file (the
    determinism discipline: identical content -> identical path -> byte
    identical re-runs). Returns the path."""
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]
    path = os.path.join(path_dir, f"{name_stub}-{digest}.md")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    return path
