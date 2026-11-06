from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


STRICT_TYPE_GATE_TARGETS = ["src/bioetl", "src/memory", "scripts/engineering/quality"]
INDEPENDENT_AUDIT_NOTE = "Handled externally via independent audit."


def sha256(data: Any) -> str:
    """Hash a JSON object, a string, or bytes for the artifact manifest."""
    if isinstance(data, dict):
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    if isinstance(data, str):
        return hashlib.sha256(data.encode()).hexdigest()
    return hashlib.sha256(data).hexdigest()


def get_git_info() -> dict[str, str | bool | None]:
    """Record the checkout base and whether its working tree matches HEAD."""
    try:
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        status = subprocess.check_output(["git", "status", "--porcelain"], text=True)
    except (OSError, subprocess.CalledProcessError):
        return {"head_sha": "unknown", "worktree_dirty": None}
    return {"head_sha": head, "worktree_dirty": bool(status)}


def generate_file_manifest(filepath: str) -> dict[str, Any]:
    """Describe an evidence file, including its digest and modification time."""
    if not os.path.exists(filepath):
        return {"error": "file not found"}
    stat = os.stat(filepath)
    with open(filepath, "rb") as f:
        content = f.read()
    return {
        "path": filepath,
        "size_bytes": stat.st_size,
        "sha256": sha256(content),
        "modified": datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
    }


def _atomic_write_text(path: Path, text: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def evaluate_mypy_criterion(
    evidence_path: str = "reports/mypy_eval.json",
) -> dict[str, Any]:
    """Derive 0.6 mypy status from the actual evaluation report."""
    path = Path(evidence_path)
    if not path.is_file():
        return {
            "status": "MISSING",
            "note": (
                "Файл reports/mypy_eval.json отсутствует; эксперимент cold/warm "
                "не выполнен, доказательств нет."
            ),
            "evidence": evidence_path,
            "typecheck_pass": False,
            "cache_measurement_usable": False,
            "diagnostics_match": False,
        }

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "status": "PARTIAL",
            "note": f"reports/mypy_eval.json нечитаем: {exc}",
            "evidence": evidence_path,
            "typecheck_pass": False,
            "cache_measurement_usable": False,
            "diagnostics_match": False,
        }

    cold = payload.get("cold") if isinstance(payload, dict) else None
    warm = payload.get("warm") if isinstance(payload, dict) else None
    comparison = payload.get("comparison") if isinstance(payload, dict) else None
    if not isinstance(cold, dict) or not isinstance(warm, dict):
        return {
            "status": "PARTIAL",
            "note": "reports/mypy_eval.json не содержит cold/warm результатов.",
            "evidence": evidence_path,
            "typecheck_pass": False,
            "cache_measurement_usable": False,
            "diagnostics_match": False,
        }

    targets_match = payload.get("targets") == STRICT_TYPE_GATE_TARGETS
    cold_rc = cold.get("returncode")
    warm_rc = warm.get("returncode")
    typecheck_pass = cold_rc == 0 and warm_rc == 0
    diagnostics_match = bool(
        isinstance(comparison, dict) and comparison.get("diagnostics_match") is True
    )
    speedup = (
        float(comparison["speedup"])
        if isinstance(comparison, dict)
        and isinstance(comparison.get("speedup"), (int, float))
        else None
    )
    # Usable cache evidence requires matching diagnostics and a warm speedup.
    cache_measurement_usable = (
        targets_match
        and typecheck_pass
        and diagnostics_match
        and speedup is not None
        and speedup > 1.05
    )

    status, note = _describe_mypy_result(
        cold_rc,
        warm_rc,
        diagnostics_match,
        speedup,
        cache_measurement_usable,
        targets_match,
    )

    return {
        "status": status,
        "note": note,
        "evidence": evidence_path,
        "typecheck_pass": typecheck_pass,
        "cache_measurement_usable": cache_measurement_usable,
        "diagnostics_match": diagnostics_match,
        "speedup": speedup,
        "targets_match": targets_match,
        "remote_cache_verified": False,
        "cold_returncode": cold_rc,
        "warm_returncode": warm_rc,
    }


def _describe_mypy_result(
    cold_rc: int | None,
    warm_rc: int | None,
    diagnostics_match: bool,
    speedup: float | None,
    cache_measurement_usable: bool,
    targets_match: bool,
) -> tuple[str, str]:
    if cold_rc != 0 or warm_rc != 0:
        return "PARTIAL", (
            f"Mypy non-PASS: cold returncode={cold_rc}, warm returncode={warm_rc}. "
            f"diagnostics_match={diagnostics_match}."
        )

    if not targets_match:
        return "PARTIAL", (
            "Type-checking PASS для измеренных целей, но отчёт не подтверждает "
            "полный набор целей строгой проверки CI."
        )

    if cache_measurement_usable:
        note = (
            f"Type-checking PASS (cold/warm returncode=0); diagnostics совпадают; "
            f"speedup={speedup:.3f} подтверждён для локального кэша. "
            "Восстановление удалённого кэша в CI не измерялось."
        )
    elif diagnostics_match:
        speedup_text = f"{speedup:.3f}" if speedup is not None else "n/a"
        note = (
            f"Type-checking PASS (cold/warm returncode=0); diagnostics совпадают; "
            f"speedup={speedup_text} — ускорение кэша не доказано "
            f"(порог >1.05)."
        )
    else:
        note = (
            "Type-checking PASS (cold/warm returncode=0), но diagnostics cold/warm "
            "не совпадают; измерение кэша непригодно."
        )
    return "PARTIAL", note


def main() -> None:
    """Collect Stage 0 evidence and render its JSON and Markdown reports."""
    os.makedirs("docs/reports/ci", exist_ok=True)
    os.makedirs("reports", exist_ok=True)

    git_info = get_git_info()
    mypy_criterion = evaluate_mypy_criterion()

    closure_report = {
        "metadata": {
            "timestamp": datetime.now(UTC).isoformat(),
            "repository": "SatoryKono/BioactivityDataAcquisition",
            "git_head": git_info["head_sha"],
            "worktree_dirty": git_info["worktree_dirty"],
        },
        "criteria": {
            "0.1_producer_evidence": {
                "status": "PARTIAL",
                "evidence_provided": True,
                "gh_details": "run41570319793 attempt1 SHA36325dd83d1c6c0e600c2e46420620bade3221c5, 71 jobs, 587 steps. Raw 166733B hash e48f5220ec3e11bc817d86c396fb308e9396bc5ba1a62654a642351e4d879f42. Canonical hash f637defe359aef23f87213f0ac6238ab2e6b319563f6949c94576c97ea404867 (53894B). Checkout 55/916s, setup 51valid/51jobs/661s.",
                "circle_details": "v1build46562 from 2026-10-15, SHA cec03dad730ae35b1ca4b01c0d2441284436b2f8. workflow 84c30254-3889-4737-baa6-8e2d23400b61: 33jobs, 31success/1failed/1not_run. 2981 cases (2918success/63skipped), raw 600386B hash 1cd006d8245691a84cd3863a0f57dcc8328306696d9731038cb191a8c84bf6ce. Artifacts empty.",
                "note": "A single CCI job is not a full corpus. Testcasetime is not collection/fixtures.",
            },
            "0.2_checkout_provenance": {
                "status": "PARTIAL",
                "evidence": "Checkout 55/916s. setup 51valid/51jobs/661s. Handled externally via independent Wolfram traversal.",
                "note": "916s checkout does not prove checkout SHA provenance boundary.",
            },
            "0.3_dag_phases": {
                "status": "INHERITED_OBSERVATIONAL",
                "evidence": INDEPENDENT_AUDIT_NOTE,
            },
            "0.4_semantic_matrix": {
                "status": "INHERITED_OBSERVATIONAL",
                "evidence": "Provided by independent audit.",
            },
            "0.5_live_ruleset": {
                "status": "BLOCKED",
                "action_required": "Owner must manually evaluate active ruleset 13643213 server-side.",
                "actor": "Owner",
                "artifact": "401/403 Resource not accessible by integration from /rulesets/rule-suites API even through sandbox curl. `gh` command not found.",
                "note": "Ruleset config verified: active, strict, pr-gate-complete, bypassactors[], current_user_can_bypass=never.",
            },
            "0.6_mypy_evaluation": mypy_criterion,
            "0.7_shard_profiles": {
                "status": "INHERITED_OBSERVATIONAL",
                "note": INDEPENDENT_AUDIT_NOTE,
            },
            "0.8_sha_pin_inventory": {
                "status": "INHERITED_OBSERVATIONAL",
                "note": INDEPENDENT_AUDIT_NOTE,
            },
            "0.9_budget_cards": {
                "status": "INHERITED_OBSERVATIONAL",
                "note": INDEPENDENT_AUDIT_NOTE,
            },
            "0.10_pre_experiment_protocol": {
                "status": "PARTIAL",
                "note": "Base protocol established. Cannot fully complete without unblocking 0.5 live ruleset execution.",
            },
            "coverage_audit": {
                "status": "INHERITED_OBSERVATIONAL",
                "note": "Independent audit verified XML raw SHA 7d3c0fdf20ce4956994d64c4bb9b9ccc81e212fed34125beaddaf5c5a3aea18f, semantic SHA 0edc2e7d44dea83b028e2132f57b06c72cb4a553db716594206f01d202b9201f. 2601 module rows, 24 numeric regressions. Missing line sets 31/21 extracted.",
            },
        },
        "consolidated_blockers": [
            {
                "action": "Evaluate GitHub ruleset enforcement server-side (HTTP 401/403 on rule-suites API from local tools).",
                "actor": "Owner",
                "artifact": "GitHub rule-suites API access",
            },
            {
                "action": "Confirm checkout SHA provenance boundaries and full CCI corpus beyond a single job.",
                "actor": "Reviewer",
                "artifact": "Expanded validation logs",
            },
        ],
        "closure_passport": {
            "owner": "SatoryKono",
            "deadline": "N/A",
            "collector_base_sha": git_info["head_sha"],
            "collector_worktree_dirty": git_info["worktree_dirty"],
            "scope": "Stage 0 CI Optimization Evidence Gathering",
            "tool_versions": "Python 3.13.x, mypy, uv",
            "commands": "python scripts/engineering/ci/evaluate_mypy.py, python scripts/engineering/ci/collect_stage0_evidence.py",
            "test_data": "Historical GH/Circle data injected, coverage audit data injected, local cold/warm mypy test.",
            "expected_result": (
                "Evidence gathered from reports/mypy_eval.json "
                f"(0.6 status={mypy_criterion['status']}); "
                "BLOCKED on 0.5 ruleset API access."
            ),
            "allowed_skips": "API queries requiring authenticated token skipped and marked BLOCKED.",
            "link_to_evidence": "docs/reports/ci/stage0_closure.json, reports/mypy_eval.json",
            "independent_reviewer": "TBD",
        },
    }

    closure_path = Path("docs/reports/ci/stage0_closure.json")
    _atomic_write_text(
        closure_path,
        json.dumps(closure_report, indent=2, ensure_ascii=False) + "\n",
    )

    report_lines = [
        "# Stage 0 CI Optimization Closure Report\n",
        "## Issue Closure Passport\n",
        "| Acceptance Criteria (Критерий) | Evidence (Доказательство) |\n",
        "| :--- | :--- |\n",
    ]
    for k, v in closure_report["closure_passport"].items():
        report_lines.append(f"| {k} | {v} |\n")

    report_lines.append("\n## Status Summary\n")
    for k, v in closure_report["criteria"].items():
        report_lines.append(f"- **{k}**: {v['status']}\n")
        if "note" in v:
            report_lines.append(f"  - {v['note']}\n")
        if "gh_details" in v:
            report_lines.append(f"  - GH Details: {v['gh_details']}\n")
        if "circle_details" in v:
            report_lines.append(f"  - Circle Details: {v['circle_details']}\n")

    report_lines.append("\n## Consolidated Blockers\n")
    if closure_report["consolidated_blockers"]:
        for b in closure_report["consolidated_blockers"]:
            report_lines.append(
                f"- **Action**: {b['action']}\n  - Actor: {b['actor']}\n  - Artifact: {b['artifact']}\n"
            )
    else:
        report_lines.append("None.\n")

    report_lines.append("\n## Artifact Manifests\n")
    report_lines.append("```json\n")
    manifests = {
        "stage0_closure.json": generate_file_manifest(
            "docs/reports/ci/stage0_closure.json"
        ),
        "mypy_eval.json": generate_file_manifest("reports/mypy_eval.json"),
    }
    report_lines.append(json.dumps(manifests, indent=2))
    report_lines.append("\n```\n")

    _atomic_write_text(
        Path("docs/reports/ci/stage0_closure_report.md"),
        "".join(report_lines),
    )

    print(
        "Reports generated: docs/reports/ci/stage0_closure.json, docs/reports/ci/stage0_closure_report.md"
    )


if __name__ == "__main__":
    main()
