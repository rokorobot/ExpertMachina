import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Force deterministic legacy path for Part 1; re-enabled for Part 2.
os.environ["EM_NLI_VERIFICATION"] = "off"
os.environ.setdefault("OPENAI_API_KEY", "mock-key")

from app import query_engine
from app import verification_engine


CITATIONS = [
    {
        "asset_id": 1,
        "name": "Deviation Logging Policy",
        "content": "Critical deviations must be logged within 24 hours.",
    },
    {
        "asset_id": 2,
        "name": "Data Retention Policy",
        "content": "Customer data must be deleted after 30 days.",
    },
    {
        "asset_id": 3,
        "name": "Timesheet Procedure",
        "content": "Employees submit timesheets weekly.",
    },
]

# Labeled verification benchmark: (claim, expected_verdict, description)
NLI_BENCHMARK = [
    ("Critical deviations must be logged within 24 hours.", "ENTAILED", "verbatim policy restatement"),
    ("Timesheets are submitted by employees every week.", "ENTAILED", "paraphrase of procedure"),
    ("Critical deviations must not be logged within 24 hours.", "CONTRADICTED", "direct negation of policy"),
    ("Customer data must be retained indefinitely.", "CONTRADICTED", "semantic inversion of retention policy"),
    ("Managers receive performance bonuses every quarter.", "UNSUPPORTED", "neutral claim, no evidence"),
]


def test_keyword_fallback_report_shape():
    print("\n--- Part 1: Legacy keyword fallback (EM_NLI_VERIFICATION=off) ---")
    answer = (
        "Critical deviations must be logged within 24 hours. "
        "Managers receive performance bonuses every quarter."
    )
    report = query_engine.verify_answer_claims(None, answer_text=answer, validated_citations=CITATIONS)

    assert report["verifier"]["method"] == "KEYWORD_OVERLAP", f"Expected KEYWORD_OVERLAP verifier, got {report['verifier']}"
    assert report["contradicted_claims"] == [], "Keyword path must not report contradictions"
    assert all("verdict" in m and "contradicting_assets" in m for m in report["claim_mappings"]), \
        "Claim mappings missing unified verdict fields"
    assert "Managers receive performance bonuses every quarter." in report["unsupported_claims"], \
        "Keyword path failed to flag the unsupported claim"
    print("Part 1 passed: fallback path works and reports its verifier identity.")


def test_contradiction_hard_fail_rule():
    print("\n--- Part 2: Contradiction hard-fail overrides coverage ---")
    # 9 supported claims + 1 contradicted = coverage 0.90, which would be
    # PARTIALLY_VERIFIED on coverage alone. Contradiction must force a block.
    claims = [f"Supported claim {i}." for i in range(9)] + ["Contradicted claim."]
    mappings = [
        {"claim": c, "verdict": "ENTAILED", "supporting_assets": [1], "contradicting_assets": []}
        for c in claims[:9]
    ]
    mappings.append({"claim": claims[9], "verdict": "CONTRADICTED", "supporting_assets": [], "contradicting_assets": [2]})

    report = query_engine._finalize_verification_report(
        claims=claims,
        claim_mappings=mappings,
        unsupported_claims=[],
        contradicted_claims=[claims[9]],
        verifier=verification_engine.verifier_identity(),
    )
    assert report["coverage_score"] == 0.9, f"Expected coverage 0.9, got {report['coverage_score']}"
    assert report["verification_status"] == "INSUFFICIENT_EVIDENCE", \
        "A contradicted claim must hard-fail verification regardless of coverage"
    print("Part 2 passed: contradiction blocks the answer even at 0.90 coverage.")


def test_nli_labeled_benchmark():
    print("\n--- Part 3: NLI entailment benchmark (local DeBERTa cross-encoder) ---")
    os.environ["EM_NLI_VERIFICATION"] = "auto"

    pipe = verification_engine.get_nli_pipeline()
    if pipe is None:
        print("SKIPPED: NLI model unavailable (transformers/torch not installed or model not downloadable).")
        return

    claims = [case[0] for case in NLI_BENCHMARK]
    result = verification_engine.verify_claims_nli(claims, CITATIONS)
    assert result is not None, "NLI verifier returned None despite an available pipeline"
    assert result["verifier"]["method"] == "NLI_LOCAL"

    failures = []
    for mapping, (claim, expected, description) in zip(result["claim_mappings"], NLI_BENCHMARK):
        status = "OK " if mapping["verdict"] == expected else "FAIL"
        print(f"  [{status}] {description}: expected {expected}, got {mapping['verdict']}")
        if mapping["verdict"] != expected:
            failures.append((claim, expected, mapping["verdict"]))

    assert not failures, f"NLI verdicts wrong for: {failures}"

    # End-to-end: an answer that inverts approved evidence must be blocked.
    report = query_engine.verify_answer_claims(
        None,
        answer_text="Critical deviations must be logged within 24 hours. Customer data must be retained indefinitely.",
        validated_citations=CITATIONS,
    )
    assert report["verifier"]["method"] == "NLI_LOCAL"
    assert "Customer data must be retained indefinitely." in report["contradicted_claims"], \
        "NLI path failed to flag the inverted claim as contradicted"
    assert report["verification_status"] == "INSUFFICIENT_EVIDENCE", \
        "Contradicted answer must be blocked"
    print("Part 3 passed: NLI verifier catches negation and semantic inversion that keyword overlap cannot.")


if __name__ == "__main__":
    test_keyword_fallback_report_shape()
    test_contradiction_hard_fail_rule()
    test_nli_labeled_benchmark()
    print("\n=== All NLI verification engine tests passed successfully! ===")
