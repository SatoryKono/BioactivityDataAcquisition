"""Unit tests for ActivityTransformer.

Tests both the main transform method and ligand efficiency extraction.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from bioetl.application.core.base_transformer.structural_policy import (
    build_structural_policy,
)
from bioetl.application.pipelines.chembl.activity_transformer import (
    ActivityTransformer,
)
from bioetl.application.core.base_transformer import FilteredOutError
from bioetl.infrastructure.config.domain_config_resolver import (
    resolve_domain_pipeline_config,
)
from bioetl.infrastructure.config.pipeline_config_loader import PipelineConfigLoader
from bioetl.domain.context import PipelineContext
from bioetl.domain.filtering import SilverFilterConfig
from bioetl.domain.schemas.chembl.activity import ActivitySchema
from bioetl.infrastructure.schemas.silver_chembl_core import CHEMBL_ACTIVITY_SCHEMA
from bioetl.infrastructure.validation.pandera_validator import PanderaSilverValidator
from tests.helpers.transformer_dependencies import build_test_transformer_dependencies
from tests.unit.application.pipelines.activity_transformer_shared import (
    SharedActivityTransformerActionTypeExtractionTests,
    SharedActivityTransformerLigandExtractionTests,
    SharedActivityTransformerTransformTests,
    mock_context,
    transformer,
)


@pytest.mark.unit
class TestActivityTransformerTransform(SharedActivityTransformerTransformTests):
    """Tests for ActivityTransformer transform method."""

    require_full_run_metadata = True

    @pytest.mark.asyncio
    async def test_transform_normalizes_bao_and_uo_identifiers(
        self, transformer, mock_context
    ):
        """Mixed-form BAO/UO identifiers should collapse to canonical underscore form."""
        record = {
            "activity_id": 12345,
            "molecule_id": "CHEMBL25",
            "bao_endpoint": " bao:0000190 ",
            "bao_format": "bao:0000218",
            "uo_units": "uo:0000065",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["bao_endpoint"] == "BAO_0000190"
        assert result["bao_format"] == "BAO_0000218"
        assert result["uo_units"] == "UO_0000065"

    @pytest.mark.asyncio
    async def test_transform_normalizes_standard_units_and_preserves_qudt_uri(
        self, transformer, mock_context
    ):
        """Canonical fields should normalize without rewriting raw unit or QUDT text."""
        record = {
            "activity_id": 12345,
            "molecule_id": "CHEMBL25",
            "standard_units": "nanomolar",
            "units": "uM",
            "qudt_units": " http://www.openphacts.org/units/Nanomolar ",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["standard_units"] == "nM"
        assert result["units"] == "uM"
        assert result["qudt_units"] == "http://www.openphacts.org/units/Nanomolar"

    @pytest.mark.asyncio
    async def test_transform_normalizes_full_activity_canonical_field_set(
        self, transformer, mock_context
    ) -> None:
        """All activity canonical fields should normalize together in one transform."""
        record = {
            "activity_id": 12345,
            "molecule_id": "CHEMBL25",
            "bao_endpoint": " bao:0000190 ",
            "bao_format": "BAO:0000218",
            "standard_units": " nanomolar ",
            "uo_units": " uo:0000065 ",
            "qudt_units": " http://www.openphacts.org/units/Nanomolar ",
            "units": "raw-uM",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["bao_endpoint"] == "BAO_0000190"
        assert result["bao_format"] == "BAO_0000218"
        assert result["standard_units"] == "nM"
        assert result["uo_units"] == "UO_0000065"
        assert result["qudt_units"] == "http://www.openphacts.org/units/Nanomolar"
        assert result["units"] == "raw-uM"

    @pytest.mark.asyncio
    async def test_transform_preserves_already_canonical_activity_fields(
        self, transformer, mock_context
    ) -> None:
        """Already canonical activity fields should remain stable after normalization."""
        record = {
            "activity_id": 12345,
            "molecule_id": "CHEMBL25",
            "bao_endpoint": "BAO_0000190",
            "bao_format": "BAO_0000218",
            "standard_units": "nM",
            "uo_units": "UO_0000065",
            "qudt_units": "http://www.openphacts.org/units/Nanomolar",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["bao_endpoint"] == "BAO_0000190"
        assert result["bao_format"] == "BAO_0000218"
        assert result["standard_units"] == "nM"
        assert result["uo_units"] == "UO_0000065"
        assert result["qudt_units"] == "http://www.openphacts.org/units/Nanomolar"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("field_name", "raw_value"),
        (
            ("bao_endpoint", "   "),
            ("bao_format", "\t"),
            ("standard_units", " "),
            ("uo_units", ""),
            ("qudt_units", "  "),
        ),
    )
    async def test_transform_normalizes_blank_canonical_fields_to_none(
        self,
        transformer,
        mock_context,
        field_name: str,
        raw_value: str,
    ) -> None:
        """Blank canonical field inputs should normalize to None before contract checks."""
        record = {
            "activity_id": 12345,
            "molecule_id": "CHEMBL25",
            field_name: raw_value,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result[field_name] is None


@pytest.mark.unit
class TestActivityTransformerLigandEfficiency(
    SharedActivityTransformerLigandExtractionTests
):
    """Tests for ligand efficiency extraction."""


@pytest.mark.unit
class TestActivityTransformerActionType(
    SharedActivityTransformerActionTypeExtractionTests
):
    """Tests for action type extraction."""


@pytest.mark.unit
class TestActivityTransformerSilverContract:
    """Regression tests for the tightened chembl_activity Silver contract."""

    @staticmethod
    def _valid_contract_record() -> dict[str, object]:
        """Return a chembl_activity record satisfying the stricter Silver contract."""
        return {
            "activity_id": 12345,
            "molecule_chembl_id": "CHEMBL25",
            "target_chembl_id": "CHEMBL1862",
            "assay_chembl_id": "CHEMBL1234567",
            "document_chembl_id": "CHEMBL998877",
            "record_id": 100,
            "src_id": 1,
            "canonical_smiles": "CC(=O)Oc1ccccc1C(=O)O",
            "target_organism": "Homo sapiens",
            "target_tax_id": 9606,
            "assay_type": "B",
            "assay_description": "Binding assay",
            "bao_endpoint": "BAO_0000019",
            "bao_format": "BAO_0000219",
            "bao_label": "single protein format",
            "relation": "=",
            "value": 10.5,
            "units": "nM",
            "standard_type": "IC50",
            "standard_relation": "=",
            "standard_value": 10.5,
            "standard_units": "nM",
            "standard_flag": 1,
            "pchembl_value": 8.0,
            "uo_units": "UO_0000065",
            "document_journal": "Journal of Testing",
            "document_year": 2024,
            "potential_duplicate": 0,
        }

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("missing_field",),
        (
            ("canonical_smiles",),
            ("standard_units",),
            ("uo_units",),
        ),
    )
    async def test_transform_quarantines_missing_nonnullable_contract_fields(
        self,
        mock_context,
        missing_field: str,
    ) -> None:
        """Required Silver contract fields are intentionally quarantined when missing."""
        transformer = ActivityTransformer(
            provider="chembl",
            silver_filters=SilverFilterConfig(
                required_fields=(
                    "canonical_smiles",
                    "standard_units",
                    "uo_units",
                )
            ),
            dependencies=build_test_transformer_dependencies(),
        )
        record = self._valid_contract_record()
        record.pop(missing_field)

        with pytest.raises(FilteredOutError):
            await transformer.transform(mock_context, record, index=0)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("missing_field",),
        (
            ("canonical_smiles",),
            ("standard_units",),
            ("uo_units",),
        ),
    )
    async def test_transform_uses_pipeline_config_to_quarantine_missing_contract_fields(
        self,
        mock_context,
        missing_field: str,
    ) -> None:
        """chembl_activity config intentionally quarantines missing contract fields."""
        loader = PipelineConfigLoader(Path("configs"))
        yaml_config = loader.load_pipeline_config("chembl_activity")
        domain_config = resolve_domain_pipeline_config(yaml_config)
        dependencies = dataclasses.replace(
            build_test_transformer_dependencies(),
            structural_policy=build_structural_policy(
                domain_config=domain_config,
                pandera_silver_schema=ActivitySchema,
            ),
        )
        transformer = ActivityTransformer(
            provider="chembl",
            silver_filters=domain_config.silver_filters,
            gold_filters=domain_config.gold_filters,
            dependencies=dependencies,
        )

        record = self._valid_contract_record()
        record.pop(missing_field)

        with pytest.raises(FilteredOutError) as exc_info:
            await transformer.transform(mock_context, record, index=0)

        details = exc_info.value.details
        assert details["policy_stage"] == "structural"
        assert details["reason_code"] == "required_field_missing"
        assert details["field"] == missing_field
        assert details["optional_sources"] == ["silver_required_fields"]
        assert details["semantic_shadow_reason_code"] == "required_field_missing"

    @pytest.mark.asyncio
    async def test_required_field_quarantine_details_cover_all_config_required_fields(
        self,
        mock_context,
    ) -> None:
        """Every chembl_activity required field should surface structural details."""
        loader = PipelineConfigLoader(Path("configs"))
        yaml_config = loader.load_pipeline_config("chembl_activity")
        domain_config = resolve_domain_pipeline_config(yaml_config)
        dependencies = dataclasses.replace(
            build_test_transformer_dependencies(),
            structural_policy=build_structural_policy(
                domain_config=domain_config,
                pandera_silver_schema=ActivitySchema,
            ),
        )
        transformer = ActivityTransformer(
            provider="chembl",
            silver_filters=domain_config.silver_filters,
            gold_filters=domain_config.gold_filters,
            dependencies=dependencies,
        )

        result = await transformer.transform(
            mock_context,
            self._valid_contract_record(),
            index=0,
        )

        assert result is not None

        missing_in_result: list[str] = []
        assertion_failures: list[str] = []
        for field_name in domain_config.silver_filters.required_fields:
            if field_name not in result:
                missing_in_result.append(field_name)
                continue

            broken_result = dict(result)
            broken_result.pop(field_name)

            try:
                post_structural = transformer._apply_structural_policy(
                    mock_context,
                    broken_result,
                    index=0,
                )
            except FilteredOutError as error:
                details = error.details
            else:
                with pytest.raises(FilteredOutError) as exc_info:
                    transformer._apply_silver_filter(
                        mock_context,
                        post_structural,
                        index=0,
                    )
                details = exc_info.value.details

            expected_policy_stage = (
                "semantic" if field_name == "_state" else "structural"
            )
            if details.get("policy_stage") != expected_policy_stage:
                assertion_failures.append(
                    f"{field_name}: unexpected policy_stage={details.get('policy_stage')!r}"
                )
            if details.get("reason_code") != "required_field_missing":
                assertion_failures.append(
                    f"{field_name}: unexpected reason_code={details.get('reason_code')!r}"
                )
            if details.get("field") != field_name:
                assertion_failures.append(
                    f"{field_name}: unexpected field={details.get('field')!r}"
                )

        assert not missing_in_result, (
            "Required fields missing from baseline transformed record: "
            + ", ".join(sorted(missing_in_result))
        )
        assert not assertion_failures, "; ".join(assertion_failures)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("standard_type", "missing_field"),
        (
            ("Ratio", "standard_units"),
            ("Relative potency", "uo_units"),
        ),
    )
    async def test_unitless_activity_measurements_are_quarantined_when_units_missing(
        self,
        mock_context,
        standard_type: str,
        missing_field: str,
    ) -> None:
        """Unit-less activity types are intentionally quarantined by final Silver policy."""
        loader = PipelineConfigLoader(Path("configs"))
        yaml_config = loader.load_pipeline_config("chembl_activity")
        domain_config = resolve_domain_pipeline_config(yaml_config)
        dependencies = dataclasses.replace(
            build_test_transformer_dependencies(),
            structural_policy=build_structural_policy(
                domain_config=domain_config,
                pandera_silver_schema=ActivitySchema,
            ),
        )
        transformer = ActivityTransformer(
            provider="chembl",
            silver_filters=domain_config.silver_filters,
            gold_filters=domain_config.gold_filters,
            dependencies=dependencies,
        )

        record = self._valid_contract_record()
        record["type"] = standard_type
        record["standard_type"] = standard_type
        record["text_value"] = "unit-less measurement"
        record["standard_text_value"] = "unit-less measurement"
        record.pop(missing_field)

        with pytest.raises(FilteredOutError) as exc_info:
            await transformer.transform(mock_context, record, index=0)

        details = exc_info.value.details
        assert details["policy_stage"] == "structural"
        assert details["reason_code"] == "required_field_missing"
        assert details["field"] == missing_field

    @pytest.mark.asyncio
    async def test_transform_output_validates_with_stateful_activity_schema(
        self,
        transformer,
        mock_context,
    ) -> None:
        """Silver validation should now accept and require _state metadata."""
        result = await transformer.transform(
            mock_context,
            self._valid_contract_record(),
            index=0,
        )

        assert result is not None
        result["_source_batch_id"] = "batch-001"

        validator = PanderaSilverValidator(ActivitySchema.to_schema(), strict=True)
        validation_result = validator.validate([result])

        assert result["_state"] == "validated"
        assert validation_result.valid, validation_result.errors

    def test_activity_arrow_schema_marks_contract_fields_non_nullable(self) -> None:
        """Committed Arrow schema should reflect the stricter Silver nullability."""
        expected_non_nullable = (
            "_source_batch_id",
            "_state",
            "assay_id",
            "target_id",
            "publication_id",
            "record_id",
            "canonical_smiles",
            "publication_year",
            "standard_value",
        )

        for field_name in expected_non_nullable:
            assert CHEMBL_ACTIVITY_SCHEMA.field(field_name).nullable is False
