"""Stream B APP: leftover metrics, evidence, batch FSM, preflight, and report branches."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.composite.helpers import (
    preflight_schema_field_extraction as preflight,
)
from bioetl.application.core.batch_executor_state_flow import process_stateful_batch
from bioetl.application.core.lifecycle.batch_fsm import (
    BatchExecutionFSM,
    BatchExecutionState,
)
from bioetl.application.observability.control_plane_evidence import models as evidence
from bioetl.application.observability.control_plane_evidence.checks import (
    EvidenceCheckResult,
)
from bioetl.application.observability import (
    control_plane_integrity_metrics as integrity,
)
from bioetl.application.services.execution import (
    _pipeline_runner_support as runner_support,
)
from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineRunResult,
    RunResult,
)
from bioetl.application.services.ops import (
    _metrics_service_gateway_support as metrics_gw,
)
from bioetl.domain.control_plane.run_ledger import (
    RUN_FAILED_EVENT,
    RUN_FINISHED_EVENT,
    RUN_SHUTDOWN_EVENT,
)
from bioetl.domain.exceptions.base import BioETLError, DataQualityError

pytestmark = pytest.mark.unit


class _MetricsHost(metrics_gw._MetricsGatewayMixin):
    TRACER_NAME = "metrics"
    logger = MagicMock()


def test_metrics_gateway_delete_exception_success_and_failure() -> None:
    host = _MetricsHost()
    host._publisher = MagicMock()
    host._publisher.delete_from_gateway.side_effect = RuntimeError("down")
    failed = host._delete_from_gateway_impl(
        gateway="https://gw", run_label="bioetl", labels={"k": "v"}
    )
    assert failed.success is False
    assert failed.error == "down"

    host._publisher.delete_from_gateway.side_effect = None
    host._publisher.delete_from_gateway.return_value = True
    ok = host._delete_from_gateway_impl(
        gateway="https://gw", run_label="bioetl", labels={}
    )
    assert ok.success is True

    host._publisher.delete_from_gateway.return_value = False
    denied = host._delete_from_gateway_impl(
        gateway="http://gw", run_label="bioetl", labels={}
    )
    assert denied.success is False
    assert denied.error == "Publisher returned unsuccessful result"


def test_evidence_models_status_scope_and_trust() -> None:
    finished = evidence._processing_status(
        SimpleNamespace(launch_context={}),
        (SimpleNamespace(event_type=RUN_FINISHED_EVENT),),
    )
    assert finished == "success"
    failed = evidence._processing_status(
        SimpleNamespace(launch_context={}),
        (SimpleNamespace(event_type=RUN_FAILED_EVENT),),
    )
    assert failed == "failed"
    shutdown = evidence._processing_status(
        SimpleNamespace(launch_context={}),
        (SimpleNamespace(event_type=RUN_SHUTDOWN_EVENT),),
    )
    assert shutdown == "shutdown"
    launched = evidence._processing_status(
        SimpleNamespace(launch_context={"processing_status": "failed"}),
        (),
    )
    assert launched == "failed"
    assert (
        evidence._scope_kind(resolved_via="selected_run_id", manifest=object())
        == "exact_run"
    )
    assert (
        evidence._scope_kind(
            resolved_via="selected_run_id_not_found", manifest=object()
        )
        == "unresolved"
    )
    assert (
        evidence._scope_kind(resolved_via="latest_success", manifest=object())
        == "pipeline_current"
    )
    assert evidence._overall_status(()) == "UNKNOWN"
    error = EvidenceCheckResult("c", "ERROR", "boom", "d")
    warn = EvidenceCheckResult("c", "WARNING", "warn", "d")
    assert evidence._overall_status((warn, error)) == "ERROR"
    assert evidence._trust_reasons((error,), "ERROR") == ["boom"]
    assert evidence._trust_reasons((warn,), "WARNING") == ["warn"]
    unknown = EvidenceCheckResult("c", "UNKNOWN", "missing", "d")
    assert evidence._trust_reasons((unknown,), "INCOMPLETE") == ["missing"]


def test_integrity_metrics_bool_parse_and_ledger_read_failure() -> None:
    assert integrity._parse_explicit_bool("false") is False
    assert integrity._parse_explicit_bool("TRUE") is True
    assert integrity._parse_explicit_bool("maybe") is None
    manifest = SimpleNamespace(
        launch_context={"run_ledger_enabled": "off"},
        runtime_config=None,
        resolved_config={"pipeline": {"ledger_enabled": "yes"}},
        manifest_id="m1",
        run_id="r1",
    )
    assert integrity.manifest_expects_ledger(manifest) is False  # type: ignore[arg-type]
    enabled = SimpleNamespace(
        launch_context={},
        runtime_config={"control_plane": {"run_ledger_enabled": "1"}},
        resolved_config=None,
        manifest_id="m1",
        run_id="r1",
    )
    assert integrity.manifest_expects_ledger(enabled) is True  # type: ignore[arg-type]
    ledger = SimpleNamespace(
        list_entries=lambda *_a, **_k: (_ for _ in ()).throw(ValueError("missing")),
        list_entries_by_run_id=lambda *_a, **_k: (),
    )
    assert integrity._ledger_matches_manifest(manifest, ledger) is False  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_process_stateful_batch_process_and_commit_failures() -> None:
    fsm = BatchExecutionFSM()

    class _Host:
        _fsm = fsm
        _fsm_state = BatchExecutionState.STREAMING
        _query_string = None
        _processing_port = SimpleNamespace(
            process_batch=AsyncMock(side_effect=ValueError("proc"))
        )
        _execution_state_service = SimpleNamespace(commit_successful_batch=MagicMock())

    host = _Host()
    with pytest.raises(ValueError, match="proc"):
        await process_stateful_batch(host, [], 0)  # type: ignore[arg-type]
    assert host._fsm_state == BatchExecutionState.FAILED

    host._fsm_state = BatchExecutionState.STREAMING
    host._processing_port.process_batch = AsyncMock(return_value=object())
    host._execution_state_service.commit_successful_batch.side_effect = RuntimeError(
        "commit"
    )
    with pytest.raises(RuntimeError, match="commit"):
        await process_stateful_batch(host, [], 0)  # type: ignore[arg-type]
    assert host._fsm_state == BatchExecutionState.FAILED


def test_preflight_schema_annotation_skip_and_extraction_fallbacks() -> None:
    class _Schema:
        __annotations__ = {"id": int, "_secret": str, "_source": str}

    fields = preflight.extract_fields_from_annotations(_Schema, "src")
    assert "id" in fields
    assert "_source" in fields
    assert "_secret" not in fields

    class _ValueBoom:
        @classmethod
        def to_schema(cls) -> object:
            raise ValueError("bad schema")

    host = SimpleNamespace(_logger=MagicMock())
    preflight.extract_fields_from_schema(host, _ValueBoom, "src")  # type: ignore[arg-type]
    host._logger.warning.assert_called()

    class _BioBoom:
        @classmethod
        def to_schema(cls) -> object:
            raise BioETLError("bio")

    host._logger.reset_mock()
    preflight.extract_fields_from_schema(host, _BioBoom, "src")  # type: ignore[arg-type]
    host._logger.warning.assert_called()

    class _DqBoom:
        @classmethod
        def to_schema(cls) -> object:
            raise DataQualityError("dq")

    host._logger.reset_mock()
    preflight.extract_fields_from_schema(host, _DqBoom, "src")  # type: ignore[arg-type]
    host._logger.warning.assert_called()


def test_pipeline_runner_identity_and_require_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = RunResult(
        status=PipelineRunResult.SUCCESS,
        pipeline_name="chembl_activity",
        run_id="r1",
        run_type="full",
    )
    identity = runner_support._identity_from_result(result, options=None, duration=1.5)
    assert identity["provider"] == "chembl"
    assert identity["entity"] == "activity"
    with pytest.raises(TypeError, match="RunResult"):
        runner_support._require_run_result("nope")

    class _Boom:
        def __str__(self) -> str:
            raise RuntimeError("ver")

    monkeypatch.setattr("bioetl.__version__", _Boom(), raising=False)
    assert runner_support._package_version() is None
