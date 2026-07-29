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
"""SilverWriter write-policy (DQ-governance) unit tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.infrastructure.storage.silver.runtime_helpers import (
    SilverWriterRuntimeServicesRequest,
)
from tests.unit.infrastructure.storage.silver_writer._test_support import (
    assert_standard_silver_write_succeeds,
    make_silver_writer,
    write_standard_silver,
)
from tests.unit.infrastructure.storage.test_silver_writer import (
    noop_logger,
    valid_records,
)

# Re-export shared fixtures for pytest discovery in this module.
_FIXTURE_IMPORTS = (noop_logger, valid_records)

pytestmark = pytest.mark.unit


class TestSilverWriterWriteModePolicy:
    """Tests for WriteModePolicy integration in SilverWriter."""

    def test_init_with_default_policy(self, noop_logger):
        """Test SilverWriter creates default WriteModePolicy when not provided."""
        from bioetl.domain.medallion import WriteModePolicy

        writer = make_silver_writer(logger=noop_logger)
        assert isinstance(writer._write_policy, WriteModePolicy)

    def test_init_with_custom_policy(self, noop_logger):
        """Test SilverWriter accepts custom WriteModePolicy."""
        from bioetl.domain.medallion import WriteModePolicy

        custom_policy = WriteModePolicy()
        writer = make_silver_writer(
            logger=noop_logger,
            runtime_request=SilverWriterRuntimeServicesRequest(
                write_policy=custom_policy,
            ),
        )
        assert writer._write_policy is custom_policy

    def test_init_with_metrics_port(self, noop_logger):
        """Test SilverWriter accepts optional MetricsPort."""
        mock_metrics = MagicMock()
        writer = make_silver_writer(
            logger=noop_logger,
            runtime_request=SilverWriterRuntimeServicesRequest(metrics=mock_metrics),
        )
        assert writer._metrics is mock_metrics

    @pytest.mark.parametrize(
        ("mode", "expected_mode"),
        [
            pytest.param("MERGE", "MERGE", id="merge"),
            pytest.param("APPEND", "APPEND", id="append"),
            pytest.param("DELETE", "OVERWRITE", id="delete-to-overwrite"),
        ],
    )
    def test_to_policy_write_mode(self, noop_logger, mode: str, expected_mode: str):
        """Public Silver modes should map to the expected policy modes."""
        from bioetl.domain.medallion import WriteMode
        from bioetl.infrastructure.storage.silver_writer import SilverWriteMode

        writer = make_silver_writer(logger=noop_logger)
        result = writer._to_policy_write_mode(getattr(SilverWriteMode, mode))
        assert result == getattr(WriteMode, expected_mode)

    @pytest.mark.parametrize(
        "mode",
        [
            pytest.param("MERGE", id="merge"),
            pytest.param("APPEND", id="append"),
        ],
    )
    def test_enforce_write_policy_allows_mode(self, noop_logger, mode: str):
        """Allowed Silver modes should pass policy enforcement."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriteMode

        writer = make_silver_writer(logger=noop_logger)
        writer._enforce_write_policy(getattr(SilverWriteMode, mode), "test.table")

    def test_enforce_write_policy_rejects_delete(self, noop_logger):
        """Test policy enforcement rejects DELETE mode for Silver (maps to OVERWRITE)."""
        from bioetl.domain.exceptions import PolicyViolationError
        from bioetl.infrastructure.storage.silver_writer import SilverWriteMode

        writer = make_silver_writer(logger=noop_logger)
        with pytest.raises(PolicyViolationError) as exc_info:
            writer._enforce_write_policy(SilverWriteMode.DELETE, "test.table")
        assert "silver does not allow overwrite" in str(exc_info.value)

    def test_enforce_write_policy_increments_metric_on_violation(self, noop_logger):
        """Test policy violation increments policy_violations_total metric."""
        from bioetl.domain.exceptions import PolicyViolationError
        from bioetl.infrastructure.storage.silver_writer import SilverWriteMode

        mock_metrics = MagicMock()
        writer = make_silver_writer(
            logger=noop_logger,
            runtime_request=SilverWriterRuntimeServicesRequest(metrics=mock_metrics),
        )

        with pytest.raises(PolicyViolationError):
            writer._enforce_write_policy(SilverWriteMode.DELETE, "test.table")

        mock_metrics.increment_counter.assert_called_once_with(
            "bioetl_policy_violations_total",
            1,
            {"layer": "silver", "mode": "overwrite"},
        )

    def test_enforce_write_policy_logs_error_on_violation(self, noop_logger):
        """Test policy violation logs error with context."""
        from bioetl.domain.exceptions import PolicyViolationError
        from bioetl.infrastructure.storage.silver_writer import SilverWriteMode

        mock_logger = MagicMock()
        writer = make_silver_writer(logger=mock_logger)

        with pytest.raises(PolicyViolationError):
            writer._enforce_write_policy(SilverWriteMode.DELETE, "test.table")

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert call_args[0][0] == "Write mode policy violation"
        assert call_args[1]["layer"] == "silver"
        assert call_args[1]["mode"] == "delete"
        assert call_args[1]["policy_mode"] == "overwrite"
        assert call_args[1]["table"] == "test.table"

    @pytest.mark.asyncio
    async def test_write_silver_delete_mode_raises_policy_violation(
        self, valid_records, noop_logger
    ):
        """Test write_silver with delete mode raises PolicyViolationError.

        This is the critical acceptance criterion: write_silver(mode="delete")
        must raise PolicyViolationError because DELETE maps to OVERWRITE
        which is not allowed for Silver layer.
        """
        from bioetl.domain.exceptions import PolicyViolationError

        writer = make_silver_writer(logger=noop_logger)

        with pytest.raises(PolicyViolationError) as exc_info:
            await write_standard_silver(
                writer,
                records=valid_records,
                mode="delete",
            )
        assert "silver does not allow overwrite" in str(exc_info.value)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "mode",
        [
            pytest.param("merge", id="merge"),
            pytest.param("append", id="append"),
        ],
    )
    async def test_write_silver_allowed_mode_passes_policy(
        self,
        valid_records,
        noop_logger,
        mode: str,
    ):
        """Allowed public write modes should proceed to Delta write."""
        writer = make_silver_writer(logger=noop_logger)
        await assert_standard_silver_write_succeeds(
            writer,
            records=valid_records,
            mode=mode,
        )

    @pytest.mark.asyncio
    async def test_write_silver_delete_mode_increments_metric(
        self, valid_records, noop_logger
    ):
        """Test write_silver with delete mode increments policy_violations_total."""
        from bioetl.domain.exceptions import PolicyViolationError

        mock_metrics = MagicMock()
        writer = make_silver_writer(
            logger=noop_logger,
            runtime_request=SilverWriterRuntimeServicesRequest(metrics=mock_metrics),
        )

        with pytest.raises(PolicyViolationError):
            await write_standard_silver(
                writer,
                records=valid_records,
                mode="delete",
            )

        mock_metrics.increment_counter.assert_called_once_with(
            "bioetl_policy_violations_total",
            1,
            {"layer": "silver", "mode": "overwrite"},
        )
