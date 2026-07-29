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
"""Unit tests for metadata writer operations."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bioetl.infrastructure.storage.metadata.writer_operations import (
    METADATA_FILENAME,
    _MetadataWriteRequest,
    _MetadataWriteRetryState,
    _MetadataWriteTelemetryContext,
    _build_metadata_write_final_telemetry,
    _build_retry_callback,
    _emit_final_telemetry,
    _emit_retry_telemetry,
    _get_metadata_filename,
    _resolve_metadata_target,
)


@pytest.mark.unit
class TestGetMetadataFilename:
    """Tests for metadata filename resolution."""

    def test_provider_and_entity_filename(self) -> None:
        """Should produce {provider}_{entity}_metadata.yaml."""
        assert (
            _get_metadata_filename("chembl", "compound")
            == "chembl_compound_metadata.yaml"
        )

    def test_default_filename_when_provider_none(self) -> None:
        """Should return default _metadata.yaml when provider is None."""
        assert _get_metadata_filename(None, None) == METADATA_FILENAME

    def test_default_filename_when_entity_none(self) -> None:
        """Should return default when entity is None."""
        assert _get_metadata_filename("chembl", None) == METADATA_FILENAME


@pytest.mark.unit
class TestResolveMetadataTarget:
    """Tests for metadata target path resolution."""

    def test_provider_entity_path(self) -> None:
        """Should resolve to base_path / filename with provider_entity."""
        request = _MetadataWriteRequest(
            base_path="/data/bronze",
            metadata=MagicMock(),
            layer="bronze",
            provider="chembl",
            entity="compound",
        )
        target = _resolve_metadata_target(request)
        assert target.metadata_path == Path(
            "/data/bronze/chembl_compound_metadata.yaml"
        )
        assert target.pipeline_label == "chembl.compound"

    def test_flat_structure_with_table_name(self) -> None:
        """Should use table_name in filename for flat structure."""
        request = _MetadataWriteRequest(
            base_path="/data/silver",
            metadata=MagicMock(),
            layer="silver",
            table_name="my_table",
            flat_structure=True,
        )
        target = _resolve_metadata_target(request)
        assert target.metadata_path == Path("/data/silver/my_table_metadata.yaml")
        assert target.pipeline_label == "my_table"

    def test_default_path_fallback(self) -> None:
        """Should fall back to _metadata.yaml when no provider/entity/table."""
        request = _MetadataWriteRequest(
            base_path="/data/gold",
            metadata=MagicMock(),
            layer="gold",
        )
        target = _resolve_metadata_target(request)
        assert target.metadata_path == Path("/data/gold/_metadata.yaml")
        assert target.pipeline_label == "gold_metadata"


@pytest.mark.unit
class TestBuildMetadataWriteFinalTelemetry:
    """Tests for final telemetry outcome resolution."""

    def test_failed_status_produces_error_severity(self) -> None:
        """Failed status should produce error severity and failed event name."""
        outcome = _build_metadata_write_final_telemetry(
            status="failed", retry_count=2, final_reason="os_error"
        )
        assert outcome.event_name == "metadata_write_failed"
        assert outcome.severity == "error"
        assert outcome.retry_count == 2

    def test_success_status_produces_info_severity(self) -> None:
        """Success status should produce info severity and completed event name."""
        outcome = _build_metadata_write_final_telemetry(
            status="success", retry_count=0, final_reason="ok"
        )
        assert outcome.event_name == "metadata_write_completed"
        assert outcome.severity == "info"


@pytest.mark.unit
class TestEmitRetryTelemetry:
    """Tests for retry telemetry emission."""

    def test_logs_warning_and_increments_counter(self) -> None:
        """Should log warning and increment metrics counter."""
        logger = MagicMock()
        metrics = MagicMock()
        context = _MetadataWriteTelemetryContext(
            layer="bronze", provider="chembl", pipeline="chembl.compound"
        )
        _emit_retry_telemetry(
            logger=logger,
            metrics=metrics,
            context=context,
            attempt=1,
            delay_seconds=0.5,
            reason="EACCES",
        )
        logger.warning.assert_called_once()
        metrics.increment_counter.assert_called_once()
        assert (
            metrics.increment_counter.call_args[0][0]
            == "bioetl_metadata_write_retries_total"
        )
        assert metrics.increment_counter.call_args[0][2] == {
            "layer": "bronze",
            "provider": "chembl",
            "pipeline": "chembl.compound",
            "reason": "EACCES",
        }

    def test_skips_metrics_when_none(self) -> None:
        """Should still log warning but skip metrics when metrics is None."""
        logger = MagicMock()
        context = _MetadataWriteTelemetryContext(
            layer="silver", provider=None, pipeline="silver_metadata"
        )
        _emit_retry_telemetry(
            logger=logger,
            metrics=None,
            context=context,
            attempt=2,
            delay_seconds=1.0,
            reason="ENOENT",
        )
        logger.warning.assert_called_once()


@pytest.mark.unit
class TestEmitFinalTelemetry:
    """Tests for final metadata telemetry emission."""

    def test_emits_metadata_write_outcome_counter(self) -> None:
        """Final metadata outcomes must use the dedicated storage counter."""
        logger = MagicMock()
        metrics = MagicMock()
        context = _MetadataWriteTelemetryContext(
            layer="silver", provider=None, pipeline="silver_metadata"
        )
        outcome = _build_metadata_write_final_telemetry(
            status="failed",
            retry_count=2,
            final_reason="atomic_write_error",
        )

        _emit_final_telemetry(
            logger=logger,
            metrics=metrics,
            context=context,
            outcome=outcome,
        )

        logger.error.assert_called_once()
        metrics.increment_counter.assert_called_once_with(
            "bioetl_metadata_write_outcomes_total",
            1,
            {
                "layer": "silver",
                "provider": "storage",
                "pipeline": "silver_metadata",
                "status": "failed",
                "final_reason": "atomic_write_error",
            },
        )


@pytest.mark.unit
class TestBuildRetryCallback:
    """Tests for retry callback construction."""

    def test_callback_updates_retry_state(self) -> None:
        """Built callback should update retry_state.count on invocation."""
        logger = MagicMock()
        metrics = MagicMock()
        context = _MetadataWriteTelemetryContext(
            layer="bronze", provider="chembl", pipeline="chembl.compound"
        )
        retry_state = _MetadataWriteRetryState()
        callback = _build_retry_callback(
            logger=logger,
            metrics=metrics,
            context=context,
            retry_state=retry_state,
        )
        callback(3, 1.5, OSError("test"))
        assert retry_state.count == 3
        logger.warning.assert_called_once()
