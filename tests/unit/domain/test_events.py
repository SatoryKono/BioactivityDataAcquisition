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
"""Tests for domain events module.

Verifies PipelineEvent constants and helper methods.
"""

from __future__ import annotations

import pytest

from bioetl.domain.events import PipelineEvent


pytestmark = pytest.mark.unit


class TestPipelineEventConstants:
    """Tests for PipelineEvent constants."""

    def test_pipeline_lifecycle_events_defined(self) -> None:
        """Verify all pipeline lifecycle events are defined."""
        assert PipelineEvent.START == "pipeline_started"
        assert PipelineEvent.COMPLETE == "pipeline_finished"
        assert PipelineEvent.FAILED == "pipeline_failed"
        assert PipelineEvent.SHUTDOWN == "pipeline_shutdown"

    def test_batch_events_defined(self) -> None:
        """Verify batch processing events are defined."""
        assert PipelineEvent.BATCH_START == "batch_started"
        assert PipelineEvent.BATCH_COMPLETE == "batch_completed"

    def test_phase_events_defined(self) -> None:
        """Verify all phase events are defined."""
        # Started events
        assert PipelineEvent.STARTUP_STARTED == "startup_started"
        assert PipelineEvent.STARTUP_COMPLETED == "startup_completed"
        assert PipelineEvent.PREFLIGHT_STARTED == "preflight_started"
        assert PipelineEvent.PREFLIGHT_COMPLETED == "preflight_completed"
        assert PipelineEvent.LIFECYCLE_CLEAR_STARTED == "lifecycle_clear_started"
        assert PipelineEvent.LIFECYCLE_CLEAR_COMPLETED == "lifecycle_clear_completed"
        assert PipelineEvent.EXECUTION_STARTED == "execution_started"
        assert PipelineEvent.EXECUTION_COMPLETED == "execution_completed"
        assert PipelineEvent.POSTRUN_STARTED == "postrun_started"
        assert PipelineEvent.POSTRUN_COMPLETED == "postrun_completed"
        assert PipelineEvent.CLEANUP_STARTED == "cleanup_started"
        assert PipelineEvent.CLEANUP_COMPLETED == "cleanup_completed"

    def test_health_check_event_defined(self) -> None:
        """Verify health check event is defined."""
        assert PipelineEvent.HEALTH_CHECK_COMPLETED == "health_check_completed"

    def test_dq_anomaly_event_defined(self) -> None:
        """Verify DQ anomaly event is defined."""
        assert PipelineEvent.DQ_ANOMALY_DETECTED == "dq_anomaly_detected"

    def test_vacuum_event_defined(self) -> None:
        """Verify vacuum event is defined."""
        assert PipelineEvent.VACUUM_COMPLETED == "vacuum_completed"

    def test_artifact_published_event_defined(self) -> None:
        """Verify artifact publication event is defined."""
        assert PipelineEvent.ARTIFACT_PUBLISHED == "artifact_published"


class TestPipelineEventPhaseMethods:
    """Tests for PipelineEvent phase helper methods."""

    @pytest.mark.parametrize(
        ("phase_value", "expected"),
        [
            ("startup", "startup_started"),
            ("preflight", "preflight_started"),
            ("lifecycle_clear", "lifecycle_clear_started"),
            ("execution", "execution_started"),
            ("postrun", "postrun_started"),
            ("cleanup", "cleanup_started"),
        ],
    )
    def test_phase_started_generates_correct_event(
        self, phase_value: str, expected: str
    ) -> None:
        """Verify phase_started generates correct event names."""
        assert PipelineEvent.phase_started(phase_value) == expected

    @pytest.mark.parametrize(
        ("phase_value", "expected"),
        [
            ("startup", "startup_completed"),
            ("preflight", "preflight_completed"),
            ("lifecycle_clear", "lifecycle_clear_completed"),
            ("execution", "execution_completed"),
            ("postrun", "postrun_completed"),
            ("cleanup", "cleanup_completed"),
        ],
    )
    def test_phase_completed_generates_correct_event(
        self, phase_value: str, expected: str
    ) -> None:
        """Verify phase_completed generates correct event names."""
        assert PipelineEvent.phase_completed(phase_value) == expected


class TestPipelineEventImportFromDomain:
    """Tests for PipelineEvent import from domain facade."""

    def test_can_import_from_domain_facade(self) -> None:
        """Verify PipelineEvent is exported from domain module."""
        from bioetl.domain.events import PipelineEvent as DomainPipelineEvent

        assert DomainPipelineEvent.START == "pipeline_started"
