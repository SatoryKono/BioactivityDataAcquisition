"""Contract tests for PK consistency between pipeline config, Silver schema, and Gold JSON contract."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from bioetl.infrastructure.config.pipeline_config_api import load_pipeline_config
from tests.contract.silver_schemas.conftest import (
    SILVER_SCHEMAS,
    extract_field_metadata,
)

ENTITIES_DIR = Path("configs/entities")
GOLD_CONTRACTS_DIR = Path("docs/04-reference/contracts/gold")


@pytest.mark.contracts
@pytest.mark.no_api
class TestGoldPkConsistency:
    """Ensure business/technical PK naming consistency across layers (ADR-034)."""

    @pytest.mark.parametrize("schema_name", sorted(SILVER_SCHEMAS.keys()))
    def test_pk_fields_exist_in_gold_and_silver(self, schema_name: str) -> None:
        config = load_pipeline_config(schema_name)

        business_pks = list(config.business_primary_keys)
        technical_pk = config.technical_primary_key

        contract_path = GOLD_CONTRACTS_DIR / f"{schema_name}_v1.0.json"
        assert contract_path.exists(), (
            f"Missing Gold contract for {schema_name}: {contract_path}. "
            "Add/update contract snapshot to keep schema contract coverage complete."
        )

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
            p for p in ENTITIES_DIR.rglob("*.yaml") if not p.name.startswith("_")
        )
        violations: list[str] = []

        for path in pipeline_files:
            with path.open(encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
            pipeline_cfg = raw.get("pipeline")
            if not isinstance(pipeline_cfg, dict):
                violations.append(f"{path}: missing pipeline section")
                continue
            if "business_primary_keys" not in pipeline_cfg:
                violations.append(f"{path}: missing business_primary_keys")
            if "technical_primary_key" in pipeline_cfg:
                # explicit value is optional; base default is allowed
                pass
            if "primary_keys" in pipeline_cfg:
                violations.append(
                    f"{path}: legacy primary_keys key must be removed from pipeline section"
                )

            # Ensure resolved config still has technical primary key from defaults.
            provider = path.parent.name
            entity = path.stem
            resolved = load_pipeline_config(f"{provider}_{entity}")
            if not resolved.technical_primary_key:
                violations.append(f"{path}: missing technical_primary_key")

        assert not violations, "\n".join(violations)
