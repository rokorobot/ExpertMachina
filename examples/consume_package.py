"""Consume an ExpertMachina .empkg package with an external AI agent.

Demonstrates the portable consumption channel (MVP 0.9.4): a downstream agent
loads a governed Expert Package, verifies its tamper-evident hash chain, and
answers questions ONLY from the packaged knowledge, with asset citations.

Usage:
    python consume_package.py <path/to/package.empkg> "<question>"

Verification (hash chain + governance snapshot) always runs and is offline.
The answer step calls the Claude API and needs:
    pip install anthropic
    ANTHROPIC_API_KEY set in the environment
Without a key the script prints the assembled agent prompt instead of calling
the model, so the packaging contract can be inspected end to end.

Note: this is the PORTABLE channel - governance state is a verifiable
snapshot, not live-enforced. For live-governed answers (per-question
verification, access tiers, audit logging) consume the Expert Model via the
ExpertMachina MCP gateway instead.
"""

import os
import sys
import json
import hashlib
import zipfile


def load_and_verify(package_path: str) -> dict:
    """Read the .empkg and verify its hash chain: every file against the
    manifest, and the manifest itself as the package hash."""
    with zipfile.ZipFile(package_path) as zf:
        manifest_bytes = zf.read("manifest.json")
        manifest = json.loads(manifest_bytes)
        files = {name: zf.read(name) for name in zf.namelist() if name != "manifest.json"}

    package_hash = hashlib.sha256(manifest_bytes).hexdigest()
    print(f"Package:        {manifest['package_name']} v{manifest['governance_version']}")
    print(f"Expert Model:   {manifest['expert_model']} (EM-{manifest['expert_model_id']})")
    print(f"Compiled at:    {manifest['compiled_at']}")
    print(f"Clearance:      {manifest['clearance_level']}")
    print(f"Trust score:    {manifest['trust_score']} (snapshot at compile time)")
    print(f"Assets:         {manifest['asset_count']}"
          + (f" ({manifest['excluded_assets_above_clearance']} excluded above clearance)"
             if manifest.get("excluded_assets_above_clearance") else ""))
    print(f"Package hash:   sha256:{package_hash}")

    for name, expected in manifest["files"].items():
        actual = hashlib.sha256(files[name]).hexdigest()
        if actual != expected:
            raise SystemExit(f"TAMPER DETECTED: {name} hash mismatch "
                             f"(expected {expected[:16]}…, got {actual[:16]}…)")
    print(f"Integrity:      all {len(manifest['files'])} files verified against the manifest\n")

    return {
        "manifest": manifest,
        "instructions": files["instructions.md"].decode("utf-8"),
        "knowledge": json.loads(files["knowledge.json"]),
        "governance": json.loads(files["governance.json"]),
    }


def build_system_prompt(pkg: dict) -> str:
    knowledge_lines = []
    for asset in pkg["knowledge"]:
        prov = asset["provenance"]
        knowledge_lines.append(
            f"[asset_id {asset['asset_id']}] ({asset['type']}) {asset['name']}\n"
            f"  Content: {asset['content']}\n"
            f"  Source: {prov['source_document']}, page {prov['source_page']}, "
            f"section {prov['source_section']}"
        )
    return (
        pkg["instructions"]
        + "\n## Governed knowledge assets\n\n"
        + "\n\n".join(knowledge_lines)
    )


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    package_path, question = sys.argv[1], sys.argv[2]

    pkg = load_and_verify(package_path)
    if pkg["governance"]["compile_gate"] != "PASSED":
        raise SystemExit("Refusing to consume: package was not compiled through a passing gate.")

    system_prompt = build_system_prompt(pkg)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY not set - printing the agent prompt instead of answering.\n")
        print("=" * 70)
        print(system_prompt)
        print("=" * 70)
        print(f"\nQuestion that would be asked: {question}")
        return

    from anthropic import Anthropic

    client = Anthropic()
    response = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=16000,
        system=system_prompt,
        messages=[{"role": "user", "content": question}],
    )
    answer = "".join(block.text for block in response.content if block.type == "text")

    print(f"Question: {question}\n")
    print(f"Answer:   {answer}\n")
    print(f"Answered by an external agent from package "
          f"'{pkg['manifest']['package_name']}' v{pkg['manifest']['governance_version']} "
          f"(trust {pkg['manifest']['trust_score']} at compile time).")


if __name__ == "__main__":
    main()
