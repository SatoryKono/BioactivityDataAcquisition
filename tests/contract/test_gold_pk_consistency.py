"""Contract tests for PK consistency between pipeline config, Silver schema, and Gold JSON contract."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from tests.contract.silver_schemas.conftest import (
    SILVER_SCHEMAS,
    extract_field_metadata,
)

PIPELINES_DIR = Path("configs/pipelines")
GOLD_CONTRACTS_DIR = Path("docs/04-reference/contracts/gold")


@pytest.mark.contracts
@pytest.mark.no_api
class TestGoldPkConsistency:
    """Ensure business/technical PK naming consistency across layers (ADR-034)."""

    @pytest.mark.parametrize("schema_name", sorted(SILVER_SCHEMAS.keys()))
    def test_pk_fields_exist_in_gold_and_silver(self, schema_name: str) -> None:
        provider, entity = schema_name.split("_", 1)
        config_path = PIPELINES_DIR / provider / f"{entity}.yaml"
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))

        business_pks = config["business_primary_keys"]
        technical_pk = config["technical_primary_key"]

        contract_path = GOLD_CONTRACTS_DIR / f"{schema_name}_v1.0.json"
        if not contract_path.exists():
            pytest.skip(f"No Gold contract for {schema_name}")

        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        contract_props = set(contract.get("properties", {}).keys())

        missing_in_gold = [pk for pk in business_pks if pk not in contract_props]
        assert not missing_in_gold, (
            f"{schema_name}: business_primary_keys missing in Gold contract: {missing_in_gold}"
        )

        silver_fields = extract_field_metadata(SILVER_SCHEMAS[schema_name])
        assert technical_pk in silver_fields, (
            f"{schema_name}: technical_primary_key '{technical_pk}' missing in Silver schema"
        )

    def test_pipeline_configs_use_new_pk_naming(self) -> None:
        pipeline_files = sorted(
            p for p in PIPELINES_DIR.rglob("*.yaml") if not p.name.startswith("_")
        )
        violations: list[str] = []

        for path in pipeline_files:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            # Composite pipelines have different structure (no direct PKs)
            if "composite" in data:
                continue
            if "business_primary_keys" not in data:
                violations.append(f"{path}: missing business_primary_keys")
            if "technical_primary_key" not in data:
                violations.append(f"{path}: missing technical_primary_key")
            if "primary_keys" in data:
                violations.append(f"{path}: legacy primary_keys key must be removed")

        assert not violations, "\n".join(violations)
