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
"""Unit tests for _MedallionConfigValidator in preflight_medallion_validator.py.

Tests the dedicated module (distinct from the one embedded in preflight_service).
Covers: layer format validation, path uniqueness, medallion policy consistency,
key nullability policies, write mode validation, and logging.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.application.core.preflight.medallion_validator import (
    _MedallionConfigValidator,
)
from bioetl.domain.medallion import WriteModePolicy
from bioetl.domain.types import RunType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_logger() -> MagicMock:
    logger = MagicMock()
    logger.debug = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    return logger


@pytest.fixture
def mock_config() -> MagicMock:
    """Minimal pipeline config mock with valid defaults."""
    config = MagicMock()
    config.table.silver_write_mode = "merge"
    config.table.gold_write_mode = "overwrite"
    config.table.silver_idempotency_contract = "merge_upsert"
    config.table.gold_idempotency_contract = "overwrite_rebuild"
    config.table.primary_keys = ["record_id"]
    config.table.partition_cols = []
    config.dq.key_nullability_rules = []
    return config


@pytest.fixture
def mock_runtime() -> MagicMock:
    """Runtime config with INCREMENTAL run type, no strict validation."""
    runtime = MagicMock()
    runtime.run_type = RunType.INCREMENTAL
    runtime.strict_validation = False
    return runtime


@pytest.fixture
def validator(
    mock_config: MagicMock, mock_logger: MagicMock
) -> _MedallionConfigValidator:
    """Create _MedallionConfigValidator with default write mode policy."""
    return _build_validator(config=mock_config, logger=mock_logger)


def _build_validator(
    *,
    config: MagicMock,
    logger: MagicMock,
) -> _MedallionConfigValidator:
    """Create validator with explicit WriteModePolicy injection."""
    return _MedallionConfigValidator(
        config=config,
        logger=logger,
        write_mode_policy=WriteModePolicy(),
    )


# ---------------------------------------------------------------------------
# Tests: Layer Format Validation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLayerFormatValidation:
    """Tests for silver/gold layer format validation."""

    def test_valid_delta_formats_return_no_errors(
        self,
        validator: _MedallionConfigValidator,
        mock_runtime: MagicMock,
    ) -> None:
        """Test that delta/delta formats pass with no errors."""
        errors = validator.validate_medallion_config(
            runtime=mock_runtime,
            bronze_path="/bronze",
            silver_path="/silver",
            gold_path="/gold",
            silver_format="delta",
            gold_format="delta",
        )
        assert errors == []

    def test_none_formats_skip_format_validation(
        self,
        validator: _MedallionConfigValidator,
        mock_runtime: MagicMock,
    ) -> None:
        """Test that None silver/gold formats skip format check."""
        errors = validator.validate_medallion_config(
            runtime=mock_runtime,
            bronze_path="/bronze",
            silver_path="/silver",
            gold_path="/gold",
            silver_format=None,
            gold_format=None,
        )
        assert errors == []

    def test_parquet_silver_format_fails(
        self,
        validator: _MedallionConfigValidator,
        mock_runtime: MagicMock,
    ) -> None:
        """Test that parquet silver format produces a validation error."""
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
        assert errors[0].expected == "delta"
        assert errors[0].actual == "parquet"

    def test_parquet_gold_format_fails(
        self,
        validator: _MedallionConfigValidator,
        mock_runtime: MagicMock,
    ) -> None:
        """Test that parquet gold format produces a validation error."""
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

    def test_csv_silver_format_fails(
        self,
        validator: _MedallionConfigValidator,
        mock_runtime: MagicMock,
    ) -> None:
        """Test that CSV silver format produces a validation error."""
        errors = validator.validate_medallion_config(
            runtime=mock_runtime,
            bronze_path="/bronze",
            silver_path="/silver",
            gold_path="/gold",
            silver_format="csv",
            gold_format="delta",
        )
        assert any(e.field == "sink.silver.format" for e in errors)

    def test_both_formats_invalid_produces_two_errors(
        self,
        validator: _MedallionConfigValidator,
        mock_runtime: MagicMock,
    ) -> None:
        """Test that both invalid formats produce two separate errors."""
        errors = validator.validate_medallion_config(
            runtime=mock_runtime,
            bronze_path="/bronze",
            silver_path="/silver",
            gold_path="/gold",
            silver_format="parquet",
            gold_format="csv",
        )
        fields = [e.field for e in errors]
        assert "sink.silver.format" in fields
        assert "sink.gold.format" in fields


@pytest.mark.unit
class TestIdempotencyContractValidation:
    """Tests for explicit sink idempotency-contract validation."""

    def test_matching_contracts_pass(
        self,
        validator: _MedallionConfigValidator,
    ) -> None:
        assert validator.validate_write_modes() == []

    def test_append_mode_requires_append_safe_contract(
        self,
        mock_config: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        mock_config.table.silver_write_mode = "append"
        mock_config.table.silver_idempotency_contract = "merge_upsert"
        validator = _build_validator(config=mock_config, logger=mock_logger)

        errors = validator.validate_write_modes()

        assert any(
            error.field == "sink.silver.idempotency_contract"
            and error.actual == "merge_upsert"
            for error in errors
        )

    def test_missing_contract_fails(
        self,
        mock_config: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        mock_config.table.silver_idempotency_contract = None
        validator = _build_validator(config=mock_config, logger=mock_logger)

        errors = validator.validate_write_modes()

        assert any(
            error.field == "sink.silver.idempotency_contract"
            and error.actual == "missing"
            for error in errors
        )

    def test_overwrite_requires_overwrite_rebuild_contract(
        self,
        mock_config: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        mock_config.table.gold_write_mode = "overwrite"
        mock_config.table.gold_idempotency_contract = "append_log"
        validator = _build_validator(config=mock_config, logger=mock_logger)

        errors = validator.validate_write_modes()

        assert any(
            error.field == "sink.gold.idempotency_contract"
            and error.expected == "overwrite_rebuild"
            for error in errors
        )


# ---------------------------------------------------------------------------
# Tests: Path Uniqueness Validation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPathUniquenessValidation:
    """Tests for path uniqueness across medallion layers."""

    def test_all_unique_paths_pass(
        self,
        validator: _MedallionConfigValidator,
        mock_runtime: MagicMock,
    ) -> None:
        """Test that three unique paths produce no errors."""
        errors = validator.validate_medallion_config(
            runtime=mock_runtime,
            bronze_path="/bronze",
            silver_path="/silver",
            gold_path="/gold",
        )
        assert errors == []

    def test_bronze_silver_same_path_fails(
        self,
        validator: _MedallionConfigValidator,
        mock_runtime: MagicMock,
    ) -> None:
        """Test that bronze == silver path produces a validation error."""
        errors = validator.validate_medallion_config(
            runtime=mock_runtime,
            bronze_path="/data",
            silver_path="/data",
            gold_path="/gold",
        )
        assert len(errors) == 1
        assert "bronze_path == silver_path" in errors[0].actual

    def test_silver_gold_same_path_fails(
        self,
        validator: _MedallionConfigValidator,
        mock_runtime: MagicMock,
    ) -> None:
        """Test that silver == gold path produces a validation error."""
        errors = validator.validate_medallion_config(
            runtime=mock_runtime,
            bronze_path="/bronze",
            silver_path="/data",
            gold_path="/data",
        )
        assert len(errors) == 1
        assert "silver_path == gold_path" in errors[0].actual

    def test_bronze_gold_same_path_fails(
        self,
        validator: _MedallionConfigValidator,
        mock_runtime: MagicMock,
    ) -> None:
        """Test that bronze == gold path produces a validation error."""
        errors = validator.validate_medallion_config(
            runtime=mock_runtime,
            bronze_path="/data",
            silver_path="/silver",
            gold_path="/data",
        )
        assert any("bronze_path == gold_path" in e.actual for e in errors)

    def test_path_uniqueness_error_uses_correct_rule(
        self,
        validator: _MedallionConfigValidator,
        mock_runtime: MagicMock,
    ) -> None:
        """Test that path uniqueness error references the Medallion Architecture rule."""
        errors = validator.validate_medallion_config(
            runtime=mock_runtime,
            bronze_path="/data",
            silver_path="/data",
            gold_path="/gold",
        )
        assert "Medallion Architecture" in errors[0].rule


# ---------------------------------------------------------------------------
# Tests: Medallion Policy Consistency
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMedallionPolicyConsistency:
    """Tests for MedallionPolicy consistency per run type."""

    def test_incremental_passes_with_no_clear(
        self,
        validator: _MedallionConfigValidator,
    ) -> None:
        """Test that INCREMENTAL run type passes medallion policy check."""
        runtime = MagicMock()
        runtime.run_type = RunType.INCREMENTAL
        runtime.strict_validation = False

        errors = validator.validate_medallion_config(
            runtime=runtime,
            bronze_path="/bronze",
            silver_path="/silver",
            gold_path="/gold",
        )
        assert errors == []

    def test_rebuild_passes_with_clear_both(
        self,
        validator: _MedallionConfigValidator,
    ) -> None:
        """Test that REBUILD run type passes medallion policy check."""
        runtime = MagicMock()
        runtime.run_type = RunType.REBUILD
        runtime.strict_validation = False

        errors = validator.validate_medallion_config(
            runtime=runtime,
            bronze_path="/bronze",
            silver_path="/silver",
            gold_path="/gold",
        )
        assert errors == []

    def test_backfill_passes_with_clear_both(
        self,
        validator: _MedallionConfigValidator,
    ) -> None:
        """Test that BACKFILL run type passes medallion policy check."""
        runtime = MagicMock()
        runtime.run_type = RunType.BACKFILL
        runtime.strict_validation = False

        errors = validator.validate_medallion_config(
            runtime=runtime,
            bronze_path="/bronze",
            silver_path="/silver",
            gold_path="/gold",
        )
        assert errors == []


# ---------------------------------------------------------------------------
# Tests: Key Nullability Policy
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestKeyNullabilityPolicyValidation:
    """Tests for DQ key_nullability policy validation."""

    def test_empty_rules_pass(
        self,
        validator: _MedallionConfigValidator,
        mock_runtime: MagicMock,
    ) -> None:
        """Test that empty key_nullability_rules produce no errors."""
        errors = validator.validate_medallion_config(
            runtime=mock_runtime,
            bronze_path="/bronze",
            silver_path="/silver",
            gold_path="/gold",
        )
        assert errors == []

    def test_rule_referencing_primary_key_passes(
        self,
        mock_logger: MagicMock,
        mock_runtime: MagicMock,
    ) -> None:
        """Test that a key_nullability_rule on a valid primary key passes."""
        config = MagicMock()
        config.table.silver_write_mode = "merge"
        config.table.gold_write_mode = "merge"
        config.table.primary_keys = ["record_id"]
        config.table.partition_cols = []

        rule = MagicMock()
        rule.field = "record_id"  # in primary_keys
        config.dq.key_nullability_rules = [rule]

        validator = _build_validator(config=config, logger=mock_logger)
        errors = validator.validate_medallion_config(
            runtime=mock_runtime,
            bronze_path="/bronze",
            silver_path="/silver",
            gold_path="/gold",
        )
        assert errors == []

    def test_rule_referencing_unknown_field_fails(
        self,
        mock_logger: MagicMock,
        mock_runtime: MagicMock,
    ) -> None:
        """Test that a key_nullability_rule on an unknown field fails."""
        config = MagicMock()
        config.table.silver_write_mode = "merge"
        config.table.gold_write_mode = "merge"
        config.table.primary_keys = ["record_id"]
        config.table.partition_cols = []

        rule = MagicMock()
        rule.field = "nonexistent_field"  # not in primary_keys or partition_cols
        config.dq.key_nullability_rules = [rule]

        validator = _build_validator(config=config, logger=mock_logger)
        errors = validator.validate_medallion_config(
            runtime=mock_runtime,
            bronze_path="/bronze",
            silver_path="/silver",
            gold_path="/gold",
        )
        assert any(e.field == "dq.key_nullability" for e in errors)

    def test_rule_referencing_partition_col_passes(
        self,
        mock_logger: MagicMock,
        mock_runtime: MagicMock,
    ) -> None:
        """Test that key_nullability_rule on a partition_col passes."""
        config = MagicMock()
        config.table.silver_write_mode = "merge"
        config.table.gold_write_mode = "merge"
        config.table.primary_keys = ["record_id"]
        config.table.partition_cols = ["partition_date"]

        rule = MagicMock()
        rule.field = "partition_date"  # in partition_cols
        config.dq.key_nullability_rules = [rule]

        validator = _build_validator(config=config, logger=mock_logger)
        errors = validator.validate_medallion_config(
            runtime=mock_runtime,
            bronze_path="/bronze",
            silver_path="/silver",
            gold_path="/gold",
        )
        assert errors == []


# ---------------------------------------------------------------------------
# Tests: Write Mode Validation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestWriteModeValidation:
    """Tests for validate_write_modes method."""

    def test_valid_silver_merge_passes(self, mock_logger: MagicMock) -> None:
        """Test that merge is valid for silver."""
        config = MagicMock()
        config.table.silver_write_mode = "merge"
        config.table.gold_write_mode = "scd2"
        config.table.silver_idempotency_contract = "merge_upsert"
        config.table.gold_idempotency_contract = "scd2"
        validator = _build_validator(config=config, logger=mock_logger)
        assert validator.validate_write_modes() == []

    def test_valid_silver_append_passes(self, mock_logger: MagicMock) -> None:
        """Test that append is valid for silver."""
        config = MagicMock()
        config.table.silver_write_mode = "append"
        config.table.gold_write_mode = "append"
        config.table.silver_idempotency_contract = "append_log"
        config.table.gold_idempotency_contract = "append_log"
        validator = _build_validator(config=config, logger=mock_logger)
        assert validator.validate_write_modes() == []

    def test_invalid_silver_overwrite_fails(self, mock_logger: MagicMock) -> None:
        """Test that overwrite is invalid for silver layer."""
        config = MagicMock()
        config.table.silver_write_mode = "overwrite"
        config.table.gold_write_mode = "scd2"
        config.table.silver_idempotency_contract = "merge_upsert"
        config.table.gold_idempotency_contract = "scd2"
        validator = _build_validator(config=config, logger=mock_logger)
        errors = validator.validate_write_modes()
        assert len(errors) == 1
        assert errors[0].field == "write_mode"

    def test_invalid_gold_merge_fails(self, mock_logger: MagicMock) -> None:
        """Test that merge is invalid for gold."""
        config = MagicMock()
        config.table.silver_write_mode = "merge"
        config.table.gold_write_mode = "merge"
        config.table.silver_idempotency_contract = "merge_upsert"
        config.table.gold_idempotency_contract = "merge_upsert"
        validator = _build_validator(config=config, logger=mock_logger)
        errors = validator.validate_write_modes()
        assert len(errors) == 1
        assert errors[0].field == "gold_write_mode"

    def test_valid_gold_scd2_passes(self, mock_logger: MagicMock) -> None:
        """Test that scd2 is valid for gold."""
        config = MagicMock()
        config.table.silver_write_mode = "merge"
        config.table.gold_write_mode = "scd2"
        config.table.silver_idempotency_contract = "merge_upsert"
        config.table.gold_idempotency_contract = "scd2"
        validator = _build_validator(config=config, logger=mock_logger)
        assert validator.validate_write_modes() == []

    def test_valid_gold_overwrite_passes(self, mock_logger: MagicMock) -> None:
        """Test that overwrite is valid for gold."""
        config = MagicMock()
        config.table.silver_write_mode = "merge"
        config.table.gold_write_mode = "overwrite"
        config.table.silver_idempotency_contract = "merge_upsert"
        config.table.gold_idempotency_contract = "overwrite_rebuild"
        validator = _build_validator(config=config, logger=mock_logger)
        assert validator.validate_write_modes() == []

    def test_invalid_gold_mode_fails(self, mock_logger: MagicMock) -> None:
        """Test that an unknown gold write mode produces a validation error."""
        config = MagicMock()
        config.table.silver_write_mode = "merge"
        config.table.gold_write_mode = "invalid_mode"
        config.table.silver_idempotency_contract = "merge_upsert"
        config.table.gold_idempotency_contract = "merge_upsert"
        validator = _build_validator(config=config, logger=mock_logger)
        errors = validator.validate_write_modes()
        assert len(errors) == 1
        assert errors[0].field == "gold_write_mode"

    def test_both_invalid_modes_produce_two_errors(
        self, mock_logger: MagicMock
    ) -> None:
        """Test that two invalid modes produce two errors."""
        config = MagicMock()
        config.table.silver_write_mode = "invalid_silver"
        config.table.gold_write_mode = "invalid_gold"
        config.table.silver_idempotency_contract = "merge_upsert"
        config.table.gold_idempotency_contract = "merge_upsert"
        validator = _build_validator(config=config, logger=mock_logger)
        errors = validator.validate_write_modes()
        assert len(errors) == 2


# ---------------------------------------------------------------------------
# Tests: Logging behavior
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMedallionValidatorLogging:
    """Tests for _MedallionConfigValidator logging behavior."""

    def test_warning_logged_when_errors_found(
        self,
        validator: _MedallionConfigValidator,
        mock_logger: MagicMock,
    ) -> None:
        """Test that warning is logged when validation finds errors."""
        runtime = MagicMock()
        runtime.run_type = RunType.INCREMENTAL
        runtime.strict_validation = False

        validator.validate_medallion_config(
            runtime=runtime,
            bronze_path="/bronze",
            silver_path="/silver",
            gold_path="/gold",
            silver_format="parquet",  # will fail
            gold_format="delta",
        )

        mock_logger.warning.assert_called_once()

    def test_debug_logged_when_no_errors(
        self,
        validator: _MedallionConfigValidator,
        mock_logger: MagicMock,
        mock_runtime: MagicMock,
    ) -> None:
        """Test that debug is logged when validation passes."""
        validator.validate_medallion_config(
            runtime=mock_runtime,
            bronze_path="/bronze",
            silver_path="/silver",
            gold_path="/gold",
            silver_format="delta",
            gold_format="delta",
        )

        mock_logger.debug.assert_called_once()

    def test_write_mode_warning_logged_when_errors(
        self, mock_logger: MagicMock
    ) -> None:
        """Test that warning is logged when write mode validation fails."""
        config = MagicMock()
        config.table.silver_write_mode = "overwrite"
        config.table.gold_write_mode = "scd2"
        config.table.silver_idempotency_contract = "merge_upsert"
        config.table.gold_idempotency_contract = "scd2"
        validator = _build_validator(config=config, logger=mock_logger)

        validator.validate_write_modes()

        mock_logger.warning.assert_called_once()

    def test_write_mode_debug_logged_when_valid(self, mock_logger: MagicMock) -> None:
        """Test that debug is logged when write mode validation passes."""
        config = MagicMock()
        config.table.silver_write_mode = "merge"
        config.table.gold_write_mode = "scd2"
        config.table.silver_idempotency_contract = "merge_upsert"
        config.table.gold_idempotency_contract = "scd2"
        validator = _build_validator(config=config, logger=mock_logger)

        validator.validate_write_modes()

        mock_logger.debug.assert_called_once()
