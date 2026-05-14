"""Contract checks for semantic pair-matrix drift budgets."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from scripts.engineering.qa.check_semantic_pair_matrix_budget import (
    DEFAULT_BUDGET_PATH,
    validate_semantic_pair_matrix_budget,
)


def test_semantic_pair_matrix_budget_gate_passes_current_repo() -> None:
    result = validate_semantic_pair_matrix_budget(
        repo_root=Path("."),
        today=date(2026, 5, 14),
    )

    assert not result.findings, "\n".join(
        finding.message for finding in result.findings
    )


def test_pair_matrix_budget_records_current_critical_and_high_counts() -> None:
    result = validate_semantic_pair_matrix_budget(
        repo_root=Path("."),
        today=date(2026, 5, 14),
    )

    assert result.risk_counts["CRITICAL"] == 16
    assert result.risk_counts["HIGH"] == 333


def test_reviewed_critical_rows_are_timeboxed_and_owned() -> None:
    payload = yaml.safe_load(DEFAULT_BUDGET_PATH.read_text(encoding="utf-8"))
    reviewed_rows = payload["reviewed_critical_rows"]

    assert len(reviewed_rows) == payload["budgets"]["CRITICAL"]["max_count"]
    for row in reviewed_rows:
        assert row["row_key"]
        assert row["owner"] == "BioETL Team"
        assert row["expires_on"]
        assert row["rationale"]
