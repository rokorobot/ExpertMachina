import json
import hashlib
import re
import zipfile

from app import llm

# First-class Expert Package consumer (v1.1 WS1).
#
# The PORTABLE channel (D10) made real: everything here operates on the
# .empkg alone. No live database retrieval, no Qdrant, no governance
# engines - the package's verifiable snapshot is the entire knowledge
# universe, which is exactly what makes "this Expert Package version
# performs best on this model" (WS2) an honest, reproducible claim.
#
# Structural purity (enforced in test_package_consumer.py): this module
# imports the standard library and app.llm only. Model generation goes
# through the D19 resolver -> provider adapter boundary (llm.generate);
# no provider SDK is imported here. Knowledge retrieval is deterministic
# lexical scoring over knowledge.json - declared as LEXICAL_OVERLAP_V1
# with counts reported (D12). An embedding index inside the .empkg is a
# future format decision, not an interpretation of this one.


class PackageVerificationError(Exception):
    """The hash chain does not hold: a file is missing, unmanifested, or
    its content does not match the manifest."""


class PackageGateError(Exception):
    """The package's compile-gate snapshot is not PASSED. Refusal is
    correct behavior - the gate is the one hard gate in the system (D5)."""


REQUIRED_FILES = ("knowledge.json", "instructions.md", "governance.json")


def load_package(package_path: str) -> dict:
    """Read a .empkg and verify its tamper-evident hash chain: every file
    against manifest.json, the file set exactly equal to the manifest's
    (no unmanifested extras), and the package hash as the sha256 of the
    manifest itself. Returns the parsed package with its verification
    record; raises PackageVerificationError on any mismatch."""
    with zipfile.ZipFile(package_path) as zf:
        names = set(zf.namelist())
        if "manifest.json" not in names:
            raise PackageVerificationError("manifest.json missing - not an Expert Package")
        manifest_bytes = zf.read("manifest.json")
        manifest = json.loads(manifest_bytes)
        files = {name: zf.read(name) for name in names if name != "manifest.json"}

    manifested = set(manifest.get("files", {}))
    actual = set(files)
    if actual != manifested:
        extras = sorted(actual - manifested)
        missing = sorted(manifested - actual)
        raise PackageVerificationError(
            f"File set does not match the manifest "
            f"(unmanifested: {extras}, missing: {missing})")

    for name, expected in manifest["files"].items():
        digest = hashlib.sha256(files[name]).hexdigest()
        if digest != expected:
            raise PackageVerificationError(
                f"TAMPER DETECTED: {name} hash mismatch "
                f"(expected {expected[:16]}..., got {digest[:16]}...)")

    for name in REQUIRED_FILES:
        if name not in files:
            raise PackageVerificationError(f"Required file {name} missing from package")

    return {
        "manifest": manifest,
        "knowledge": json.loads(files["knowledge.json"]),
        "instructions": files["instructions.md"].decode("utf-8"),
        "governance": json.loads(files["governance.json"]),
        "package_hash": hashlib.sha256(manifest_bytes).hexdigest(),
        "files_verified": len(manifest["files"]),
    }


def _tokens(text: str) -> set:
    return {t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(t) > 2}


def retrieve(package: dict, question: str, top_k: int = 8) -> dict:
    """Package-local evidence retrieval: deterministic lexical overlap
    between the question and each knowledge asset (name + content),
    highest overlap first, asset_id as the tie-break. Counts are always
    declared (D12); zero-overlap selections are honest context, and the
    answering policy's refusal rule handles insufficiency."""
    question_tokens = _tokens(question)
    scored = []
    for entry in package["knowledge"]:
        overlap = len(question_tokens & _tokens(f"{entry.get('name', '')} {entry.get('content', '')}"))
        scored.append((overlap, entry["asset_id"], entry))
    scored.sort(key=lambda item: (-item[0], item[1]))
    selected = [entry for _, _, entry in scored[:top_k]]
    return {
        "method": "LEXICAL_OVERLAP_V1",
        "considered": len(scored),
        "selected": selected,
        "selected_with_zero_overlap": sum(
            1 for overlap, _, entry in scored[:top_k] if overlap == 0),
    }


def _evidence_block(entries: list) -> str:
    lines = []
    for entry in entries:
        prov = entry.get("provenance", {})
        lines.append(
            f"[asset_id {entry['asset_id']}] ({entry.get('type')}) {entry.get('name')}\n"
            f"  Content: {entry.get('content')}\n"
            f"  Source: {prov.get('source_document')}, page {prov.get('source_page')}, "
            f"section {prov.get('source_section')}")
    return "\n\n".join(lines)


def _cited_asset_ids(answer: str, offered_ids: set) -> list:
    """Asset ids the answer cites, parsed heuristically (asset_id NNN) and
    intersected with what was actually offered - a claimed citation to an
    asset that was never in context is not a citation."""
    claimed = {int(m) for m in re.findall(r"asset[_\s]?id\D{0,3}(\d+)", answer, re.IGNORECASE)}
    return sorted(claimed & offered_ids)


def consume(package_path: str, question: str, top_k: int = 8,
            session=None, max_tokens: int = 4096) -> dict:
    """Answer a question from a verified Expert Package: verify the hash
    chain, refuse a non-PASSED gate snapshot, retrieve package-local
    evidence, generate through the D19 resolver/adapter boundary, and
    return answer + evidence + package provenance + model provenance."""
    package = load_package(package_path)
    gate = package["governance"].get("compile_gate")
    if gate != "PASSED":
        raise PackageGateError(
            f"Refusing to consume: compile gate snapshot is {gate}, not PASSED")

    retrieval = retrieve(package, question, top_k=top_k)
    system_prompt = (
        package["instructions"]
        + "\n## Governed knowledge assets (verified evidence context)\n\n"
        + _evidence_block(retrieval["selected"])
    )
    generation = llm.generate("PACKAGE_CONSUMER", system_prompt, question,
                              session=session, max_tokens=max_tokens)

    manifest = package["manifest"]
    offered_ids = {entry["asset_id"] for entry in retrieval["selected"]}
    return {
        "answer": generation["text"],
        "cited_asset_ids": _cited_asset_ids(generation["text"], offered_ids),
        "evidence": [{
            "asset_id": entry["asset_id"],
            "name": entry.get("name"),
            "type": entry.get("type"),
            "content": entry.get("content"),
            "access_level": entry.get("access_level"),
            "provenance": entry.get("provenance"),
        } for entry in retrieval["selected"]],
        "retrieval": {k: v for k, v in retrieval.items() if k != "selected"},
        "model": {"provider": generation["provider"], "model": generation["model"],
                  "source": generation["source"]},
        "package": {
            "package_name": manifest["package_name"],
            "governance_version": manifest["governance_version"],
            "expert_model": manifest["expert_model"],
            "expert_model_id": manifest["expert_model_id"],
            "clearance_level": manifest["clearance_level"],
            "compiled_at": manifest["compiled_at"],
            "trust_score_at_compile": manifest["trust_score"],
            "package_hash": package["package_hash"],
            "files_verified": package["files_verified"],
        },
    }
