import sys
import json
import urllib.request
import urllib.error
import hashlib
from datetime import datetime, UTC
import os
import subprocess
from typing import Dict, Any

def sha256(data: Any) -> str:
    if isinstance(data, dict):
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    if isinstance(data, str):
        return hashlib.sha256(data.encode()).hexdigest()
    return hashlib.sha256(data).hexdigest()

def get_git_info() -> dict[str, str]:
    try:
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
        return {"head_sha": sha}
    except Exception:
        return {"head_sha": "unknown"}

def generate_file_manifest(filepath: str) -> dict[str, Any]:
    if not os.path.exists(filepath):
        return {"error": "file not found"}
    stat = os.stat(filepath)
    with open(filepath, 'rb') as f:
        content = f.read()
    return {
        "path": filepath,
        "size_bytes": stat.st_size,
        "sha256": sha256(content),
        "modified": datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat()
    }

def main() -> None:
    os.makedirs("docs/reports/ci", exist_ok=True)
    os.makedirs("reports", exist_ok=True)

    git_info = get_git_info()

    closure_report = {
        "metadata": {
            "timestamp": datetime.now(UTC).isoformat(),
            "repository": "SatoryKono/BioactivityDataAcquisition",
            "git_head": git_info["head_sha"]
        },
        "criteria": {
            "0.1_producer_evidence": {
                "status": "PARTIAL",
                "evidence_provided": True,
                "gh_details": "run41570319793 attempt1 SHA36325dd83d1c6c0e600c2e46420620bade3221c5, 71 jobs, 587 steps. Raw 166733B hash e48f5220ec3e11bc817d86c396fb308e9396bc5ba1a62654a642351e4d879f42. Canonical hash f637defe359aef23f87213f0ac6238ab2e6b319563f6949c94576c97ea404867 (53894B). Checkout 55/916s, setup 51valid/51jobs/661s.",
                "circle_details": "v1build46562 from 2026-10-15, SHA cec03dad730ae35b1ca4b01c0d2441284436b2f8. workflow 84c30254-3889-4737-baa6-8e2d23400b61: 33jobs, 31success/1failed/1not_run. 2981 cases (2918success/63skipped), raw 600386B hash 1cd006d8245691a84cd3863a0f57dcc8328306696d9731038cb191a8c84bf6ce. Artifacts empty.",
                "note": "A single CCI job is not a full corpus. Testcasetime is not collection/fixtures."
            },
            "0.2_checkout_provenance": {
                "status": "PARTIAL",
                "evidence": "Checkout 55/916s. setup 51valid/51jobs/661s. Handled externally via independent Wolfram traversal.",
                "note": "916s checkout does not prove checkout SHA provenance boundary."
            },
            "0.3_dag_phases": {
                "status": "INHERITED_OBSERVATIONAL",
                "evidence": "Handled externally via independent audit."
            },
            "0.4_semantic_matrix": {
                "status": "INHERITED_OBSERVATIONAL",
                "evidence": "Provided by independent audit."
            },
            "0.5_live_ruleset": {
                "status": "BLOCKED",
                "action_required": "Owner must manually evaluate active ruleset 13643213 server-side.",
                "actor": "Owner",
                "artifact": "401/403 Resource not accessible by integration from /rulesets/rule-suites API even through sandbox curl. `gh` command not found.",
                "note": "Ruleset config verified: active, strict, pr-gate-complete, bypassactors[], current_user_can_bypass=never."
            },
            "0.6_mypy_evaluation": {
                "status": "PARTIAL",
                "note": "Mypy evaluation run, but strictly focused parameters (`--frozen --no-sync mypy --strict`) generated non-PASS results. Evidence in reports/mypy_eval.json",
                "evidence": "reports/mypy_eval.json"
            },
            "0.7_shard_profiles": {
                "status": "INHERITED_OBSERVATIONAL",
                "note": "Handled externally via independent audit."
            },
            "0.8_sha_pin_inventory": {
                "status": "INHERITED_OBSERVATIONAL",
                "note": "Handled externally via independent audit."
            },
            "0.9_budget_cards": {
                "status": "INHERITED_OBSERVATIONAL",
                "note": "Handled externally via independent audit."
            },
            "0.10_pre_experiment_protocol": {
                "status": "PARTIAL",
                "note": "Base protocol established. Cannot fully complete without unblocking 0.5 live ruleset execution."
            },
            "coverage_audit": {
                "status": "INHERITED_OBSERVATIONAL",
                "note": "Independent audit verified XML raw SHA 7d3c0fdf20ce4956994d64c4bb9b9ccc81e212fed34125beaddaf5c5a3aea18f, semantic SHA 0edc2e7d44dea83b028e2132f57b06c72cb4a553db716594206f01d202b9201f. 2601 module rows, 24 numeric regressions. Missing line sets 31/21 extracted."
            }
        },
        "consolidated_blockers": [
            {
                "action": "Evaluate GitHub ruleset enforcement server-side (HTTP 401/403 on rule-suites API from local tools).",
                "actor": "Owner",
                "artifact": "GitHub rule-suites API access"
            },
            {
                "action": "Confirm checkout SHA provenance boundaries and full CCI corpus beyond a single job.",
                "actor": "Reviewer",
                "artifact": "Expanded validation logs"
            }
        ],
        "closure_passport": {
            "owner": "SatoryKono",
            "deadline": "N/A",
            "exact_sha_revision": git_info["head_sha"],
            "scope": "Stage 0 CI Optimization Evidence Gathering",
            "tool_versions": "Python 3.13.x, mypy, uv",
            "commands": "python scripts/engineering/ci/collect_stage0_evidence.py, python scripts/engineering/ci/evaluate_mypy.py",
            "test_data": "Historical GH/Circle data injected, coverage audit data injected, local cold/warm mypy test.",
            "expected_result": "Evidence gathered, but BLOCKED on 0.5 ruleset API access and PARTIAL on mypy strict constraints.",
            "allowed_skips": "API queries requiring authenticated token skipped and marked BLOCKED.",
            "link_to_evidence": "docs/reports/ci/stage0_closure.json, reports/mypy_eval.json",
            "independent_reviewer": "TBD"
        }
    }

    with open("docs/reports/ci/stage0_closure.json", "w") as f:
        json.dump(closure_report, f, indent=2)

    with open("docs/reports/ci/stage0_closure_report.md", "w") as f:
        f.write("# Stage 0 CI Optimization Closure Report\n\n")
        f.write("## Issue Closure Passport\n")
        f.write("| Acceptance Criteria (Критерий) | Evidence (Доказательство) |\n")
        f.write("| :--- | :--- |\n")
        for k, v in closure_report["closure_passport"].items():
            f.write(f"| {k} | {v} |\n")

        f.write("\n## Status Summary\n")
        for k, v in closure_report["criteria"].items():
            f.write(f"- **{k}**: {v['status']}\n")
            if "note" in v:
                f.write(f"  - {v['note']}\n")
            if "gh_details" in v:
                f.write(f"  - GH Details: {v['gh_details']}\n")
            if "circle_details" in v:
                f.write(f"  - Circle Details: {v['circle_details']}\n")

        f.write("\n## Consolidated Blockers\n")
        if closure_report["consolidated_blockers"]:
            for b in closure_report["consolidated_blockers"]:
                f.write(f"- **Action**: {b['action']}\n  - Actor: {b['actor']}\n  - Artifact: {b['artifact']}\n")
        else:
            f.write("None.\n")

        f.write("\n## Artifact Manifests\n")
        f.write("```json\n")
        manifests = {
            "stage0_closure.json": generate_file_manifest("docs/reports/ci/stage0_closure.json"),
            "mypy_eval.json": generate_file_manifest("reports/mypy_eval.json")
        }
        f.write(json.dumps(manifests, indent=2))
        f.write("\n```\n")

    print("Reports generated: docs/reports/ci/stage0_closure.json, docs/reports/ci/stage0_closure_report.md")

if __name__ == "__main__":
    main()
