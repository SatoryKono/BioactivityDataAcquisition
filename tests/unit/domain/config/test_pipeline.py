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
"""Tests for PipelineConfig configuration object.

Tests for PipelineConfig frozen dataclass with validation.
"""

from __future__ import annotations

import pytest

from bioetl.domain.config.pipeline import PipelineConfig
from bioetl.domain.config.table import TableConfig
from bioetl.domain.medallion import LoadingStrategy


def _make_config(**overrides: object) -> PipelineConfig:
    """Helper to create PipelineConfig with defaults."""
    defaults = {
        "pipeline_name": "chembl-activity",
        "provider": "chembl",
        "entity_type": "activity",
        "table": TableConfig(primary_keys=("entity_id",)),
    }
    defaults.update(overrides)  # type: ignore[arg-type]
    return PipelineConfig(**defaults)  # type: ignore[arg-type]


@pytest.mark.unit
class TestPipelineConfig:
    """Tests for PipelineConfig frozen dataclass."""

    def test_valid_creation(self) -> None:
        config = _make_config()
        assert config.pipeline_name == "chembl-activity"
        assert config.provider == "chembl"
        assert config.entity_type == "activity"
        assert config.batch_size == 100
        assert config.checkpoint_interval == 1000

    def test_pipeline_config__pipeline_name_raises__cc7046e4(self) -> None:
        with pytest.raises(ValueError, match="pipeline_name cannot be empty"):
            _make_config(pipeline_name="")

    def test_pipeline_config__provider_raises__de1d5e92(self) -> None:
        with pytest.raises(ValueError, match="provider cannot be empty"):
            _make_config(provider="")

    def test_pipeline_config__entity_type_raises__45b27978(self) -> None:
        with pytest.raises(ValueError, match="entity_type cannot be empty"):
            _make_config(entity_type="")

    def test_pipeline_config__batch_size_raises__a6f2d4df(self) -> None:
        with pytest.raises(ValueError, match="batch_size must be positive"):
            _make_config(batch_size=0)

    def test_pipeline_config__interval_raises__536a13f2(self) -> None:
        with pytest.raises(ValueError, match="checkpoint_interval must be positive"):
            _make_config(checkpoint_interval=0)

    def test_pipeline_config__primary_keys_raises__cb63270b(self) -> None:
        with pytest.raises(ValueError, match="primary_keys cannot be empty"):
            _make_config(table=TableConfig(primary_keys=()))

    def test_lock_key(self) -> None:
        config = _make_config()
        assert config.lock_key == "pipeline:chembl-activity"

    def test_effective_silver_table_with_table(self) -> None:
        config = _make_config(
            table=TableConfig(
                primary_keys=("entity_id",),
                silver_table="custom.silver",
            )
        )
        assert config.effective_silver_table == "custom.silver"

    def test_effective_silver_table_fallback(self) -> None:
        config = _make_config()
        assert config.effective_silver_table == "chembl.activity"

    def test_effective_gold_table_with_table(self) -> None:
        config = _make_config(
            table=TableConfig(
                primary_keys=("entity_id",),
                gold_table="custom.gold",
            )
        )
        assert config.effective_gold_table == "custom.gold"

    def test_effective_gold_table_fallback(self) -> None:
        config = _make_config()
        assert config.effective_gold_table == "chembl.activity"

    def test_fields_list_to_tuple(self) -> None:
        config = _make_config(fields=["a", "b"])
        assert isinstance(config.fields, tuple)
        assert config.fields == ("a", "b")

    def test_pipeline_config__string_conversion__58ad87a5(self) -> None:
        config = _make_config(loading_strategy="full_scan_only")
        assert config.loading_strategy == LoadingStrategy.FULL_SCAN_ONLY

    def test_loading_strategy_none(self) -> None:
        config = _make_config(loading_strategy=None)
        assert config.loading_strategy is None

    def test_loading_strategy_enum(self) -> None:
        config = _make_config(loading_strategy=LoadingStrategy.FULL_SCAN_ONLY)
        assert config.loading_strategy == LoadingStrategy.FULL_SCAN_ONLY
