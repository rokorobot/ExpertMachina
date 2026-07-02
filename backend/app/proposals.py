from sqlalchemy.orm import Session

from app import database as db
from app import policy

# The proposal lane (v1.4.0 WS1, D29/D30 - docs/diagnostic-workbench-v1.4.md).
#
# D29 (The One-Way Valve): agent findings re-enter governed knowledge
# ONLY as proposal documents through a PROPOSAL-lane connector, held as
# CANDIDATEs for the human gate. D30 (Derived Source Class): what an
# accepted proposal becomes is a DERIVED fact - and the class is decided
# by the ingestion channel, never claimed by document content.
#
# This module is the ONE allowlisted writer of KnowledgeAsset.source_class
# (enforced by test_agent_authorship_guard.py Part 4 - any other writer
# fails CI), and the ONE place proposal synthesis provenance is verified.
# The disciplines:
#
#   - Channel decides class: assign_source_classes derives DERIVED from
#     SourceConnector.lane through the document's scan rows. Frontmatter
#     claiming a class is recorded verbatim as a claim and ignored as a
#     decision (a proposal claiming PRIMARY is still DERIVED).
#   - Provenance is verified, never trusted: a proposal's frontmatter
#     PROPOSES its provenance (agent principal, binding, package hash,
#     cited evidence); verification checks every claim against governed
#     records - the binding must exist, belong to the claimed principal,
#     and match the claimed package hash; the principal must be an
#     active AGENT. "The agent said so" is never a verification.
#   - Nothing is persisted (D1): verification is recomputed at read time
#     (the inbox) and at approval time (quoted verbatim in the approval
#     event). The proposal document itself is the immutable evidence -
#     the frontmatter lives inside the content-hashed document.
#   - Language (D26/D29 rulings): unverifiable provenance is "held for
#     review", never "rejected by the engine".
#
# Frontmatter contract (the /00_system vault contract documents this for
# agents at WS3): the proposal document begins with a '---' line,
# followed by 'key: value' lines, closed by a '---' line:
#
#   ---
#   em_proposal: 1
#   agent_principal: <AGENT principal name>
#   binding_id: <ExpertAgentBinding id>
#   package_hash: <the bound package hash>
#   workbench: <workbench name>          (optional)
#   cited_assets: <id>,<id>,...          (optional - the governed
#                                         evidence the finding drew from)
#   ---
#
# Unknown keys are recorded as unrecognized claims, never fatal (D12:
# the verdict declares what it saw). A document without frontmatter has
# claimed no provenance - honestly unverifiable, held for review.

FRONTMATTER_DELIMITER = "---"
RECOGNIZED_KEYS = {"em_proposal", "agent_principal", "binding_id",
                   "package_hash", "workbench", "cited_assets"}


def assign_source_classes(session: Session, project_id: int,
                          document_ids: list) -> dict:
    """D30: the channel-derivation pass - assets extracted from
    PROPOSAL-lane documents become DERIVED. Idempotent (re-scans and
    changed-file re-extractions converge on the same class); everything
    else keeps the PRIMARY default. Returns a declared summary."""
    summary = {
        "documents_considered": len(document_ids or []),
        "proposal_lane_documents": 0,
        "assets_marked_derived": 0,
    }
    lane_doc_ids = policy.proposal_lane_document_ids(session, document_ids or [])
    summary["proposal_lane_documents"] = len(lane_doc_ids)
    if not lane_doc_ids:
        return summary
    assets = session.query(db.KnowledgeAsset).filter(
        db.KnowledgeAsset.project_id == project_id,
        db.KnowledgeAsset.document_id.in_(lane_doc_ids),
    ).order_by(db.KnowledgeAsset.id).all()
    for asset in assets:
        if asset.source_class != "DERIVED":
            asset.source_class = "DERIVED"
            summary["assets_marked_derived"] += 1
    session.commit()
    return summary


def parse_frontmatter(text: str) -> dict:
    """Parse the proposal frontmatter block. Returns
    {claimed: bool, claims: {...verbatim...}, unrecognized: [...],
    problems: [...]} - a record of what the document PROPOSES, never a
    decision about anything."""
    result = {"claimed": False, "claims": {}, "unrecognized": [], "problems": []}
    lines = (text or "").splitlines()
    if not lines or lines[0].strip() != FRONTMATTER_DELIMITER:
        return result
    body, closed = [], False
    for line in lines[1:]:
        if line.strip() == FRONTMATTER_DELIMITER:
            closed = True
            break
        body.append(line)
    if not closed:
        result["problems"].append("frontmatter block never closed")
        return result
    result["claimed"] = True
    for line in body:
        if not line.strip():
            continue
        if ":" not in line:
            result["problems"].append(f"unparseable line: {line.strip()!r}")
            continue
        key, value = line.split(":", 1)
        key, value = key.strip(), value.strip()
        result["claims"][key] = value
        if key not in RECOGNIZED_KEYS:
            result["unrecognized"].append(key)
    return result


def _document_head(session: Session, document_id: int) -> str:
    """The document's opening text, from the stored content-hashed file
    (ingestion copies source bytes into the upload store and hashes
    them - the file IS the immutable evidence the frontmatter lives in;
    chunk text flattens line structure and cannot carry a frontmatter
    block). A missing or binary file yields no parseable frontmatter -
    honestly nothing claimed, never reconstructed."""
    document = session.query(db.Document).filter(
        db.Document.id == document_id).first()
    if document is None or not document.file_path:
        return ""
    try:
        with open(document.file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(65536)
    except OSError:
        return ""


def verify_provenance(session: Session, document_id: int) -> dict:
    """D30: verify a proposal document's claimed synthesis provenance
    against governed records. Every check that fails is a declared
    reason; provenance_verified is True only when the claimed binding
    exists, belongs to the claimed principal, matches the claimed
    package hash, and the principal is an active AGENT. Computed, never
    stored - recompute at every gate."""
    parsed = parse_frontmatter(_document_head(session, document_id))
    verdict = {
        "document_id": document_id,
        "provenance_claimed": parsed["claimed"],
        "provenance_verified": False,
        "reasons": list(parsed["problems"]),
        "claimed": parsed["claims"],          # verbatim, always
        "unrecognized_keys": parsed["unrecognized"],
        "verified": None,
        "cited_assets": None,
    }
    if not parsed["claimed"]:
        verdict["reasons"].append("no provenance claimed - the document has "
                                  "no proposal frontmatter")
        return verdict
    claims = parsed["claims"]

    binding = None
    binding_raw = claims.get("binding_id", "")
    if not binding_raw:
        verdict["reasons"].append("binding_id not claimed")
    else:
        try:
            binding = session.query(db.ExpertAgentBinding).filter(
                db.ExpertAgentBinding.id == int(binding_raw)).first()
        except ValueError:
            verdict["reasons"].append(f"binding_id {binding_raw!r} is not an id")
        else:
            if binding is None:
                verdict["reasons"].append(
                    f"binding {binding_raw} does not exist in governed records")

    principal = None
    if binding is not None:
        principal = session.query(db.Principal).filter(
            db.Principal.id == binding.agent_principal_id).first()
        claimed_principal = claims.get("agent_principal", "")
        if principal is None:
            verdict["reasons"].append("the binding's principal no longer resolves")
        else:
            if principal.name != claimed_principal:
                verdict["reasons"].append(
                    f"binding {binding.id} belongs to principal "
                    f"{principal.name!r}, not the claimed {claimed_principal!r}")
            if principal.kind != "AGENT":
                verdict["reasons"].append(
                    f"principal {principal.name!r} is {principal.kind}, not AGENT")
            if not principal.active:
                verdict["reasons"].append(
                    f"principal {principal.name!r} is deactivated")
        claimed_hash = claims.get("package_hash", "")
        if claimed_hash != binding.package_hash:
            verdict["reasons"].append(
                f"claimed package_hash does not match binding {binding.id}'s "
                f"governed coordinates")

    # Cited governed evidence: existence checked, absences declared
    # (D12). The citations make derivation depth computable - the
    # anti-inbreeding measure.
    cited_raw = claims.get("cited_assets", "")
    if cited_raw:
        cited, malformed = [], []
        for token in cited_raw.split(","):
            token = token.strip()
            if not token:
                continue
            try:
                cited.append(int(token))
            except ValueError:
                malformed.append(token)
        found = {a.id: a.source_class for a in session.query(db.KnowledgeAsset)
                 .filter(db.KnowledgeAsset.id.in_(cited or [-1])).all()}
        verdict["cited_assets"] = {
            "claimed": cited,
            "found": sorted(found),
            "missing": sorted(set(cited) - set(found)),
            "malformed": malformed,
            # second-generation synthesis is visible at the gate
            "derived_evidence": sorted(i for i, c in found.items()
                                       if c == "DERIVED"),
        }

    if not verdict["reasons"]:
        verdict["provenance_verified"] = True
        verdict["verified"] = {
            "binding_id": binding.id,
            "agent_principal": principal.name,
            "agent_principal_id": principal.id,
            "agent_package_id": binding.agent_package_id,
            "package_hash": binding.package_hash,
            "package_version": binding.package_version,
            "selected_provider": binding.selected_provider,
            "selected_model_name": binding.selected_model_name,
            "binding_identity_fact_id": binding.identity_fact_id,
        }
    return verdict


def proposal_verdicts(session: Session, document_ids: list) -> dict:
    """Verification verdicts for the PROPOSAL-lane documents among
    document_ids, keyed by document id. Non-lane documents are absent -
    they claim nothing and need nothing."""
    lane_doc_ids = policy.proposal_lane_document_ids(session, document_ids or [])
    return {doc_id: verify_provenance(session, doc_id)
            for doc_id in sorted(lane_doc_ids)}


def approval_provenance(session: Session, asset) -> dict:
    """The synthesis provenance quoted at the human gate: the
    verification verdict recomputed against governed records at approval
    time. Six months later, 'which agent synthesized this, under which
    binding, from which package, citing what - and did the records
    vouch?' is answerable from the approval event alone."""
    if asset.document_id is None:
        return {"provenance_claimed": False, "provenance_verified": False,
                "reasons": ["the asset has no source document"],
                "claimed": {}, "verified": None, "cited_assets": None}
    return verify_provenance(session, asset.document_id)
