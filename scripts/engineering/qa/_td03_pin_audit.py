#!/usr/bin/env python3
"""Pin TD-03 total tech-debt audit without shell backtick mangling."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import yaml

from scripts.engineering.qa.technical_debt_audit_registry import (
    compute_evidence_surface_sha256,
)

ROOT = Path(__file__).resolve().parents[3]


def main() -> int:
    # Assume quality evidence artifacts are already finalized.
    # Do not regenerate gates/scorecard here (would immediately stale the pin).

    sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True, cwd=ROOT
    ).strip()
    paths = [
        "configs/quality/compatibility_facade_inventory.yaml",
        "configs/quality/debt_scorecard.yaml",
        "reports/quality/architecture-quality-scorecard.json",
        "reports/quality/compatibility-importer-census.json",
        "reports/quality/dead-code-inventory.json",
        "reports/quality/debt-governance-gates.json",
        "reports/quality/module-coverage-inventory.json",
        "reports/quality/test-governance-current.json",
    ]
    evidence_hash = compute_evidence_surface_sha256(ROOT, paths)
    gates = json.loads(
        (ROOT / "reports/quality/debt-governance-gates.json").read_text(
            encoding="utf-8"
        )
    )
    inv = json.loads(
        (ROOT / "reports/quality/module-coverage-inventory.json").read_text(
            encoding="utf-8"
        )
    )
    sc = inv["summary"]["status_counts"]
    score = gates["summary"].get("architecture_quality_scorecard_integral_score")
    fail = gates["summary"].get("fail_count")
    pass_count = gates["summary"].get("pass_count")

    # Use chr(96) for backticks to avoid shell interpolation issues if wrapped.
    bt = chr(96)
    lines = [
        "# Total Technical Debt Audit: GitHub main",
        "",
        "Lifecycle status: current",
        "",
        "Audit date: 2026-07-27",
        "",
        "Audited repository: SatoryKono/BioactivityDataAcquisition",
        "",
        "Audited branch: main",
        "",
        f"Audited commit SHA: {bt}{sha}{bt}",
        "",
        f"Evidence surface SHA-256: {bt}{evidence_hash}{bt}",
        "",
        "Registry: configs/quality/technical_debt_audit_registry.yaml",
        "",
        "Refresh reason: TD-03 re-pin after TD-01..TD-10 closeout. No debt budget growth.",
        "",
        "## Executive summary",
        "",
        (
            f"1. Debt-governance: integral score {score}, "
            f"fail_count={fail}, pass_count={pass_count}."
        ),
        (
            "1. Module inventory: fully_covered="
            f"{sc.get('fully_covered')}, partially_covered="
            f"{sc.get('partially_covered')}, uncovered="
            f"{sc.get('uncovered', 0)}, unmeasured={sc.get('unmeasured', 0)}."
        ),
        "1. Hotspot composition_runtime_builders duplication_clusters = 0 (TD-06).",
        "1. Constructor waivers 19 to 10 (TD-07).",
        "1. Scripts zero-ref budget green with untriaged 0 (TD-01/TD-02).",
        "1. Compatibility transition/sunset/expired 0/0/0; twin pairs 0 (TD-10).",
        "1. Closeout inventory fold fraction >= 0.25 (TD-05).",
        "1. Partial-coverage top-50 + domain tranche (TD-04).",
        "1. infrastructure.config sunset design (TD-08); public API hygiene (TD-09).",
        "",
        "## Reproducibility",
        "",
        "python -m scripts.engineering.qa report-debt-governance-gates --update",
        "python -m scripts.engineering.qa validate-technical-debt-audit --json",
        "",
    ]

    src = ROOT / "reports/quality/total-tech-debt-audit-main-current.md"
    archive = (
        ROOT / "docs/99-archive/reports/quality/total-tech-debt-audit-main-2026-07-23.md"
    )
    archive.parent.mkdir(parents=True, exist_ok=True)
    if src.exists() and not archive.exists():
        shutil.copy2(src, archive)
    src.write_text("\n".join(lines), encoding="utf-8")

    reg_path = ROOT / "configs/quality/technical_debt_audit_registry.yaml"
    reg = yaml.safe_load(reg_path.read_text(encoding="utf-8"))
    audits = []
    for record in reg.get("audits", []):
        if record.get("id") == "total-tech-debt-main-2026-07-27":
            continue
        if record.get("status") == "current":
            record = dict(record)
            record["status"] = "superseded"
            record["report_path"] = (
                "docs/99-archive/reports/quality/total-tech-debt-audit-main-2026-07-23.md"
            )
            record["superseded_by"] = "total-tech-debt-main-2026-07-27"
            record["superseded_on"] = "2026-07-27"
        audits.append(record)
    new = {
        "id": "total-tech-debt-main-2026-07-27",
        "status": "current",
        "report_path": "reports/quality/total-tech-debt-audit-main-current.md",
        "audited_commit_sha": sha,
        "evidence_surface_sha256": evidence_hash,
        "evidence_paths": paths,
        "reviewed_on": "2026-07-27",
        "linked_issue": "#6619",
    }
    reg["current_audit_id"] = new["id"]
    reg["audits"] = [new] + audits
    reg_path.write_text(
        yaml.safe_dump(reg, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    print("pinned", sha, evidence_hash[:16])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
