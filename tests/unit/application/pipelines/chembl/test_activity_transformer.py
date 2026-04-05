"""Unit tests for ActivityTransformer.

Tests both the main transform method and ligand efficiency extraction.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

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
from bioetl.domain.types import RunType
from bioetl.infrastructure.schemas.silver_chembl_core import CHEMBL_ACTIVITY_SCHEMA
from bioetl.infrastructure.validation.pandera_validator import PanderaSilverValidator
from tests.helpers.transformer_dependencies import build_test_transformer_dependencies


@pytest.fixture
def transformer():
    """Fixture for ActivityTransformer instance."""
    return ActivityTransformer(
        provider="chembl", dependencies=build_test_transformer_dependencies()
    )


@pytest.fixture
def mock_context():
    """Create a mock pipeline context."""
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)
    mock_logger.warning = MagicMock()
    return PipelineContext(
        run_id=uuid4(),
        run_type=RunType.INCREMENTAL,
        logger=mock_logger,
    )


@pytest.mark.unit
class TestActivityTransformerTransform:
    """Tests for ActivityTransformer transform method."""

    @pytest.mark.asyncio
    async def test_transform_valid_record(self, transformer, mock_context):
        """Test transformation of valid activity record."""
        record = {
            "activity_id": 12345,
            "molecule_id": "CHEMBL25",
            "target_id": "CHEMBL1862",
            "assay_id": "CHEMBL1234567",
            "standard_type": "IC50",
            "standard_value": 10.5,
            "standard_units": "nM",
            "pchembl_value": 8.0,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["activity_id"] == "12345"
        assert result["molecule_id"] == "CHEMBL25"
        assert result["target_id"] == "CHEMBL1862"
        assert result["standard_type"] == "IC50"
        assert result["standard_value"] == pytest.approx(10.5)
        assert result["pchembl_value"] == pytest.approx(8.0)
        assert "entity_id" in result
        assert "content_hash" in result
        assert "_run_id" in result

    @pytest.mark.asyncio
    async def test_transform_missing_activity_id(self, transformer, mock_context):
        """Test transformation returns None when activity_id is missing."""
        record = {
            "molecule_id": "CHEMBL25",
            "target_id": "CHEMBL1862",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None

    @pytest.mark.asyncio
    async def test_transform_missing_molecule_id(self, transformer, mock_context):
        """Test transformation returns None when molecule_id is missing."""
        record = {
            "activity_id": 12345,
            "target_id": "CHEMBL1862",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None

    @pytest.mark.asyncio
    async def test_transform_with_ligand_efficiency(self, transformer, mock_context):
        """Test transformation with ligand efficiency data."""
        record = {
            "activity_id": 12345,
            "molecule_id": "CHEMBL25",
            "ligand_efficiency": {
                "bei": "14.06",
                "le": "0.26",
                "lle": "1.30",
                "sei": "5.56",
            },
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["ligand_efficiency_bei"] == pytest.approx(14.06)
        assert result["ligand_efficiency_le"] == pytest.approx(0.26)
        assert result["ligand_efficiency_lle"] == pytest.approx(1.30)
        assert result["ligand_efficiency_sei"] == pytest.approx(5.56)

    @pytest.mark.asyncio
    async def test_transform_with_all_core_fields(self, transformer, mock_context):
        """Test transformation with all core activity fields."""
        record = {
            "activity_id": 99999,
            "molecule_id": "CHEMBL25",
            "target_id": "CHEMBL1862",
            "assay_id": "CHEMBL123",
            "publication_id": "CHEMBL456",
            "record_id": 100,
            "src_id": 1,
            "canonical_smiles": "CC(=O)Oc1ccccc1C(=O)O",
            "molecule_pref_name": "ASPIRIN",
            "parent_molecule_id": "CHEMBL25",
            "target_pref_name": "Cyclooxygenase-2",
            "target_organism": "Homo sapiens",
            "target_tax_id": 9606,  # Source API field name
            "assay_type": "B",
            "assay_description": "Binding assay",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["canonical_smiles"] == "CC(=O)Oc1ccccc1C(=O)O"
        assert result["molecule_pref_name"] == "ASPIRIN"
        assert result["target_pref_name"] == "Cyclooxygenase-2"
        assert result["target_organism"] == "Homo sapiens"
        assert result["target_taxonomy_id"] == 9606  # Standardized output
        assert result["assay_type"] == "B"

    @pytest.mark.asyncio
    async def test_transform_with_activity_values(self, transformer, mock_context):
        """Test transformation with raw and standardized activity values."""
        record = {
            "activity_id": 12345,
            "molecule_id": "CHEMBL25",
            "type": "IC50",
            "value": 10.5,
            "units": "nM",
            "relation": "=",
            "upper_value": 20.0,
            "text_value": "Active",
            "standard_type": "IC50",
            "standard_value": 10.5,
            "standard_units": "nM",
            "standard_relation": "=",
            "standard_upper_value": 20.0,
            "standard_text_value": "Active",
            "standard_flag": 1,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["type"] == "IC50"
        assert result["value"] == pytest.approx(10.5)
        assert result["standard_value"] == pytest.approx(10.5)
        assert result["standard_flag"] == 1

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

    @pytest.mark.asyncio
    async def test_transform_with_quality_annotations(self, transformer, mock_context):
        """Test transformation with data quality annotations."""
        record = {
            "activity_id": 12345,
            "molecule_id": "CHEMBL25",
            "activity_comment": "Potent inhibitor",
            "data_validity_comment": "Valid",
            "data_validity_description": "Data passed validation",
            "potential_duplicate": 0,
            "manual_curation_flag": 1,
            "original_activity_id": 98765,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["activity_comment"] == "Potent inhibitor"
        assert result["data_validity_comment"] == "Valid"
        assert result["data_validity_description"] == "Data passed validation"
        assert result["potential_duplicate"] == 0
        assert result["manual_curation_flag"] == 1
        assert result["original_activity_id"] == 98765

    @pytest.mark.asyncio
    async def test_transform_with_curation_fields_null(self, transformer, mock_context):
        """Test transformation handles nullable curation fields."""
        record = {
            "activity_id": 12345,
            "molecule_id": "CHEMBL25",
            # Curation fields are missing/null
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["manual_curation_flag"] is None
        assert result["original_activity_id"] is None
        assert result["data_validity_description"] is None

    @pytest.mark.asyncio
    async def test_transform_with_curation_flag_zero(self, transformer, mock_context):
        """Test transformation with manual_curation_flag set to 0 (not curated)."""
        record = {
            "activity_id": 12345,
            "molecule_id": "CHEMBL25",
            "manual_curation_flag": 0,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["manual_curation_flag"] == 0

    @pytest.mark.asyncio
    async def test_transform_with_json_fields_single(self, transformer, mock_context):
        """Test transformation unwraps single-element activity_properties."""
        record = {
            "activity_id": 12345,
            "molecule_id": "CHEMBL25",
            "activity_properties": [{"type": "Ki", "value": 5.0}],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        # Single-element list is unwrapped to just the dict string
        assert result.get("activity_properties") == '{"type":"Ki","value":5.0}'

    @pytest.mark.asyncio
    async def test_transform_with_json_fields_multiple(self, transformer, mock_context):
        """Test transformation keeps multi-element activity_properties as array."""
        record = {
            "activity_id": 12345,
            "molecule_id": "CHEMBL25",
            "activity_properties": [{"type": "Ki"}, {"type": "IC50"}],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        # Multi-element list stays as array string
        assert result.get("activity_properties") == '[{"type":"Ki"},{"type":"IC50"}]'

    @pytest.mark.asyncio
    async def test_transform_with_empty_activity_properties(
        self, transformer, mock_context
    ):
        """Test transformation returns None for empty activity_properties."""
        record = {
            "activity_id": 12345,
            "molecule_id": "CHEMBL25",
            "activity_properties": [],  # Empty array from ChEMBL API
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        # Empty collections are treated as None for semantic consistency
        assert result.get("activity_properties") is None

    @pytest.mark.asyncio
    async def test_transform_with_action_type(self, transformer, mock_context):
        """Test transformation with action type data (flattened structure)."""
        record = {
            "activity_id": 12345,
            "molecule_id": "CHEMBL25",
            "action_type": {
                "action_type": "INHIBITOR",
                "description": "Compound that inhibits target activity",
                "parent_type": "NEGATIVE MODULATOR",
            },
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["action_type"] == "INHIBITOR"
        assert (
            result["action_type_description"]
            == "Compound that inhibits target activity"
        )
        assert result["action_type_parent_type"] == "NEGATIVE MODULATOR"

    @pytest.mark.asyncio
    async def test_transform_with_action_type_null(self, transformer, mock_context):
        """Test transformation with null action type."""
        record = {
            "activity_id": 12345,
            "molecule_id": "CHEMBL25",
            "action_type": None,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["action_type"] is None
        assert result["action_type_description"] is None
        assert result["action_type_parent_type"] is None


@pytest.mark.unit
class TestActivityTransformerLigandEfficiency:
    """Tests for ligand efficiency extraction."""

    def test_extract_ligand_efficiency_valid_dict(self, transformer):
        """Test extraction with valid ligand efficiency dictionary."""
        le_data = {
            "bei": "14.06",
            "le": "0.26",
            "lle": "1.30",
            "sei": "5.56",
        }

        result = transformer._extract_ligand_efficiency(le_data)

        assert result["ligand_efficiency_bei"] == pytest.approx(14.06)
        assert result["ligand_efficiency_le"] == pytest.approx(0.26)
        assert result["ligand_efficiency_lle"] == pytest.approx(1.30)
        assert result["ligand_efficiency_sei"] == pytest.approx(5.56)

    def test_extract_ligand_efficiency_none(self, transformer):
        """Test extraction with None input."""
        result = transformer._extract_ligand_efficiency(None)

        assert result["ligand_efficiency_bei"] is None
        assert result["ligand_efficiency_le"] is None
        assert result["ligand_efficiency_lle"] is None
        assert result["ligand_efficiency_sei"] is None


@pytest.mark.unit
class TestActivityTransformerActionType:
    """Tests for action type extraction."""

    def test_extract_action_type_valid_dict(self, transformer):
        """Test extraction with valid action type dictionary."""
        action_data = {
            "action_type": "INHIBITOR",
            "description": "Compound that inhibits target activity",
            "parent_type": "NEGATIVE MODULATOR",
        }

        result = transformer._extract_action_type(action_data)

        assert result["action_type"] == "INHIBITOR"
        assert (
            result["action_type_description"]
            == "Compound that inhibits target activity"
        )
        assert result["action_type_parent_type"] == "NEGATIVE MODULATOR"

    def test_extract_action_type_none(self, transformer):
        """Test extraction with None input."""
        result = transformer._extract_action_type(None)

        assert result["action_type"] is None
        assert result["action_type_description"] is None
        assert result["action_type_parent_type"] is None


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
