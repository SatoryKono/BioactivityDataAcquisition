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
    assert payload["schema_version"] == "contract-coverage-matrix-v2"
    assert payload["row_count"] == 1
    assert payload["covered_gold_enabled_count"] == 1
    assert "effective runtime state" in payload["semantics"]["gold_enabled"].lower()


def test_build_payload_distinguishes_disabled_runtime_from_contract_coverage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A disabled sink is excluded, not counted as a missing Gold contract."""
    monkeypatch.setattr(
        matrix,
        "_collect_rows",
        lambda: [
            {
                "pipeline_name": "chembl_example",
                "gold_enabled": False,
                "parity_status": "excluded",
                "constraint_completeness_status": "excluded",
                "golden_test_evidence_declared": True,
                "contract_ref": "chembl.example",
                "exclusion_reason": "gold_runtime_disabled",
            }
        ],
    )

    payload = matrix.build_payload(snapshot_date="2026-07-23")

    assert payload["gold_enabled_count"] == 0
    assert payload["covered_gold_enabled_count"] == 0
    assert payload["missing_gold_enabled_count"] == 0
    assert payload["excluded_count"] == 1
    assert payload["exclusions"] == [
        {
            "pipeline_name": "chembl_example",
            "contract_ref": "chembl.example",
            "reason": "gold_runtime_disabled",
        }
    ]
