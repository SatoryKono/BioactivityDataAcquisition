"""Tests for _MedallionConfigValidator (internal helper in preflight_service).

Tests the medallion validation functionality integrated into PreflightService.
These tests validate the internal _MedallionConfigValidator class.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from bioetl.application.core.preflight.service import (
    _MedallionConfigValidator as MedallionConfigValidator,
)
from bioetl.domain.medallion import WriteModePolicy
from bioetl.domain.types import RunType

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_logger() -> Mock:
    """Create mock logger."""
    logger = Mock()
    logger.warning = Mock()
    logger.debug = Mock()
    return logger


@pytest.fixture
def mock_config() -> Mock:
    """Create mock pipeline config."""
    config = Mock()
    config.table.silver_write_mode = "merge"
    config.table.gold_write_mode = "merge"
    config.table.primary_keys = ["record_id"]
    config.table.partition_cols = []
    config.dq.key_nullability_rules = []
    return config


@pytest.fixture
def validator(mock_config: Mock, mock_logger: Mock) -> MedallionConfigValidator:
    """Create MedallionConfigValidator instance."""
    return MedallionConfigValidator(
        config=mock_config,
        logger=mock_logger,
        write_mode_policy=WriteModePolicy(),
    )


@pytest.fixture
def mock_runtime() -> Mock:
    """Create mock runtime config."""
    runtime = Mock()
    runtime.run_type = RunType.INCREMENTAL
    runtime.strict_validation = False
    return runtime


class TestMedallionConfigValidator:
    """Tests for MedallionConfigValidator."""

    def test_validate_layer_formats_valid_delta(
        self,
        validator: MedallionConfigValidator,
        mock_runtime: Mock,
    ) -> None:
        """Test validation passes for valid delta format."""
        errors = validator.validate_medallion_config(
            runtime=mock_runtime,
            bronze_path="/bronze",
            silver_path="/silver",
            gold_path="/gold",
            silver_format="delta",
            gold_format="delta",
        )
        assert len(errors) == 0

    def test_validate_layer_formats_rejects_parquet_gold(
        self,
        validator: MedallionConfigValidator,
        mock_runtime: Mock,
    ) -> None:
        """Test validation fails for parquet gold format (RULES §2.1)."""
        errors = validator.validate_medallion_config(
            runtime=mock_runtime,
            bronze_path="/bronze",
            silver_path="/silver",
            gold_path="/gold",
            silver_format="delta",
            gold_format="parquet",
        )
        assert len(errors) == 1
        assert errors[0].field == "sink.gold.format"
        assert errors[0].expected == "delta"
        assert errors[0].actual == "parquet"

    def test_validate_layer_formats_invalid_silver(
        self,
        validator: MedallionConfigValidator,
        mock_runtime: Mock,
    ) -> None:
        """Test validation fails for non-delta silver format."""
        errors = validator.validate_medallion_config(
            runtime=mock_runtime,
            bronze_path="/bronze",
            silver_path="/silver",
            gold_path="/gold",
            silver_format="parquet",
            gold_format="delta",
        )
        assert len(errors) == 1
        assert errors[0].field == "sink.silver.format"
        assert "delta" in errors[0].expected

    def test_validate_layer_formats_invalid_gold(
        self,
        validator: MedallionConfigValidator,
        mock_runtime: Mock,
    ) -> None:
        """Test validation fails for invalid gold format."""
        errors = validator.validate_medallion_config(
            runtime=mock_runtime,
            bronze_path="/bronze",
            silver_path="/silver",
            gold_path="/gold",
            silver_format="delta",
            gold_format="csv",  # Invalid
        )
        assert len(errors) == 1
        assert errors[0].field == "sink.gold.format"

    def test_validate_path_uniqueness_all_unique(
        self,
        validator: MedallionConfigValidator,
        mock_runtime: Mock,
    ) -> None:
        """Test validation passes when all paths are unique."""
        errors = validator.validate_medallion_config(
            runtime=mock_runtime,
            bronze_path="/bronze",
            silver_path="/silver",
            gold_path="/gold",
        )
        assert len(errors) == 0

    def test_validate_path_uniqueness_bronze_silver_same(
        self,
        validator: MedallionConfigValidator,
        mock_runtime: Mock,
    ) -> None:
        """Test validation fails when bronze and silver paths are same."""
        errors = validator.validate_medallion_config(
            runtime=mock_runtime,
            bronze_path="/data",
            silver_path="/data",  # Same as bronze
            gold_path="/gold",
        )
        assert len(errors) == 1
        assert "bronze_path == silver_path" in errors[0].actual

    def test_validate_path_uniqueness_silver_gold_same(
        self,
        validator: MedallionConfigValidator,
        mock_runtime: Mock,
    ) -> None:
        """Test validation fails when silver and gold paths are same."""
        errors = validator.validate_medallion_config(
            runtime=mock_runtime,
            bronze_path="/bronze",
            silver_path="/data",
            gold_path="/data",  # Same as silver
        )
        assert len(errors) == 1
        assert "silver_path == gold_path" in errors[0].actual

    def test_validate_medallion_policy_incremental(
        self,
        validator: MedallionConfigValidator,
    ) -> None:
        """Test validation passes for incremental run type."""
        runtime = Mock()
        runtime.run_type = RunType.INCREMENTAL
        runtime.strict_validation = False

        errors = validator.validate_medallion_config(
            runtime=runtime,
            bronze_path="/bronze",
            silver_path="/silver",
            gold_path="/gold",
        )
        assert len(errors) == 0

    def test_validate_medallion_policy_backfill(
        self,
        validator: MedallionConfigValidator,
    ) -> None:
        """Test validation passes for backfill run type."""
        runtime = Mock()
        runtime.run_type = RunType.BACKFILL
        runtime.strict_validation = False

        # MedallionPolicy.for_run_type(BACKFILL) returns policy with
        # should_clear_silver=True and should_clear_gold=True
        errors = validator.validate_medallion_config(
            runtime=runtime,
            bronze_path="/bronze",
            silver_path="/silver",
            gold_path="/gold",
        )
        assert len(errors) == 0

    def test_validate_medallion_policy_rebuild(
        self,
        validator: MedallionConfigValidator,
    ) -> None:
        """Test validation passes for rebuild run type."""
        runtime = Mock()
        runtime.run_type = RunType.REBUILD
        runtime.strict_validation = False

        errors = validator.validate_medallion_config(
            runtime=runtime,
            bronze_path="/bronze",
            silver_path="/silver",
            gold_path="/gold",
        )
        assert len(errors) == 0


class TestWriteModeValidation:
    """Tests for write mode validation."""

    def test_valid_silver_merge(self, mock_logger: Mock) -> None:
        """Test validation passes for merge mode in silver."""
        config = Mock()
        config.table.silver_write_mode = "merge"
        config.table.gold_write_mode = "merge"
        config.table.silver_idempotency_contract = "merge_upsert"
        config.table.gold_idempotency_contract = "merge_upsert"

        validator = MedallionConfigValidator(
            config=config, logger=mock_logger, write_mode_policy=WriteModePolicy()
        )
        errors = validator.validate_write_modes()
        assert len(errors) == 0

    def test_valid_silver_append(self, mock_logger: Mock) -> None:
        """Test validation passes for append mode in silver."""
        config = Mock()
        config.table.silver_write_mode = "append"
        config.table.gold_write_mode = "merge"
        config.table.silver_idempotency_contract = "append_log"
        config.table.gold_idempotency_contract = "merge_upsert"

        validator = MedallionConfigValidator(
            config=config, logger=mock_logger, write_mode_policy=WriteModePolicy()
        )
        errors = validator.validate_write_modes()
        assert len(errors) == 0

    def test_invalid_silver_overwrite(self, mock_logger: Mock) -> None:
        """Test validation fails for overwrite mode in silver."""
        config = Mock()
        config.table.silver_write_mode = "overwrite"  # Not allowed for silver
        config.table.gold_write_mode = "merge"

        validator = MedallionConfigValidator(
            config=config, logger=mock_logger, write_mode_policy=WriteModePolicy()
        )
        errors = validator.validate_write_modes()
        assert len(errors) == 1
        assert errors[0].field == "write_mode"

    def test_valid_gold_merge(self, mock_logger: Mock) -> None:
        """Test validation passes for merge mode in gold."""
        config = Mock()
        config.table.silver_write_mode = "merge"
        config.table.gold_write_mode = "merge"
        config.table.silver_idempotency_contract = "merge_upsert"
        config.table.gold_idempotency_contract = "merge_upsert"

        validator = MedallionConfigValidator(
            config=config, logger=mock_logger, write_mode_policy=WriteModePolicy()
        )
        errors = validator.validate_write_modes()
        assert len(errors) == 0

    def test_valid_gold_overwrite(self, mock_logger: Mock) -> None:
        """Test validation passes for overwrite mode in gold."""
        config = Mock()
        config.table.silver_write_mode = "merge"
        config.table.gold_write_mode = "overwrite"
        config.table.silver_idempotency_contract = "merge_upsert"
        config.table.gold_idempotency_contract = "overwrite_rebuild"

        validator = MedallionConfigValidator(
            config=config, logger=mock_logger, write_mode_policy=WriteModePolicy()
        )
        errors = validator.validate_write_modes()
        assert len(errors) == 0

    def test_valid_gold_scd2(self, mock_logger: Mock) -> None:
        """Test validation passes for scd2 mode in gold."""
        config = Mock()
        config.table.silver_write_mode = "merge"
        config.table.gold_write_mode = "scd2"
        config.table.silver_idempotency_contract = "merge_upsert"
        config.table.gold_idempotency_contract = "scd2"

        validator = MedallionConfigValidator(
            config=config, logger=mock_logger, write_mode_policy=WriteModePolicy()
        )
        errors = validator.validate_write_modes()
        assert len(errors) == 0

    def test_valid_gold_append(self, mock_logger: Mock) -> None:
        """Test validation passes for append mode in gold."""
        config = Mock()
        config.table.silver_write_mode = "merge"
        config.table.gold_write_mode = "append"  # Allowed for gold per ALLOWED_MODES
        config.table.silver_idempotency_contract = "merge_upsert"
        config.table.gold_idempotency_contract = "append_log"

        validator = MedallionConfigValidator(
            config=config, logger=mock_logger, write_mode_policy=WriteModePolicy()
        )
        errors = validator.validate_write_modes()
        assert len(errors) == 0

    def test_invalid_gold_mode(self, mock_logger: Mock) -> None:
        """Test validation fails for invalid gold mode."""
        config = Mock()
        config.table.silver_write_mode = "merge"
        config.table.gold_write_mode = "invalid_mode"
        config.table.silver_idempotency_contract = "merge_upsert"
        config.table.gold_idempotency_contract = None

        validator = MedallionConfigValidator(
            config=config, logger=mock_logger, write_mode_policy=WriteModePolicy()
        )
        errors = validator.validate_write_modes()
        assert len(errors) == 2
        assert errors[0].field == "gold_write_mode"
        assert errors[1].field == "sink.gold.idempotency_contract"

    def test_invalid_both_modes(self, mock_logger: Mock) -> None:
        """Test validation fails for both invalid modes."""
        config = Mock()
        config.table.silver_write_mode = "invalid_mode"
        config.table.gold_write_mode = "invalid_mode"
        config.table.silver_idempotency_contract = None
        config.table.gold_idempotency_contract = None

        validator = MedallionConfigValidator(
            config=config, logger=mock_logger, write_mode_policy=WriteModePolicy()
        )
        errors = validator.validate_write_modes()
        assert len(errors) == 4
