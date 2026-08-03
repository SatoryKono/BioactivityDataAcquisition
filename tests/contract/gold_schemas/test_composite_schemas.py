# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Contract tests for composite Gold schemas and published contracts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bioetl.domain.contracts.gold.composite import (
    CompositeActivityGoldSchema,
    CompositeAssayGoldSchema,
    CompositeMoleculeGoldSchema,
    CompositePublicationGoldSchema,
    CompositeTargetGoldSchema,
)

CONTRACTS_DIR = Path("docs/04-reference/contracts/gold")


def _required_composite_columns() -> set[str]:
    # Note: content_hash is excluded from Gold layer by FieldGroupRegistry
    # (SYSTEM_METADATA group, include_in_gold=False). It lives in Silver only.
    # Occurrence-scoped provenance fields also live in sidecars/control-plane,
    # not in persisted Gold rows.
    return {
        "entity_id",
        "_dq_warn",
        "_dq_error",
        "_index",
        "_source_providers",
        "_enrichment_status",
    }


@pytest.mark.contracts
@pytest.mark.no_api
class TestCompositeGoldSchemaContract:
    """Validate composite Gold schema contracts and DataFrameModel settings."""

    @pytest.mark.parametrize(
        "schema_cls",
        [
            CompositeActivityGoldSchema,
            CompositeAssayGoldSchema,
            CompositeMoleculeGoldSchema,
            CompositePublicationGoldSchema,
            CompositeTargetGoldSchema,
        ],
    )
    def test_schema_has_required_columns(self, schema_cls: type) -> None:
        """Composite DataFrameModel contains mandatory persisted DQ/lineage fields."""
        schema = schema_cls.to_schema()
        columns = set(schema.columns.keys())
        missing = _required_composite_columns() - columns
        assert not missing, f"{schema_cls.__name__} missing required columns: {missing}"

    @pytest.mark.parametrize(
        "schema_cls",
        [
            CompositeActivityGoldSchema,
            CompositeAssayGoldSchema,
            CompositeMoleculeGoldSchema,
            CompositePublicationGoldSchema,
            CompositeTargetGoldSchema,
        ],
    )
    def test_schema_strict_mode_true(self, schema_cls: type) -> None:
        """Composite Gold contracts are strict like the rest of the Gold layer."""
        strict_value = getattr(schema_cls.Config, "strict", None)
        assert strict_value is True


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
        """Published JSON contract contains expected persisted fields and descriptions."""
        path = CONTRACTS_DIR / filename
        assert path.exists(), f"Missing contract file: {path}"

        contract = json.loads(path.read_text(encoding="utf-8"))
        properties = contract.get("properties", {})

        # JSON contracts may still document content_hash for Silver reference,
        # but it is not required in Gold output (excluded by FieldGroupRegistry).
        required_in_gold = _required_composite_columns()
        missing = required_in_gold - set(properties.keys())
        assert not missing, f"{filename} missing contract properties: {missing}"

        assert properties["entity_id"]["description"] == entity_description

    def test_composite_activity_taxonomy_id_is_published_with_integer_typing(
        self,
    ) -> None:
        path = CONTRACTS_DIR / "composite_activity_v1.0.json"
        contract = json.loads(path.read_text(encoding="utf-8"))
        taxonomy = contract["properties"]["taxonomy_id"]

        assert taxonomy["type"] == ["integer", "null"]
        assert taxonomy["nullable"] is True

    def test_composite_assay_cell_line_fields_publish_optional_string_contracts(
        self,
    ) -> None:
        schema = CompositeAssayGoldSchema.to_schema()
        path = CONTRACTS_DIR / "composite_assay_v1.0.json"
        contract = json.loads(path.read_text(encoding="utf-8"))

        for field_name in ("cell_type", "clo_id"):
            column = schema.columns[field_name]
            property_payload = contract["properties"][field_name]

            assert column.nullable is True
            assert property_payload["type"] == ["string", "null"]
            assert property_payload["nullable"] is True
