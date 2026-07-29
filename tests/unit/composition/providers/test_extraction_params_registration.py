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
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Tests for extraction_params threading from filter config to ChemblAdapter.

Verifies:
- ExtractionParams are passed from pipeline config to ChemblAdapter
- Overlap validation between extraction_params and input_filter
- Other providers handle extraction_params gracefully (empty params)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from bioetl.domain.filtering import FilterColumn, InputFilterConfig
from bioetl.domain.models.filter import ExtractionParams
from bioetl.composition.providers._config_helpers import (
    _validate_extraction_input_filter_overlap,
)


pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def logger() -> MagicMock:
    """Mock LoggerPort."""
    return MagicMock()


@pytest.fixture()
def active_extraction_params() -> ExtractionParams:
    """Non-empty ExtractionParams."""
    return ExtractionParams(
        params={
            "standard_type__in": "IC50,Ki",
            "standard_units": "nM",
            "assay_type__in": "B,F",
        }
    )


@pytest.fixture()
def empty_extraction_params() -> ExtractionParams:
    """Empty ExtractionParams."""
    return ExtractionParams.empty()


@pytest.fixture()
def enabled_input_filter() -> InputFilterConfig:
    """Enabled single-column InputFilterConfig."""
    return InputFilterConfig(
        enabled=True,
        source_path="data/input/ids.csv",
        column_name="activity_id",
        filter_field="activity_id",
        batch_size=20,
    )


@pytest.fixture()
def disabled_input_filter() -> InputFilterConfig:
    """Disabled InputFilterConfig."""
    return InputFilterConfig(enabled=False)


@pytest.fixture()
def overlapping_input_filter() -> InputFilterConfig:
    """InputFilterConfig whose filter_field overlaps extraction_params."""
    return InputFilterConfig(
        enabled=True,
        source_path="data/input/ids.csv",
        column_name="type_col",
        filter_field="standard_type__in",
        batch_size=20,
    )


@pytest.fixture()
def multi_column_overlapping_filter() -> InputFilterConfig:
    """Multi-column InputFilterConfig with overlapping column."""
    return InputFilterConfig(
        enabled=True,
        source_path="data/input/multi.csv",
        columns=(
            FilterColumn(column_name="type_col", filter_field="standard_type__in"),
            FilterColumn(column_name="unit_col", filter_field="target_id"),
        ),
        batch_size=20,
    )


# ---------------------------------------------------------------------------
# Overlap Validation Tests
# ---------------------------------------------------------------------------


class TestOverlapValidation:
    """Tests for _validate_extraction_input_filter_overlap."""

    def test_overlap_validation_warns_on_conflict(
        self,
        active_extraction_params: ExtractionParams,
        overlapping_input_filter: InputFilterConfig,
        logger: MagicMock,
    ) -> None:
        """Warning is logged when filter_field overlaps extraction_params key."""
        _validate_extraction_input_filter_overlap(
            active_extraction_params, overlapping_input_filter, logger
        )

        logger.warning.assert_called_once()
        call_args = logger.warning.call_args
        assert call_args[0][0] == "extraction_params_input_filter_overlap"
        assert call_args[1]["overlap_field"] == "standard_type__in"

    def test_overlap_validation_silent_when_no_overlap(
        self,
        active_extraction_params: ExtractionParams,
        enabled_input_filter: InputFilterConfig,
        logger: MagicMock,
    ) -> None:
        """No warning when filter_field does not overlap extraction_params."""
        _validate_extraction_input_filter_overlap(
            active_extraction_params, enabled_input_filter, logger
        )

        logger.warning.assert_not_called()

    def test_overlap_validation_skipped_when_input_filter_disabled(
        self,
        active_extraction_params: ExtractionParams,
        disabled_input_filter: InputFilterConfig,
        logger: MagicMock,
    ) -> None:
        """No warning when input_filter is disabled."""
        _validate_extraction_input_filter_overlap(
            active_extraction_params, disabled_input_filter, logger
        )

        logger.warning.assert_not_called()

    def test_overlap_validation_skipped_when_extraction_empty(
        self,
        empty_extraction_params: ExtractionParams,
        enabled_input_filter: InputFilterConfig,
        logger: MagicMock,
    ) -> None:
        """No warning when extraction_params is empty."""
        _validate_extraction_input_filter_overlap(
            empty_extraction_params, enabled_input_filter, logger
        )

        logger.warning.assert_not_called()

    def test_overlap_validation_multi_column_overlap(
        self,
        active_extraction_params: ExtractionParams,
        multi_column_overlapping_filter: InputFilterConfig,
        logger: MagicMock,
    ) -> None:
        """Warning logged for each overlapping column in multi-column mode."""
        _validate_extraction_input_filter_overlap(
            active_extraction_params, multi_column_overlapping_filter, logger
        )

        # Only standard_type__in overlaps, target_id does not
        assert logger.warning.call_count == 1
        call_args = logger.warning.call_args
        assert call_args[1]["overlap_field"] == "standard_type__in"


# ---------------------------------------------------------------------------
# ChemblAdapter extraction_params passthrough
# ---------------------------------------------------------------------------


class TestExtractionParamsPassedToAdapter:
    """Test that extraction_params reaches ChemblAdapter via DataSourceFactory."""

    @patch(
        "bioetl.composition.providers.registration_bio._get_adapter_config",
    )
    def test_extraction_params_passed_to_adapter(
        self,
        mock_get_adapter_config: MagicMock,
    ) -> None:
        """ExtractionParams from pipeline_config reaches DataSourceFactory.create."""
        from bioetl.composition.providers.registration_bio import (
            _create_chembl_data_source,
        )

        # Setup mocks
        support = MagicMock()
        mock_get_adapter_config.return_value = MagicMock()

        mock_settings = MagicMock()
        mock_logger = MagicMock()
        mock_pipeline_config = MagicMock()
        mock_pipeline_config.extraction_params = {
            "standard_type__in": "IC50,Ki",
            "standard_units": "nM",
        }
        mock_pipeline_config.entity_type = "activity"

        _create_chembl_data_source(
            settings=mock_settings,
            pipeline_config=mock_pipeline_config,
            logger=mock_logger,
            assembly_support=support,
        )

        # Verify injected adapter factory was called with extraction_params
        support.create_adapter.assert_called_once()
        call_kwargs = support.create_adapter.call_args
        extraction_params = call_kwargs[1].get("extraction_params")

        assert extraction_params is not None
        assert isinstance(extraction_params, ExtractionParams)
        assert extraction_params.params["standard_type__in"] == "IC50,Ki"
        assert extraction_params.params["standard_units"] == "nM"

    @patch(
        "bioetl.composition.providers.registration_bio._get_adapter_config",
    )
    def test_empty_extraction_params_when_not_configured(
        self,
        mock_get_adapter_config: MagicMock,
    ) -> None:
        """Empty ExtractionParams when pipeline has no extraction_params."""
        from bioetl.composition.providers.registration_bio import (
            _create_chembl_data_source,
        )

        support = MagicMock()
        mock_get_adapter_config.return_value = MagicMock()

        mock_settings = MagicMock()
        mock_logger = MagicMock()
        mock_pipeline_config = MagicMock()
        mock_pipeline_config.extraction_params = {}
        mock_pipeline_config.entity_type = "activity"

        _create_chembl_data_source(
            settings=mock_settings,
            pipeline_config=mock_pipeline_config,
            logger=mock_logger,
            assembly_support=support,
        )

        call_kwargs = support.create_adapter.call_args[1]
        extraction_params = call_kwargs["extraction_params"]
        assert extraction_params.is_empty


# ---------------------------------------------------------------------------
# Other providers: unpack triple without error
# ---------------------------------------------------------------------------


class TestOtherProvidersUnpackTriple:
    """Verify PipelineYamlConfig.extraction_params defaults to empty dict.

    Other providers (PubChem, UniProt, etc.) do not use extraction_params
    but must not break when the field is present in pipeline config.
    """

    def test_pipeline_config_extraction_params_defaults_empty(self) -> None:
        """PipelineYamlConfig has extraction_params defaulting to empty dict."""
        from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

        config = PipelineYamlConfig(
            pipeline_name="pubchem_compound",
            provider="pubchem",
            entity_type="compound",
            business_primary_keys=["compound_id"],
            silver_table="compound",
        )
        assert config.extraction_params == {}

    def test_pipeline_config_accepts_extraction_params(self) -> None:
        """PipelineYamlConfig accepts extraction_params from YAML."""
        from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

        config = PipelineYamlConfig(
            pipeline_name="chembl_activity",
            provider="chembl",
            entity_type="activity",
            business_primary_keys=["activity_id"],
            silver_table="activity",
            extraction_params={
                "standard_type__in": "IC50,Ki",
                "standard_units": "nM",
            },
        )
        assert config.extraction_params["standard_type__in"] == "IC50,Ki"
        assert config.extraction_params["standard_units"] == "nM"
