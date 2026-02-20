"""Contract tests for composite Gold schemas and published contracts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bioetl.domain.contracts.gold.composite import (
    CompositeMoleculeGoldSchema,
    CompositePublicationGoldSchema,
)

CONTRACTS_DIR = Path("docs/04-reference/contracts/gold")


def _required_composite_columns() -> set[str]:
    return {
        "entity_id",
        "content_hash",
        "_dq_warn",
        "_dq_error",
        "_run_id",
        "_run_type",
        "_ingestion_ts",
        "_index",
        "_composite_run_id",
        "_source_providers",
        "_enrichment_status",
        "_lineage_created_at",
    }


@pytest.mark.contracts
@pytest.mark.no_api
class TestCompositeGoldSchemaContract:
    """Validate composite Gold schema contracts and DataFrameModel settings."""

    @pytest.mark.parametrize(
        "schema_cls",
        [CompositePublicationGoldSchema, CompositeMoleculeGoldSchema],
    )
    def test_schema_has_required_columns(self, schema_cls: type) -> None:
        """Composite DataFrameModel contains mandatory lineage and DQ fields."""
        schema = schema_cls.to_schema()
        columns = set(schema.columns.keys())
        missing = _required_composite_columns() - columns
        assert not missing, f"{schema_cls.__name__} missing required columns: {missing}"

    @pytest.mark.parametrize(
        "schema_cls",
        [CompositePublicationGoldSchema, CompositeMoleculeGoldSchema],
    )
    def test_schema_strict_mode_false(self, schema_cls: type) -> None:
        """Composite schema uses strict=False to allow extra enricher columns."""
        strict_value = getattr(schema_cls.Config, "strict", None)
        assert strict_value is False


@pytest.mark.contracts
@pytest.mark.no_api
class TestCompositeGoldJsonContracts:
    """Validate published JSON contracts for composite Gold entities."""

    @pytest.mark.parametrize(
        "filename,entity_description",
        [
            (
                "composite_publication_v1.0.json",
                "Stable business identifier for merged publication entity.",
            ),
            (
                "composite_molecule_v1.0.json",
                "Stable business identifier for merged molecule entity.",
            ),
        ],
    )
    def test_contract_file_has_required_fields(
        self,
        filename: str,
        entity_description: str,
    ) -> None:
        """Published JSON contract contains expected required fields and descriptions."""
        path = CONTRACTS_DIR / filename
        assert path.exists(), f"Missing contract file: {path}"

        contract = json.loads(path.read_text(encoding="utf-8"))
        properties = contract.get("properties", {})

        missing = _required_composite_columns() - set(properties.keys())
        assert not missing, f"{filename} missing contract properties: {missing}"

        assert properties["entity_id"]["description"] == entity_description
        assert (
            properties["content_hash"]["description"]
            == "Deterministic SHA-256 hash for SCD Type 2 change tracking."
        )
