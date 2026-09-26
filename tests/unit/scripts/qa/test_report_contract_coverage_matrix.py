# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

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
                "gold_contract_available": True,
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
    assert payload["schema_version"] == "contract-coverage-matrix-v3"
    assert payload["row_count"] == 1
    assert payload["covered_gold_enabled_count"] == 1
    assert payload["gold_contract_available_count"] == 1
    assert "effective runtime state" in payload["semantics"]["gold_enabled"].lower()
    assert "independent" in payload["semantics"]["gold_contract_available"].lower()
    assert "strict" in payload["semantics"]["gold_contract_available"].lower()


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
                "gold_contract_available": True,
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
    assert payload["gold_contract_available_count"] == 1
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


def test_gold_runtime_enabled_reads_only_sink_gold_flag() -> None:
    """Unrelated filter flags must not be treated as Gold runtime enablement."""
    assert matrix._gold_runtime_enabled({"sink": {"gold": {"enabled": False}}}) is False
    assert matrix._gold_runtime_enabled({"sink": {"gold": {}}}) is True
    assert matrix._gold_runtime_enabled({"sink": {}}) is True
    assert matrix._gold_runtime_enabled({}) is True


def test_molecule_input_filter_disabled_does_not_disable_gold_runtime() -> None:
    """Issue #6491 audit trap: filters.input_filter.enabled is not gold.enabled."""
    config_path = matrix.ENTITIES_ROOT / "chembl" / "molecule.yaml"
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert raw["filters"]["input_filter"]["enabled"] is False
    assert "enabled" not in raw["pipeline"]["sink"]["gold"]

    effective = matrix.load_pipeline_config_from_root(
        "chembl_molecule",
        configs_root=matrix.CONFIGS_ROOT,
    ).model_dump(mode="python")
    assert matrix._gold_runtime_enabled(effective) is True


def test_build_row_keeps_contract_available_when_gold_runtime_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Strict contract surfaces stay visible even when Gold writes are disabled."""

    class _FakePipeline:
        def model_dump(self, *, mode: str = "python") -> dict[str, Any]:
            assert mode == "python"
            return {
                "pipeline_name": "chembl_molecule",
                "sink": {"gold": {"enabled": False}},
                "business_primary_keys": ["molecule_id", "entity_id"],
            }

    monkeypatch.setattr(
        matrix,
        "load_pipeline_config_from_root",
        lambda pipeline_name, configs_root=None: _FakePipeline(),
    )

    config_path = matrix.ENTITIES_ROOT / "chembl" / "molecule.yaml"
    row = matrix._build_row(
        config_path=config_path,
        config_payload=yaml.safe_load(config_path.read_text(encoding="utf-8")),
        registry_entries=matrix._registry_entries(),
        test_index=matrix._contract_test_index(),
    )

    assert row["gold_enabled"] is False
    assert row["parity_status"] == "excluded"
    assert row["exclusion_reason"] == "gold_runtime_disabled"
    assert row["contract_yaml_exists"] is True
    assert row["registry_entry_exists"] is True
    assert row["pandera_contract_declared"] is True
    # Available only when Pandera + strict Gold validation are both declared.
    assert row["gold_contract_available"] is (
        row["pandera_contract_declared"] and row["gold_strict_validation_declared"]
    )
