from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.engineering.qa import report_contract_coverage_matrix as matrix


pytestmark = pytest.mark.unit


def test_existing_snapshot_date_reads_committed_value(tmp_path: Path) -> None:
    artifact = tmp_path / "contract-coverage-matrix.json"
    artifact.write_text(
        json.dumps({"snapshot_date": "2026-06-23", "rows": []}, indent=2) + "\n",
        encoding="utf-8",
    )

    assert matrix._existing_snapshot_date(artifact) == "2026-06-23"


def test_build_payload_uses_explicit_snapshot_date(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        matrix,
        "_collect_rows",
        lambda: [
            {
                "pipeline_name": "chembl_activity",
                "gold_enabled": True,
                "parity_status": "covered",
                "constraint_completeness_status": "covered",
                "golden_test_evidence_declared": True,
                "contract_ref": "chembl.activity",
                "exclusion_reason": "",
            }
        ],
    )

    payload = matrix.build_payload(snapshot_date="2026-06-23")

    assert payload["snapshot_date"] == "2026-06-23"
    assert payload["row_count"] == 1
    assert payload["covered_gold_enabled_count"] == 1
