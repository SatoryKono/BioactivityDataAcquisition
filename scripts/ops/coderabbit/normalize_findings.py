"""Normalize CodeRabbit agent logs into reproducible campaign ledgers."""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
CAMPAIGN_DATE = os.environ.get(
    "CODERABBIT_CAMPAIGN_DATE", datetime.now(UTC).strftime("%Y%m%d")
)
OUT = ROOT / "reports" / "quality" / "coderabbit" / CAMPAIGN_DATE
OVERRIDES_PATH = OUT / "TRIAGE_OVERRIDES.json"


def normalize_text(value: str) -> str:
    value = re.sub(r"around lines?\s+\d+\s*-\s*\d+", "", value, flags=re.I)
    value = re.sub(r"at line\s+\d+", "", value, flags=re.I)
    return " ".join(value.lower().split())


def fingerprint(path: str, claim: str) -> str:
    payload = f"{path.strip().lower()}\n{normalize_text(claim)}".encode()
    return hashlib.sha256(payload).hexdigest()[:16]


def claim_from_instruction(instruction: str) -> str:
    marker = "\n\n"
    if marker in instruction:
        instruction = instruction.split(marker, 1)[1]
    return " ".join(instruction.split())


def fix_class(claim: str) -> str:
    lowered = claim.lower()
    if any(
        token in lowered for token in ("unit test", "tests covering", "regression test")
    ):
        return "test"
    if any(
        token in lowered for token in ("document", "migration note", "adr reference")
    ):
        return "docs"
    if any(token in lowered for token in ("config", "yaml", "workflow")):
        return "config"
    return "code"


def load_overrides() -> dict[str, dict[str, Any]]:
    if not OVERRIDES_PATH.exists():
        return {}
    value = json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError("TRIAGE_OVERRIDES.json must be an object")
    return {key: item for key, item in value.items() if isinstance(item, dict)}


def raw_findings() -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for log_path in sorted(OUT.glob("review_*_*.log")):
        name = log_path.stem.removeprefix("review_")
        wave, leaf = name.split("_", 1)
        finding_index = 0
        for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict) or event.get("type") != "finding":
                continue
            finding_index += 1
            path = str(event.get("fileName", "<unknown>"))
            claim = claim_from_instruction(str(event.get("codegenInstructions", "")))
            item_id = f"CR-{CAMPAIGN_DATE}-{wave}-{leaf}-{finding_index:03d}"
            findings.append(
                {
                    "id": item_id,
                    "wave": wave,
                    "leaf": leaf,
                    "severity": str(event.get("severity", "minor")).lower(),
                    "path": path,
                    "claim": claim,
                    "fix_class": fix_class(claim),
                    "confidence": "medium",
                    "status": "pending",
                    "fingerprint": fingerprint(path, claim),
                    "gh_issue": None,
                    "log": str(log_path.relative_to(ROOT)),
                }
            )
    return findings


def _split_findings(
    original_findings: list[dict[str, Any]],
    overrides: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for finding in original_findings:
        override = overrides.get(str(finding["fingerprint"]), {})
        split_problems = override.get("split_problems")
        if not isinstance(split_problems, list) or not split_problems:
            findings.append(finding)
            continue
        finding["status"] = "split_parent"
        finding["triage_reason"] = str(
            override.get(
                "triage_reason", "CodeRabbit compound claim split into atomic problems"
            )
        )
        findings.append(finding)
        findings.extend(
            _derived_problem(finding, raw_problem, index)
            for index, raw_problem in enumerate(split_problems, 1)
            if isinstance(raw_problem, dict)
        )
    return findings


def _derived_problem(
    finding: dict[str, Any],
    raw_problem: dict[str, Any],
    index: int,
) -> dict[str, Any]:
    problem = dict(finding)
    problem.update(raw_problem)
    problem["id"] = f"{finding['id']}-S{index}"
    problem["origin_id"] = finding["id"]
    problem["derived"] = True
    problem["fingerprint"] = fingerprint(str(problem["path"]), str(problem["claim"]))
    return problem


def _apply_override(finding: dict[str, Any], override: dict[str, Any]) -> None:
    for key in (
        "status",
        "severity",
        "confidence",
        "fix_class",
        "triage_reason",
        "evidence",
        "gh_issue",
        "gh_url",
        "prior_issue",
    ):
        if key in override:
            finding[key] = override[key]


def _deduplicate_findings(
    findings: list[dict[str, Any]],
    overrides: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    canonical: dict[str, str] = {}
    dedupe: dict[str, dict[str, Any]] = {}
    for finding in findings:
        fp = str(finding["fingerprint"])
        if fp in canonical:
            finding["status"] = "duplicate"
            finding["duplicate_of"] = canonical[fp]
            dedupe[fp]["duplicates"].append(finding["id"])
            continue
        canonical[fp] = str(finding["id"])
        dedupe[fp] = {
            "canonical_finding_id": finding["id"],
            "path": finding["path"],
            "claim": finding["claim"],
            "duplicates": [],
            "gh_issue": None,
        }
        _apply_override(finding, overrides.get(fp, {}))
        dedupe[fp]["gh_issue"] = finding.get("gh_issue")
    return dedupe


def _write_machine_ledgers(
    findings: list[dict[str, Any]],
    dedupe: dict[str, dict[str, Any]],
) -> None:
    with (OUT / "FINDINGS.jsonl").open("w", encoding="utf-8") as stream:
        for finding in findings:
            stream.write(json.dumps(finding, ensure_ascii=False) + "\n")
    (OUT / "DE_DUPE_MAP.json").write_text(
        json.dumps(dedupe, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _findings_markdown(
    findings: list[dict[str, Any]],
    *,
    original_count: int,
    raw_counts: Counter[str],
    accepted_counts: Counter[str],
    accepted_count: int,
) -> str:
    lines = [
        f"# FINDINGS — CR-FULL {CAMPAIGN_DATE}",
        "",
        f"- Raw findings: **{original_count}**",
        f"- Normalized problem records: **{len(findings)}**",
        f"- Accepted problems: **{accepted_count}**",
        f"- Raw severity: `{dict(sorted(raw_counts.items()))}`",
        f"- Accepted severity: `{dict(sorted(accepted_counts.items()))}`",
        "",
        "| id | wave | leaf | severity | status | path | fingerprint | issue | claim |",
        "|---|---|---|---|---|---|---|---:|---|",
    ]
    for item in findings:
        issue = item.get("gh_issue") or ""
        claim = str(item["claim"]).replace("|", "\\|")
        lines.append(
            f"| `{item['id']}` | {item['wave']} | `{item['leaf']}` | {item['severity']} | "
            f"{item['status']} | `{item['path']}` | `{item['fingerprint']}` | {issue} | {claim} |"
        )
    return "\n".join(lines) + "\n"


def _triage_markdown(findings: list[dict[str, Any]]) -> str:
    lines = [
        f"# TRIAGE — CR-FULL {CAMPAIGN_DATE}",
        "",
        "Code/config/contracts and executable gates outrank CodeRabbit output.",
        "",
        "| id | status | final severity | reason | evidence |",
        "|---|---|---|---|---|",
    ]
    for item in findings:
        reason = str(
            item.get("triage_reason", "pending ground-truth reconciliation")
        ).replace("|", "\\|")
        evidence = str(item.get("evidence", "")).replace("|", "\\|")
        lines.append(
            f"| `{item['id']}` | {item['status']} | {item['severity']} | "
            f"{reason} | {evidence} |"
        )
    return "\n".join(lines) + "\n"


def _write_issue_outputs(accepted: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issue_rows = [item for item in accepted if item.get("gh_issue")]
    issue_map = {
        str(item["id"]): {
            "issue": item["gh_issue"],
            "severity": item["severity"],
            "path": item["path"],
            "url": item.get("gh_url"),
        }
        for item in issue_rows
    }
    (OUT / "ISSUES_MAP.json").write_text(
        json.dumps(issue_map, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    lines = [
        f"# Issues created or linked — CR-FULL {CAMPAIGN_DATE}",
        "",
        "| finding_id | severity | issue | path |",
        "|---|---|---:|---|",
    ]
    for item in issue_rows:
        lines.append(
            f"| `{item['id']}` | {item['severity']} | "
            f"[#{item['gh_issue']}]({item.get('gh_url', '')}) | `{item['path']}` |"
        )
    (OUT / "ISSUES_CREATED.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return issue_rows


def main() -> None:
    overrides = load_overrides()
    original_findings = raw_findings()
    findings = _split_findings(original_findings, overrides)
    dedupe = _deduplicate_findings(findings, overrides)

    _write_machine_ledgers(findings, dedupe)

    raw_counts = Counter(str(item["severity"]) for item in original_findings)
    accepted = [item for item in findings if item.get("status") == "confirm"]
    accepted_counts = Counter(str(item["severity"]) for item in accepted)
    (OUT / "FINDINGS.md").write_text(
        _findings_markdown(
            findings,
            original_count=len(original_findings),
            raw_counts=raw_counts,
            accepted_counts=accepted_counts,
            accepted_count=len(accepted),
        ),
        encoding="utf-8",
    )
    (OUT / "TRIAGE.md").write_text(_triage_markdown(findings), encoding="utf-8")
    issue_rows = _write_issue_outputs(accepted)

    print(
        json.dumps(
            {
                "raw": len(original_findings),
                "normalized_records": len(findings),
                "raw_severity": dict(sorted(raw_counts.items())),
                "accepted": len(accepted),
                "accepted_severity": dict(sorted(accepted_counts.items())),
                "published_or_linked": len(issue_rows),
                "pending": sum(item.get("status") == "pending" for item in findings),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
