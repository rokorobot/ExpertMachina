"""v2.5.0 WS3 - THE D33 REAL-MODEL PROOF (one run per invocation).

Reuses a workbench's own milestone-gate suite (backend/test_<corpus>_
acceptance.py) for the full governed setup - the ratified corpus through
the real pipeline, human-approved PRIMARY facts, an INTERNAL empkg-v1.1
package, a real AGENT binding - and intercepts its diagnosis call:

  1. BASELINE - the suite's own CI contract-follower (the planted map);
  2. REAL - the same call with answerer=None, i.e. the runner's real
     consume() path, PACKAGE_CONSUMER set to ANTHROPIC through the audited
     settings route (D19 CONFIG tier, one LLM_CONFIG_UPDATED event).

Then stops (later gate stages assert CI-specific counts). PASS iff the
real run's refusal-backed findings equal the baseline's EXACTLY (every
planted gap found, every covered control silent) and no answer is
UNDETERMINED. Customer-ops gets its covered control the way its workbench
suite adds it (the refund-window question, which the corpus answers).

Usage (from backend/, with ANTHROPIC_API_KEY in the environment):
    python ../tools/d33_real_model_proof.py customer_ops|compliance MODEL OUT.json
Never committed evidence: OUT.json is written outside the repo by the
caller; the gate record quotes it.
"""
import importlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

CORPUS, MODEL, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
assert CORPUS in ("customer_ops", "compliance"), CORPUS
assert os.environ.get("ANTHROPIC_API_KEY"), "ANTHROPIC_API_KEY required"

BACKEND = os.path.abspath(".")
sys.path.insert(0, BACKEND)
acc = importlib.import_module(f"test_{CORPUS}_acceptance")   # sets up temp DB/dirs
import test_support                                          # noqa: E402
from app import database as db, package_consumer, schemas, llm   # noqa: E402
from app.routers import settings as settings_router          # noqa: E402

# The covered control must be UNCONTESTED: the refund-window question the
# workbench suite uses is a planted contradiction (14 vs 30 days), so a
# real model rightly declines to answer it fully. It is kept as a probe.
CONTROL_QUESTION = ("Do approved refunds go back to the original payment method "
                    "within 10 business days of approval?")
CONTESTED_PROBE = ("May customers request a refund within days of delivery "
                   "under the refund policy?")


class ProofDone(Exception):
    pass


calls, evidence = [], {}
_real_consume = package_consumer.consume


def recording_consume(path, question, *a, **k):
    r = _real_consume(path, question, *a, **k)
    calls.append({"question": question, "answer_status": r["answer_status"],
                  "refused_scope": r["refused_scope"], "status_source": r["status_source"],
                  "model": r["model"], "answer_head": r["answer"][:300]})
    return r


def covered_skills_dir():
    src = os.path.join(acc.REPO_DIR, "workbench", "customer_operations", "skills")
    dst = tempfile.mkdtemp(prefix="em_d33_skills_")
    for n in os.listdir(src):
        shutil.copy(os.path.join(src, n), os.path.join(dst, n))
    p = os.path.join(dst, "detect_sla_obligation_gap.yaml")
    text = open(p, encoding="utf-8").read()
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(text.replace("question_frame:",
                             f'question_frame:\n  - "{CONTROL_QUESTION}"\n  - "{CONTESTED_PROBE}"', 1))
    return dst


_real_run = acc.runner.run_diagnostic


def intercept(package_path, vault_dir, project_id, *args, **kwargs):
    if CORPUS == "customer_ops":
        kwargs["skills_dir"] = covered_skills_dir()
    base_status = {}
    ci_answerer = kwargs["answerer"]

    def recording_ci(question):
        r = ci_answerer(question)
        base_status[question] = package_consumer.parse_answer_status(
            r.get("answer"), "empkg-v1.1")["answer_status"]
        return r
    kwargs["answerer"] = recording_ci
    baseline = _real_run(package_path, vault_dir, project_id, *args, **kwargs)
    s = db.SessionLocal()
    admin = test_support.governed_actor(s, "D33ProofAdmin", role="ADMIN")
    settings_router.update_llm_setting(
        "PACKAGE_CONSUMER", schemas.LLMFunctionSettingUpdate(provider="ANTHROPIC", model=MODEL),
        db_session=s, actor=admin)
    resolved = llm.resolve("PACKAGE_CONSUMER", s)
    s.close()
    assert resolved["provider"] == "ANTHROPIC" and resolved["source"] == "CONFIG", resolved
    real_vault = tempfile.mkdtemp(prefix="em_d33_real_vault_")
    r = subprocess.run([sys.executable, os.path.join(acc.REPO_DIR, "vault", "bootstrap.py"),
                        "--vault-dir", real_vault], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    kwargs["answerer"] = None
    package_consumer.consume = recording_consume
    try:
        real = _real_run(package_path, real_vault, project_id, *args, **kwargs)
    finally:
        package_consumer.consume = _real_consume
    want = test_support.refusal_backed(baseline["findings"])
    got = test_support.refusal_backed(real["findings"])
    evidence.update({
        "corpus": CORPUS, "model": MODEL, "resolved": resolved,
        "baseline_refusal_backed": want, "real_refusal_backed": got,
        "missed_gaps": sorted(set(map(tuple, want)) - set(map(tuple, got))),
        "extra_findings": sorted(set(map(tuple, got)) - set(map(tuple, want))),
        "answer_status_counts": real["answer_status_counts"],
        "baseline_status_counts": baseline["answer_status_counts"],
        "partial_scopes": [
            line for f in real["findings"] if f.get("evidence_basis") == "REFUSAL_BACKED"
            for line in f["evidence_lines"] if line.startswith("Refused scope")],
        "calls": calls,
    })
    real_status = {c["question"]: c["answer_status"] for c in calls}
    covered = sorted(q for q, st in base_status.items()
                     if st == "ANSWERED" and q != CONTESTED_PROBE)
    evidence["covered_controls"] = {q: real_status.get(q) for q in covered}
    evidence["contested_probe"] = {q: real_status.get(q) for q in base_status
                                   if q == CONTESTED_PROBE}
    probe_ids = [x for x in got if x[1] == CONTESTED_PROBE]
    evidence["contested_probe_findings"] = probe_ids
    evidence["passed"] = (
        [x for x in got if x[1] != CONTESTED_PROBE] == [x for x in want if x[1] != CONTESTED_PROBE]
        and "UNDETERMINED" not in real["answer_status_counts"]
        and all(st == "ANSWERED" for st in evidence["covered_controls"].values()))
    raise ProofDone()


acc.runner.run_diagnostic = intercept
try:
    acc.main()
except ProofDone:
    pass
json.dump(evidence, open(OUT, "w"), indent=2, default=str)
print(json.dumps({k: evidence[k] for k in ("corpus", "passed", "missed_gaps",
                                           "extra_findings", "answer_status_counts",
                                           "covered_controls", "contested_probe")},
                 default=str))
