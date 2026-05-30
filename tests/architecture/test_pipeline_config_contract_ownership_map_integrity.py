"""Integrity guard for pipeline-config-contract ownership map rows."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
JSON_ARTIFACT = (
    PROJECT_ROOT / "reports" / "quality" / "pipeline-config-contract-ownership-map.json"
)


def _load_rows() -> list[dict[str, object]]:
    payload = json.loads(JSON_ARTIFACT.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    rows = payload.get("rows")
    assert isinstance(rows, list)
    normalized: list[dict[str, object]] = []
    for row in rows:
        assert isinstance(row, dict)
        normalized.append(row)
    return normalized


@pytest.mark.architecture
def test_pipeline_config_contract_ownership_map_rows_reference_existing_artifacts() -> None:
    """Ownership map rows must point at committed config, contract, and code owners."""
    assert JSON_ARTIFACT.exists(), (
        "Missing pipeline-config-contract ownership map artifact; regenerate with "
        "python -m scripts.engineering.qa report-pipeline-config-contract-ownership-map"
    )

    violations: list[str] = []
    for row in _load_rows():
        pipeline_name = row.get("pipeline_name")
        assert isinstance(pipeline_name, str)

        for field in ("config_path", "contract_config_path", "pipeline_code_owner"):
            rel_path = row.get(field)
            if not isinstance(rel_path, str) or not rel_path:
                violations.append(f"{pipeline_name}: missing {field}")
                continue
            if not (PROJECT_ROOT / rel_path).is_file():
                violations.append(f"{pipeline_name}: missing file for {field}={rel_path}")

        provider = row.get("provider")
        if provider == "composite":
            composite_path = row.get("composite_runtime_config_path")
            if not isinstance(composite_path, str) or not composite_path:
                violations.append(
                    f"{pipeline_name}: composite rows require composite_runtime_config_path"
                )
            elif not (PROJECT_ROOT / composite_path).is_file():
                violations.append(
                    f"{pipeline_name}: missing composite runtime config {composite_path}"
                )

    assert not violations, "\n".join(violations)


@pytest.mark.architecture
def test_pipeline_config_contract_ownership_map_contract_refs_match_contract_yaml() -> None:
    """Each ownership row contract_ref must match the committed contract YAML."""
    violations: list[str] = []
    for row in _load_rows():
        pipeline_name = row.get("pipeline_name")
        contract_ref = row.get("contract_ref")
        contract_path = row.get("contract_config_path")
        if (
            not isinstance(pipeline_name, str)
            or not isinstance(contract_ref, str)
            or not isinstance(contract_path, str)
            or not contract_path
        ):
            continue

        payload = yaml.safe_load(
            (PROJECT_ROOT / contract_path).read_text(encoding="utf-8")
        )
        if not isinstance(payload, dict):
            violations.append(f"{pipeline_name}: contract payload is not a mapping")
            continue
        declared_ref = payload.get("contract_ref")
        if declared_ref != contract_ref:
            violations.append(
                f"{pipeline_name}: contract_ref mismatch "
                f"row={contract_ref!r} yaml={declared_ref!r}"
            )

    assert not violations, "\n".join(violations)
