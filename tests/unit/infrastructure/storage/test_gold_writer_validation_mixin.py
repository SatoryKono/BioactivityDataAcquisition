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
"""Unit tests for GoldWriterValidationMixin."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.domain.medallion import GoldWriteMode
from bioetl.domain.types import GoldContractValidationError
from bioetl.infrastructure.storage.gold.validation_mixin import (
    GoldWriterValidationMixin,
)


class _Host(GoldWriterValidationMixin):
    """Minimal host that wires the mixin for isolated testing."""

    def __init__(self) -> None:
        self.logger = MagicMock()


@pytest.mark.unit
class TestGoldWriterValidationMixin:
    """Tests for Gold writer validation helpers."""

    def test_validate_write_mode_valid_append(self) -> None:
        """Should return GoldWriteMode.APPEND for 'append' string."""
        host = _Host()
        assert host._validate_write_mode("append") == GoldWriteMode.APPEND

    def test_validate_write_mode_valid_scd2(self) -> None:
        """Should return GoldWriteMode.SCD2 for 'scd2' string."""
        host = _Host()
        assert host._validate_write_mode("scd2") == GoldWriteMode.SCD2

    def test_validate_write_mode_invalid(self) -> None:
        """Should raise ValueError for unrecognized mode."""
        host = _Host()
        with pytest.raises(ValueError, match="Invalid Gold write mode"):
            host._validate_write_mode("invalid_mode")

    def test_validate_records_non_empty(self) -> None:
        """Non-empty records should pass validation."""
        host = _Host()
        host._validate_records([{"id": 1}])

    def test_validate_records_empty_raises(self) -> None:
        """Empty records list should raise ValueError."""
        host = _Host()
        with pytest.raises(ValueError, match="No records to write"):
            host._validate_records([])

    def test_validate_scd2_requirements_non_scd2_mode_skips(self) -> None:
        """Non-SCD2 mode should skip all SCD2 checks."""
        host = _Host()
        # Should not raise
        host._validate_scd2_requirements(GoldWriteMode.APPEND, None, None)

    def test_validate_scd2_requirements_missing_config_raises(self) -> None:
        """SCD2 mode without scd_config should raise."""
        host = _Host()
        with pytest.raises(ValueError, match="scd_config required"):
            host._validate_scd2_requirements(GoldWriteMode.SCD2, None, None)

    def test_validate_scd2_requirements_wrong_type_raises(self) -> None:
        """SCD2 mode with scd_type != 2 should raise."""
        host = _Host()
        scd_config = MagicMock()
        scd_config.scd_type = 1
        with pytest.raises(ValueError, match=r"scd_config.type must be 2"):
            host._validate_scd2_requirements(GoldWriteMode.SCD2, scd_config, None)

    def test_validate_scd2_requirements_missing_business_keys_raises(self) -> None:
        """SCD2 mode with empty business_keys should raise."""
        host = _Host()
        scd_config = MagicMock()
        scd_config.scd_type = 2
        scd_config.business_keys = []
        with pytest.raises(ValueError, match=r"scd_config.business_key required"):
            host._validate_scd2_requirements(GoldWriteMode.SCD2, scd_config, None)

    def test_validate_scd2_requirements_missing_ingestion_ts_raises(self) -> None:
        """SCD2 mode without ingestion_ts should raise."""
        host = _Host()
        scd_config = MagicMock()
        scd_config.scd_type = 2
        scd_config.business_keys = ["id"]
        with pytest.raises(ValueError, match="ingestion_ts required"):
            host._validate_scd2_requirements(GoldWriteMode.SCD2, scd_config, None)

    def test_validate_schema_strict_passes(self) -> None:
        """Schema with strict=True should pass."""
        host = _Host()
        schema = MagicMock()
        schema.strict = True
        host._validate_schema_strict(schema)

    def test_validate_schema_strict_fails(self) -> None:
        """Schema without strict=True should raise ValueError."""
        host = _Host()
        schema = MagicMock(spec=[])
        # No strict attr at all
        with pytest.raises(
            GoldContractValidationError, match="strict=True"
        ) as exc_info:
            host._validate_schema_strict(schema)
        assert (
            exc_info.value.reject_reason.reason_code == "gold_contract_schema_failure"
        )
        assert exc_info.value.reject_reason.rule_id == "gold.contract.strict_schema"
