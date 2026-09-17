"""Behavior tests closing #10518 application-layer residuals (svc1 batch, part B).

Covers: quality._quarantine_service_filtered_mixin,
control_plane.forensic.diagnostics_support, ops.health_service,
control_plane.manifest.inspection_artifact_refs, run_reports.markdown,
control_plane.manifest.diagnostics.replay_state,
ops._metrics_service_gateway_support.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.unit

from bioetl.application.services.control_plane.forensic import diagnostics_support as _ds  # noqa: E402
from bioetl.application.services.control_plane.manifest.diagnostics import (  # noqa: E402
    replay_state as _rs,
)
from bioetl.application.services.control_plane.manifest.diagnostics.replay_invariants.replay_family_context import (  # noqa: E402
    ReplayFamilyContext,
)
from bioetl.application.services.control_plane.manifest.inspection_artifact_refs import (  # noqa: E402
    _analyze_artifact_ref_pair,
    _artifact_ref_identity_label,
    _artifact_ref_occurrence_difference_fields,
    _artifact_ref_pair_label,
    _artifact_ref_sort_key,
    _semantic_artifact_ref,
    build_artifact_ref_semantic_diff,
)
from bioetl.application.services.control_plane.manifest.inspection_models import (  # noqa: E402
    RunManifestDiffResult,
)
from bioetl.application.services.control_plane.manifest.inspection_result_model import (  # noqa: E402
    RunManifestInspectionResult,
)
from bioetl.application.services.ops._metrics_service_gateway_support import (  # noqa: E402
    _MetricsGatewayMixin,
)
from bioetl.application.services.ops.health_service import (  # noqa: E402
    HealthCheckSummary,
    HealthResult,
    HealthService,
    _NullAsyncContext,
)
from bioetl.application.services.quality.quarantine_service import (  # noqa: E402
    QuarantineService,
)
from bioetl.application.services.run_reports import markdown as _md  # noqa: E402
from bioetl.domain.control_plane import (  # noqa: E402
    ReplayCapability,
    RunManifest,
)
from bioetl.domain.control_plane.reproducibility_policy import (  # noqa: E402
    ReproducibilityPolicyAssessment,
    SnapshotEnvelopeStatus,
)
from bioetl.domain.control_plane.snapshot_materialization import (  # noqa: E402
    HISTORICAL_COMPOSITE_REPLAY_ENVELOPE_CERTIFIED,
    HISTORICAL_SOURCE_SNAPSHOT_CERTIFIED,
    LIVE_CAPTURE_SNAPSHOT_MATERIALIZED,
)
from bioetl.domain.run_reports.models import (  # noqa: E402
    BalanceStatus,
    LayerCounts,
    PipelineRunReport,
    ReasonRemoval,
    StageFunnelRow,
    TrackingCoverage,
    WorkflowExecutionRow,
    WorkflowRunReport,
)


# ---------------------------------------------------------------------------
# quality._quarantine_service_filtered_mixin (via QuarantineService)
# ---------------------------------------------------------------------------


def _quarantine_service(port=None, logger=None):
    return QuarantineService(
        quarantine_port=port if port is not None else AsyncMock(),
        logger=logger if logger is not None else MagicMock(),
        clock=MagicMock(),
        metrics=None,
    )


class TestListFilteredRecords:
    async def test_success_lists_records(self):
        logger = MagicMock()
        port = AsyncMock()
        port.list_filtered_records = AsyncMock(
            return_value={"items": [{"pipeline": "p1"}], "total": 1}
        )
        service = _quarantine_service(port=port, logger=logger)
        result = await service.list_filtered_records(pipeline="p1")
        assert result["total"] == 1
        logger.info.assert_called_once()
        port.list_filtered_records.assert_called_once()

    async def test_operator_error_propagates(self):
        port = AsyncMock()
        port.list_filtered_records = AsyncMock(side_effect=OSError("store down"))
        with pytest.raises(OSError, match="store down"):
            await _quarantine_service(port=port).list_filtered_records()


class TestGetFilteredRecord:
    async def test_success_returns_record(self):
        logger = MagicMock()
        port = AsyncMock()
        port.get_filtered_record = AsyncMock(
            return_value={"pipeline": "p1", "payload_hash": "h"}
        )
        service = _quarantine_service(port=port, logger=logger)
        result = await service.get_filtered_record(payload_hash="h")
        assert result["pipeline"] == "p1"
        logger.info.assert_called_once()

    async def test_missing_returns_none(self):
        logger = MagicMock()
        port = AsyncMock()
        port.get_filtered_record = AsyncMock(return_value=None)
        service = _quarantine_service(port=port, logger=logger)
        assert await service.get_filtered_record(payload_hash="h") is None
        logger.warning.assert_called_once()

    async def test_operator_error_propagates(self):
        port = AsyncMock()
        port.get_filtered_record = AsyncMock(side_effect=ValueError("bad filter"))
        with pytest.raises(ValueError, match="bad filter"):
            await _quarantine_service(port=port).get_filtered_record(payload_hash="h")


class TestGetFilteredStats:
    async def test_success_returns_stats(self):
        logger = MagicMock()
        port = AsyncMock()
        port.get_filtered_stats = AsyncMock(return_value={"total": 4})
        service = _quarantine_service(port=port, logger=logger)
        result = await service.get_filtered_stats(pipeline="p1")
        assert result["total"] == 4
        logger.info.assert_called_once()

    async def test_operator_error_propagates(self):
        port = AsyncMock()
        port.get_filtered_stats = AsyncMock(side_effect=RuntimeError("stats down"))
        with pytest.raises(RuntimeError, match="stats down"):
            await _quarantine_service(port=port).get_filtered_stats()


class TestGetFilteredFilterOptions:
    async def test_success_returns_options(self):
        logger = MagicMock()
        port = AsyncMock()
        port.get_filtered_filter_options = AsyncMock(
            return_value={"run_types": ["incremental"]}
        )
        service = _quarantine_service(port=port, logger=logger)
        result = await service.get_filtered_filter_options()
        assert result == {"run_types": ["incremental"]}
        logger.info.assert_called_once()

    async def test_operator_error_propagates(self):
        port = AsyncMock()
        port.get_filtered_filter_options = AsyncMock(
            side_effect=TypeError("bad options")
        )
        with pytest.raises(TypeError, match="bad options"):
            await _quarantine_service(port=port).get_filtered_filter_options()


class TestGetFilteredTimeseries:
    async def test_success_returns_payload(self):
        logger = MagicMock()
        port = AsyncMock()
        port.get_filtered_timeseries = AsyncMock(
            return_value={"rows": [], "bucket": "1h"}
        )
        service = _quarantine_service(port=port, logger=logger)
        result = await service.get_filtered_timeseries(bucket="1h")
        assert result["bucket"] == "1h"
        logger.info.assert_called_once()

    async def test_operator_error_propagates(self):
        port = AsyncMock()
        port.get_filtered_timeseries = AsyncMock(side_effect=OSError("ts down"))
        with pytest.raises(OSError, match="ts down"):
            await _quarantine_service(port=port).get_filtered_timeseries()


class TestFilteredHostProtocolStub:
    def test_record_metrics_stub_executes(self):
        from bioetl.application.services.quality._quarantine_service_filtered_mixin import (
            _FilteredQuarantineHost,
        )

        assert (
            _FilteredQuarantineHost._record_operator_metrics(
                _quarantine_service(),
                operation="x",
                status="y",
                duration_seconds=0.1,
            )
            is None
        )


# ---------------------------------------------------------------------------
# control_plane.forensic.diagnostics_support
# ---------------------------------------------------------------------------


def _inspection(manifest_id="m1", diagnostics=None, ledger=()):
    return RunManifestInspectionResult(
        manifest=RunManifest(
            manifest_id=manifest_id, execution_fingerprint=f"fp-{manifest_id}"
        ),
        ledger_entries=ledger,
        diagnostics=dict(diagnostics or {}),
    )


def _diff(**overrides):
    kwargs = {
        "left_manifest_id": "m-left",
        "right_manifest_id": "m-right",
        "differences": (),
        "classification": "identical",
        "semantic_equivalent": True,
        "occurrence_only": False,
    }
    kwargs.update(overrides)
    return RunManifestDiffResult(**kwargs)


class TestInspectionServiceFactory:
    def test_provided_factory_returned(self):
        factory = MagicMock()
        assert (
            _ds.inspection_service_factory_from_ports(
                MagicMock(), None, factory
            )
            is factory
        )

    def test_builds_service_from_ports(self):
        from bioetl.application.services.control_plane.manifest.inspection_service import (
            RunManifestInspectionService,
        )

        factory = _ds.inspection_service_factory_from_ports(MagicMock(), None, None)
        assert isinstance(factory(), RunManifestInspectionService)


class TestDictAndArtifactRefs:
    def test_dict_or_empty(self):
        assert _ds.dict_or_empty({"a": 1}) == {"a": 1}
        assert _ds.dict_or_empty(["not", "mapping"]) == {}
        assert _ds.dict_or_empty(None) == {}

    def test_artifact_refs_filters_mappings(self):
        diagnostics = {"artifact_refs": [{"a": 1}, "junk", 42]}
        assert _ds.artifact_refs(diagnostics) == [{"a": 1}]

    def test_artifact_refs_non_list(self):
        assert _ds.artifact_refs({"artifact_refs": "nope"}) == []
        assert _ds.artifact_refs({}) == []


class TestCoerceInt:
    def test_bool_int_float(self):
        assert _ds.coerce_int(True) == 1
        assert _ds.coerce_int(7) == 7
        assert _ds.coerce_int(2.9) == 2

    def test_string_branches(self):
        assert _ds.coerce_int("12") == 12
        assert _ds.coerce_int("nope") == 0

    def test_other_types(self):
        assert _ds.coerce_int(None) == 0
        assert _ds.coerce_int(["x"]) == 0


class TestTraceHelpers:
    def test_sidecar_missing_count(self):
        diagnostics = {
            "artifact_refs": [
                {"metadata_path": "m"},
                {"artifact_id": "a"},
            ]
        }
        assert _ds.metadata_sidecar_missing_count(diagnostics) == 1

    def test_trace_missing_requirements(self):
        assert _ds.trace_missing_requirements(
            {"produced_artifact_trace": {"missing_requirements": ["r1", 2]}}
        ) == ("r1", "2")
        assert _ds.trace_missing_requirements({}) == ()
        assert (
            _ds.trace_missing_requirements(
                {"produced_artifact_trace": {"missing_requirements": "nope"}}
            )
            == ()
        )

    def test_string_list_helpers(self):
        assert _ds.string_list_or_empty(["a", 1]) == ["a", "1"]
        assert _ds.string_list_or_empty("nope") == []
        assert _ds.string_list(("a", "b")) == ["a", "b"]

    def test_trace_complete(self):
        assert _ds.trace_complete({"produced_artifact_trace": {"complete": True}})
        assert not _ds.trace_complete({})


class TestLineageClosurePayload:
    def test_missing_supported(self):
        payload = _ds.lineage_closure_payload(_inspection())
        assert payload["status"] == "missing"
        assert payload["supported"] is None

    def test_supported(self):
        payload = _ds.lineage_closure_payload(
            _inspection(diagnostics={"lineage_closure_boundary": {"supported": True}})
        )
        assert payload["status"] == "supported"

    def test_unsupported(self):
        payload = _ds.lineage_closure_payload(
            _inspection(diagnostics={"lineage_closure_boundary": {"supported": False}})
        )
        assert payload["status"] == "unsupported"


class TestArtifactCompleteness:
    def test_complete_artifact_set(self):
        result = _inspection(
            diagnostics={
                "published_artifact_count": 2,
                "missing_artifact_links": 0,
                "artifact_refs": [{"metadata_path": "m"}],
                "produced_artifact_trace": {"complete": True},
            }
        )
        payload = _ds.artifact_completeness(result)
        assert payload["complete"] is True
        assert payload["metadata_sidecar_count"] == 1

    def test_incomplete_artifact_set(self):
        payload = _ds.artifact_completeness(_inspection())
        assert payload["complete"] is False


class TestReplayAndCheckpointPayloads:
    def test_replay_capability_payload(self):
        left = _inspection(
            "m-left", {"replay_capability": "exact", "persistence_profile": "p1"}
        )
        right = _inspection(
            "m-right", {"replay_capability": "exact", "persistence_profile": "p1"}
        )
        payload = _ds.replay_capability_payload(left=left, right=right)
        assert payload["capability_match"] is True
        assert payload["left"]["manifest_id"] == "m-left"

    def test_replay_capability_mismatch(self):
        left = _inspection("m-left", {"replay_capability": "a"})
        right = _inspection("m-right", {"replay_capability": "b"})
        assert (
            _ds.replay_capability_payload(left=left, right=right)["capability_match"]
            is False
        )

    def test_checkpoint_compatibility_payload(self):
        assert _ds.checkpoint_compatibility_payload({}) == {
            "available": False,
            "compatible": None,
            "matching_fields": [],
            "mismatched_fields": [],
        }
        payload = _ds.checkpoint_compatibility_payload(
            {
                "checkpoint_anchors": {
                    "compatible": True,
                    "matching_fields": ["a"],
                    "mismatched_fields": ["b"],
                }
            }
        )
        assert payload["available"] is True
        assert payload["compatible"] is True
        assert payload["matching_fields"] == ["a"]


class TestResolveForensicVerdict:
    def test_semantic_drift(self):
        manifest_diff = _diff(classification="semantic_drift")
        assert (
            _ds.resolve_forensic_verdict(manifest_diff=manifest_diff, forensic_diff={})
            == "semantic_drift"
        )

    def test_checkpoint_incompatible(self):
        manifest_diff = _diff()
        forensic_diff = {"checkpoint_anchors": {"compatible": False}}
        assert (
            _ds.resolve_forensic_verdict(
                manifest_diff=manifest_diff, forensic_diff=forensic_diff
            )
            == "checkpoint_incompatible"
        )

    def test_occurrence_only_replay(self):
        manifest_diff = _diff(occurrence_only=True)
        assert (
            _ds.resolve_forensic_verdict(manifest_diff=manifest_diff, forensic_diff={})
            == "occurrence_only_replay"
        )

    def test_semantic_equivalent_replay(self):
        assert (
            _ds.resolve_forensic_verdict(manifest_diff=_diff(), forensic_diff={})
            == "semantic_equivalent_replay"
        )


class TestForensicDiffPayload:
    def test_computes_missing_verdict(self):
        manifest_diff = _diff(cross_surface_replay_diff={})
        payload = _ds.forensic_diff_payload(manifest_diff)
        assert payload["verdict"] == "semantic_equivalent_replay"

    def test_keeps_existing_verdict(self):
        manifest_diff = _diff(
            cross_surface_replay_diff={"verdict": "custom", "other": 1}
        )
        assert _ds.forensic_diff_payload(manifest_diff)["verdict"] == "custom"


class TestDiagnosticSnapshot:
    def test_bounded_fields(self):
        diagnostics = {
            "replay_capability": "exact",
            "exact_replay_eligible": True,
            "exact_replay_blockers": ["b"],
            "persistence_profile": "p",
            "published_artifact_count": 2,
            "missing_artifact_links": 1,
            "unrelated": "dropped?",
        }
        snapshot = _ds.diagnostic_snapshot(_inspection("m1", diagnostics))
        assert snapshot["manifest_id"] == "m1"
        assert snapshot["replay_capability"] == "exact"
        assert snapshot["exact_replay_blockers"] == ["b"]
        assert "unrelated" not in snapshot


class TestMissingEvidence:
    def test_all_gaps_reported(self):
        gaps = _ds.missing_evidence(_inspection())
        assert "run_ledger_entries_missing" in gaps
        assert "published_artifacts_missing" in gaps
        assert "produced_artifact_trace_incomplete" in gaps
        assert "lineage_closure_boundary_missing" in gaps

    def test_no_gaps_for_complete_evidence(self):
        result = _inspection(
            diagnostics={
                "published_artifact_count": 1,
                "missing_artifact_links": 0,
                "artifact_refs": [{"metadata_path": "m"}],
                "produced_artifact_trace": {"complete": True},
                "lineage_closure_boundary": {"supported": True},
            },
            ledger=("entry",),
        )
        assert _ds.missing_evidence(result) == ()

    def test_incomplete_links_and_sidecars(self):
        result = _inspection(
            diagnostics={
                "published_artifact_count": 1,
                "missing_artifact_links": 2,
                "artifact_refs": [{"artifact_id": "a"}],
                "produced_artifact_trace": {"complete": True},
                "lineage_closure_boundary": {"supported": True},
            },
            ledger=("entry",),
        )
        gaps = _ds.missing_evidence(result)
        assert "artifact_links_incomplete" in gaps
        assert "metadata_sidecars_missing" in gaps

    def test_unsupported_lineage_boundary(self):
        result = _inspection(
            diagnostics={
                "published_artifact_count": 1,
                "produced_artifact_trace": {"complete": True},
                "lineage_closure_boundary": {"supported": False},
            },
            ledger=("entry",),
        )
        assert "lineage_closure_boundary_unsupported" in _ds.missing_evidence(result)


# ---------------------------------------------------------------------------
# ops.health_service
# ---------------------------------------------------------------------------


def _health_service(factory=None, observer=None):
    from bioetl.domain.types import HealthStatus  # noqa: F401

    return HealthService(
        logger=MagicMock(),
        _factory=factory if factory is not None else MagicMock(),
        clock=MagicMock(now=lambda: datetime(2026, 1, 1, tzinfo=UTC)),
        result_observer=observer,
    )


class _PortAdapter:
    """Adapter implementing the HealthCheckPort protocol."""

    def __init__(self, result):
        self._result = result

    @property
    def provider_name(self) -> str:
        return "p1"

    async def check_health(self):
        return self._result


class _SimpleAdapter:
    """Composite-style adapter with only a health_check coroutine."""

    def __init__(self, status):
        self._status = status

    async def health_check(self):
        return self._status


def _health_result(status_name="HEALTHY"):
    from bioetl.domain.ports import HealthCheckResult
    from bioetl.domain.types import HealthStatus

    return HealthCheckResult(
        status=HealthStatus[status_name],
        latency_ms=2.5,
        provider="p1",
        endpoint="/health",
    )


class TestCheckProviders:
    async def test_all_providers_checked_with_observer(self):
        from bioetl.domain.types import HealthStatus  # noqa: F401

        seen = []
        factory = MagicMock()
        factory.list_providers.return_value = ["p1", "p2"]
        factory.create.side_effect = lambda name: _PortAdapter(_health_result())
        service = _health_service(factory=factory, observer=seen.append)
        summary = await service.check_providers()
        assert summary.all_healthy is True
        assert summary.healthy_count == 2
        assert summary.unhealthy_count == 0
        assert [result.provider for result in seen] == ["p1", "p2"]
        assert set(summary.to_dict()) == {"p1", "p2"}

    async def test_observer_skipped_for_unknown_provider(self):
        seen = []
        factory = MagicMock()
        factory.list_providers.return_value = ["p1"]
        factory.create.side_effect = lambda name: (
            _PortAdapter(_health_result()) if name == "p1" else object()
        )
        service = _health_service(factory=factory, observer=seen.append)
        summary = await service.check_providers(providers=["p1", "ghost"])
        assert summary.all_healthy is False
        assert summary.results["ghost"].status == "unknown"
        assert [result.provider for result in seen] == ["p1"]

    async def test_simple_health_check_adapter(self):
        from bioetl.domain.types import HealthStatus

        factory = MagicMock()
        factory.list_providers.return_value = ["p1"]
        factory.create.return_value = _SimpleAdapter(HealthStatus.DEGRADED)
        service = _health_service(factory=factory)
        summary = await service.check_providers()
        assert summary.results["p1"].status == "degraded"
        assert summary.results["p1"].is_degraded

    async def test_factory_error_reports_unhealthy(self):
        factory = MagicMock()
        factory.list_providers.return_value = ["p1"]
        factory.create.side_effect = OSError("cannot create")
        service = _health_service(factory=factory)
        summary = await service.check_providers()
        result = summary.results["p1"]
        assert result.status == "unhealthy"
        assert result.is_unhealthy
        assert "cannot create" in result.error


class TestHealthResultModel:
    def test_status_properties(self):
        assert HealthResult(provider="p", status="healthy").is_healthy
        assert HealthResult(provider="p", status="degraded").is_degraded
        assert HealthResult(provider="p", status="unknown").is_unhealthy

    def test_to_dict_branches(self):
        full = HealthResult(
            provider="p",
            status="healthy",
            latency_ms=1.234,
            endpoint="/h",
            error="e",
        ).to_dict()
        assert full == {
            "status": "healthy",
            "latency_ms": "1.23",
            "endpoint": "/h",
            "error": "e",
        }
        assert HealthResult(provider="p", status="unknown").to_dict() == {
            "status": "unknown"
        }

    def test_summary_counts(self):
        summary = HealthCheckSummary(
            results={
                "a": HealthResult(provider="a", status="healthy"),
                "b": HealthResult(provider="b", status="unhealthy"),
            },
            all_healthy=False,
        )
        assert summary.healthy_count == 1
        assert summary.unhealthy_count == 1


class _AsyncContext:
    def __init__(self):
        self.entered = False
        self.exited = False

    async def __aenter__(self):
        self.entered = True
        return self

    async def __aexit__(self, *exc):
        self.exited = True
        return None


class TestHealthProbeContext:
    def test_adapter_lifecycle_preferred(self):
        service = _health_service()
        adapter = _AsyncContext()
        assert service._health_probe_context(adapter) is adapter

    def test_http_client_attribute(self):
        service = _health_service()
        client = _AsyncContext()
        adapter = SimpleNamespace(http_client=client)
        assert service._health_probe_context(adapter) is client

    def test_private_http_client_attribute(self):
        service = _health_service()
        client = _AsyncContext()
        adapter = SimpleNamespace(_http_client=client)
        assert service._health_probe_context(adapter) is client

    def test_nested_client_attribute(self):
        service = _health_service()
        client = _AsyncContext()
        adapter = SimpleNamespace(_client=SimpleNamespace(http_client=client))
        assert service._health_probe_context(adapter) is client

    def test_nested_client_without_http_client(self):
        service = _health_service()
        adapter = SimpleNamespace(_client=SimpleNamespace())
        assert isinstance(
            service._health_probe_context(adapter), _NullAsyncContext
        )

    def test_fallback_null_context(self):
        service = _health_service()
        assert isinstance(
            service._health_probe_context(SimpleNamespace()), _NullAsyncContext
        )

    async def test_adapter_probe_uses_http_client_context(self):
        client = _AsyncContext()
        adapter = _PortAdapter(_health_result())
        adapter.http_client = client
        factory = MagicMock()
        factory.list_providers.return_value = ["p1"]
        factory.create.return_value = adapter
        summary = await _health_service(factory=factory).check_providers()
        assert summary.results["p1"].is_healthy
        assert client.entered and client.exited

    async def test_null_context_roundtrip(self):
        context = _NullAsyncContext()
        assert await context.__aenter__() is context
        assert await context.__aexit__(None, None, None) is None

    def test_list_available_providers(self):
        factory = MagicMock()
        factory.list_providers.return_value = ["p1", "p2"]
        assert _health_service(factory=factory).list_available_providers() == [
            "p1",
            "p2",
        ]


# ---------------------------------------------------------------------------
# control_plane.manifest.inspection_artifact_refs
# ---------------------------------------------------------------------------


class TestArtifactRefSortKey:
    def test_orders_by_stage_dataset_fragment(self):
        refs = [
            {"stage": "silver", "dataset_ref": "b", "lineage_fragment_id": "f"},
            {"stage": "bronze", "artifact_id": "a"},
        ]
        assert sorted(refs, key=_artifact_ref_sort_key)[0]["stage"] == "bronze"

    def test_fallback_fields(self):
        key = _artifact_ref_sort_key({})
        assert key == ("", "", "", "", "", "")
        key = _artifact_ref_sort_key(
            {
                "dataset_ref": "d",
                "artifact_path": "p",
                "metadata_path": "m",
                "event_type": "e",
            }
        )
        assert key[1] == "d"


class TestSemanticArtifactRef:
    def test_drops_occurrence_only_fields(self):
        ref = {"run_id": "r", "manifest_id": "m", "stage": "bronze"}
        assert _semantic_artifact_ref(ref) == {"stage": "bronze"}


class TestArtifactRefLabels:
    def test_identity_label_fallbacks(self):
        assert _artifact_ref_identity_label({"artifact_id": "a"}, 0) == "a"
        assert _artifact_ref_identity_label({"dataset_ref": "d"}, 0) == "d"
        assert _artifact_ref_identity_label({}, 3) == "3"

    def test_pair_label(self):
        assert (
            _artifact_ref_pair_label({"artifact_id": "a"}, {"artifact_id": "b"}, index=0)
            == "a == b"
        )


class TestOccurrenceDifferenceFields:
    def test_reports_only_occurrence_fields(self):
        left = {"run_id": "r1", "manifest_id": "m", "stage": "bronze"}
        right = {"run_id": "r2", "manifest_id": "m", "stage": "bronze"}
        assert _artifact_ref_occurrence_difference_fields(
            index=0, left_ref=left, right_ref=right
        ) == ["artifact_refs[0].run_id"]

    def test_no_differences(self):
        ref = {"run_id": "r", "stage": "s"}
        assert (
            _artifact_ref_occurrence_difference_fields(
                index=1, left_ref=ref, right_ref=dict(ref)
            )
            == []
        )


class TestAnalyzeArtifactRefPair:
    def test_semantic_difference(self):
        label, field, occurrence = _analyze_artifact_ref_pair(
            index=2,
            left_ref={"stage": "bronze"},
            right_ref={"stage": "silver"},
        )
        assert field == "artifact_refs[2]"
        assert occurrence == []
        assert "==" in label

    def test_occurrence_only_difference(self):
        label, field, occurrence = _analyze_artifact_ref_pair(
            index=0,
            left_ref={"stage": "s", "run_id": "r1"},
            right_ref={"stage": "s", "run_id": "r2"},
        )
        assert field is None
        assert occurrence == ["artifact_refs[0].run_id"]

    def test_identical_refs(self):
        label, field, occurrence = _analyze_artifact_ref_pair(
            index=0,
            left_ref={"stage": "s", "run_id": "r"},
            right_ref={"stage": "s", "run_id": "r"},
        )
        assert (field, occurrence) == (None, [])


class TestBuildArtifactRefSemanticDiff:
    def test_empty_refs(self):
        payload = build_artifact_ref_semantic_diff(
            left_artifact_refs=(), right_artifact_refs=()
        )
        assert payload["artifact_refs_available"] is False
        assert payload["artifact_ref_semantic_equivalent"] is True
        assert payload["artifact_ref_occurrence_only"] is False

    def test_count_mismatch_is_semantic(self):
        payload = build_artifact_ref_semantic_diff(
            left_artifact_refs=({"stage": "s"},),
            right_artifact_refs=({"stage": "s"}, {"stage": "t"}),
        )
        assert "artifact_ref_count" in payload["artifact_ref_semantic_difference_fields"]
        assert payload["left_artifact_ref_count"] == 1
        assert payload["right_artifact_ref_count"] == 2
        assert payload["artifact_ref_semantic_equivalent"] is False

    def test_occurrence_only_drift(self):
        payload = build_artifact_ref_semantic_diff(
            left_artifact_refs=({"stage": "s", "run_id": "r1"},),
            right_artifact_refs=({"stage": "s", "run_id": "r2"},),
        )
        assert payload["artifact_ref_semantic_equivalent"] is True
        assert payload["artifact_ref_occurrence_only"] is True
        assert payload["artifact_ref_occurrence_difference_fields"] == [
            "artifact_refs[0].run_id"
        ]
        assert payload["artifact_ref_pairs"] == ["0 == 0"]

    def test_semantic_difference_in_build(self):
        payload = build_artifact_ref_semantic_diff(
            left_artifact_refs=({"stage": "bronze", "artifact_id": "a"},),
            right_artifact_refs=({"stage": "silver", "artifact_id": "a"},),
        )
        assert payload["artifact_ref_semantic_difference_fields"] == [
            "artifact_refs[0]"
        ]
        assert payload["artifact_ref_semantic_equivalent"] is False
        assert payload["artifact_ref_occurrence_only"] is False


# ---------------------------------------------------------------------------
# run_reports.markdown
# ---------------------------------------------------------------------------


def _pipeline_report(**overrides):
    funnel = (
        StageFunnelRow(
            stage_id="silver",
            records_in=10,
            records_out=7,
            removed_total=3,
            removals=(
                ReasonRemoval(
                    outcome="filtered_out",
                    reason_code="bad_value",
                    count=3,
                    sample_refs=("s1", "s2"),
                ),
            ),
            balance_status=BalanceStatus.OK,
            tracking=TrackingCoverage.FULL,
        ),
        StageFunnelRow(
            stage_id="gold",
            records_in=7,
            records_out=7,
            removed_total=0,
            removals=(),
            balance_status=BalanceStatus.OK,
            tracking=TrackingCoverage.FULL,
        ),
    )
    report = PipelineRunReport(
        identity={
            "pipeline_name": "pipe1",
            "run_id": "run1",
            "status": "success",
            "run_type": "incremental",
            "manifest_id": "manifest-1",
            "provider": "chembl",
            "entity": "activity",
            "started_at": "2026-01-01",
            "completed_at": "2026-01-02",
            "duration_seconds": 3.5,
            "workflow_run_id": "wrun1",
            "workflow_id": "wf1",
            "workflow_step_id": "s1",
        },
        funnel=funnel,
        layers=LayerCounts(bronze_records=10, silver_valid=7),
        reasons_top_n=(
            {"reason_code": "bad_value", "outcome": "filtered_out", "count": 3},
        ),
        reconciliation={
            "silver_vs_bronze_status": "OK",
            "silver_delta": 0,
            "gold_vs_silver_status": "OK",
            "gold_delta": 0,
        },
        tracking_coverage=TrackingCoverage.FULL,
        reason_catalog_version="v1",
        artifacts=(
            {"kind": "report", "ref": "r.json", "hash": "abc"},
            {"kind": "log", "ref": "l.txt"},
        ),
        failure={"stage": "none"},
        stage_timings={"silver": [1.0, 2.0]},
    )
    assert not overrides, "pipeline fixture takes no overrides"
    return report


def _workflow_report(**overrides):
    execution = (
        WorkflowExecutionRow(
            step_id="s1",
            status="success",
            records_extracted=10,
            pipeline_name="pipe1",
            records_silver=7,
            records_gold=None,
            pipeline_report_ref="reports/r.json",
            top_reasons=({"reason_code": "bad_value", "count": 3},),
            skip_reason="manual-skip",
        ),
        WorkflowExecutionRow(
            step_id="s2",
            status="success",
            records_extracted=4,
            pipeline_name=None,
            records_silver=None,
            records_gold=2,
            pipeline_report_ref=None,
        ),
    )
    kwargs = {
        "identity": {
            "workflow_name": "wf1",
            "workflow_run_id": "wrun1",
            "status": "success",
            "resumed": False,
            "execution_fingerprint": "fp",
            "duration_seconds": 9.0,
        },
        "plan_steps": (
            {"step_id": "s1", "kind": "pipeline", "depends_on": []},
            {"step_id": "s2", "kind": "pipeline", "depends_on": ["s1"]},
        ),
        "execution": execution,
        "totals": {
            "steps_planned": 2,
            "steps_succeeded": 2,
            "steps_failed": 0,
            "steps_skipped": 0,
            "records_extracted_sum": 14,
            "records_silver_sum": 7,
            "records_gold_sum": 2,
        },
        "reasons_rollup": (
            {"reason_code": "bad_value", "outcome": "filtered_out", "count": 3},
        ),
    }
    kwargs.update(overrides)
    return WorkflowRunReport(**kwargs)


class TestRenderPipelineMarkdown:
    def test_full_report_sections(self):
        text = _md.render_pipeline_run_report_markdown(_pipeline_report())
        assert "# Pipeline run report: pipe1" in text
        assert "bad_value=3" in text
        assert "## Top samples" in text
        assert "`silver` / `bad_value`: `s1`, `s2`" in text
        assert "## Artifacts" in text
        assert "(hash=abc)" in text
        assert "## Failure" in text
        assert "## Stage timings" in text
        assert "`manifest-1`" in text
        assert "provider/entity" in text
        assert "workflow:" in text
        assert "## Reconciliation" in text

    def test_minimal_report(self):
        report = _pipeline_report()
        minimal = PipelineRunReport(
            identity={"pipeline_name": "pipe1", "run_id": "r", "status": "success"},
            funnel=(),
            layers=LayerCounts(),
            reasons_top_n=(),
            reconciliation={},
            tracking_coverage=TrackingCoverage.PARTIAL,
            reason_catalog_version="v1",
        )
        text = _md.render_pipeline_run_report_markdown(minimal)
        assert "- (none)" in text
        assert "## Artifacts" not in text
        assert report is not None


class TestRenderWorkflowMarkdown:
    def test_full_workflow_report(self):
        text = _md.render_workflow_run_report_markdown(_workflow_report())
        assert "# Workflow run report: wf1" in text
        assert "## Steps" in text
        assert "report: `reports/r.json`" in text
        assert "top reasons: bad_value=3" in text
        assert "skip_reason: `manual-skip`" in text
        assert "## Plan / DAG" in text
        assert "```mermaid" in text
        assert "s1 --> s2" in text
        assert "## Totals" in text
        assert "records_silver_sum" in text
        assert "## Reasons rollup" in text

    def test_empty_plan_and_reasons(self):
        report = _workflow_report(plan_steps=(), reasons_rollup=())
        text = _md.render_workflow_run_report_markdown(report)
        assert "## Plan / DAG" not in text
        assert "## Reasons rollup" not in text

    def test_totals_without_optional_sums(self):
        report = _workflow_report(
            totals={
                "steps_planned": 2,
                "steps_succeeded": 2,
                "steps_failed": 0,
                "steps_skipped": 0,
                "records_extracted_sum": 14,
            }
        )
        text = _md.render_workflow_run_report_markdown(report)
        assert "records_silver_sum" not in text
        assert "records_gold_sum" not in text

    def test_samples_section_skips_empty_removals(self):
        funnel = (
            StageFunnelRow(
                stage_id="silver",
                records_in=10,
                records_out=10,
                removed_total=0,
                removals=(
                    ReasonRemoval(
                        outcome="filtered_out", reason_code="unused", count=0
                    ),
                ),
                balance_status=BalanceStatus.OK,
                tracking=TrackingCoverage.FULL,
            ),
        )
        report = PipelineRunReport(
            identity={"pipeline_name": "pipe1", "run_id": "r", "status": "success"},
            funnel=funnel,
            layers=LayerCounts(),
            reasons_top_n=(),
            reconciliation={},
            tracking_coverage=TrackingCoverage.FULL,
            reason_catalog_version="v1",
        )
        assert "## Top samples" not in _md.render_pipeline_run_report_markdown(report)

    def test_mermaid_id_fallback(self):
        assert _md._mermaid_id("a-b c!") == "a_b_c_"
        assert _md._mermaid_id("!!!") == "___"
        assert _md._mermaid_id("") == "step"


# ---------------------------------------------------------------------------
# control_plane.manifest.diagnostics.replay_state
# ---------------------------------------------------------------------------


def _strict_profile():
    return SimpleNamespace(
        strict_exact_replay_supported=True,
        post_capture_replayable_parent_supported=True,
    )


def _family_context(profile=None):
    return ReplayFamilyContext(
        execution_context="source",
        profile=profile if profile is not None else _strict_profile(),
        replay_family_contract={},
        replay_family_contract_payload={},
        exact_replay_support_boundary="test",
        strict_exact_replay_supported=True,
    )


def _envelope(any_input=False, full=False):
    return SnapshotEnvelopeStatus(
        source_count=1,
        sources_with_snapshots=1 if any_input else 0,
        any_input_snapshots=any_input,
        full_snapshot_envelope=full,
        require_full_snapshot_envelope=False,
    )


def _assessment(envelope=None, capability=ReplayCapability.REBUILD_ONLY):
    from bioetl.domain.control_plane._reproducibility_policy_verdicts import (
        ReplayReadinessVerdict,
    )

    return ReproducibilityPolicyAssessment(
        required_persistence_profile="standard",
        replay_capability=capability,
        strict_requirement_requested=False,
        strict_exact_replay_supported=False,
        snapshot_envelope=envelope if envelope is not None else _envelope(),
        blocking_gaps=(),
        replay_readiness_verdict=ReplayReadinessVerdict.REBUILD_ONLY,
    )


def _composite_manifest():
    return RunManifest(launch_context={"execution_context": "composite"})


class TestResolveReplayCapabilityReason:
    def test_family_outside_boundary(self):
        profile = SimpleNamespace(strict_exact_replay_supported=False)
        reason = _rs._resolve_replay_capability_reason(
            manifest=RunManifest(),
            input_snapshots=[],
            resume_requested=False,
            policy_assessment=_assessment(),
            replay_family_context=_family_context(profile),
        )
        assert reason == "family_outside_supported_exact_replay_boundary"

    def test_partial_input_envelope(self):
        reason = _rs._resolve_replay_capability_reason(
            manifest=RunManifest(),
            input_snapshots=[],
            resume_requested=False,
            policy_assessment=_assessment(_envelope(any_input=True, full=False)),
            replay_family_context=_family_context(),
        )
        assert reason == "partial_input_snapshot_envelope"

    def test_certified_historical_composite(self):
        snapshots = [
            {"materialization_mode": HISTORICAL_COMPOSITE_REPLAY_ENVELOPE_CERTIFIED}
        ]
        reason = _rs._resolve_replay_capability_reason(
            manifest=RunManifest(),
            input_snapshots=snapshots,
            resume_requested=False,
            policy_assessment=_assessment(_envelope(any_input=True, full=True)),
            replay_family_context=_family_context(),
        )
        assert reason == "certified_historical_composite_snapshot_envelope_present"

    def test_certified_historical_source(self):
        snapshots = [{"materialization_mode": HISTORICAL_SOURCE_SNAPSHOT_CERTIFIED}]
        reason = _rs._resolve_replay_capability_reason(
            manifest=RunManifest(),
            input_snapshots=snapshots,
            resume_requested=False,
            policy_assessment=_assessment(_envelope(any_input=True, full=True)),
            replay_family_context=_family_context(),
        )
        assert reason == "certified_historical_source_snapshot_envelope_present"

    def test_materialized_live_capture_supported(self):
        snapshots = [{"materialization_mode": LIVE_CAPTURE_SNAPSHOT_MATERIALIZED}]
        reason = _rs._resolve_replay_capability_reason(
            manifest=RunManifest(
                replay_capability=ReplayCapability.EXACT_REPLAY_SUPPORTED
            ),
            input_snapshots=snapshots,
            resume_requested=False,
            policy_assessment=_assessment(_envelope(any_input=True, full=True)),
            replay_family_context=_family_context(),
        )
        assert reason == "materialized_live_capture_snapshot_envelope_present"

    def test_composite_envelope_missing(self):
        reason = _rs._resolve_replay_capability_reason(
            manifest=_composite_manifest(),
            input_snapshots=[],
            resume_requested=False,
            policy_assessment=_assessment(_envelope()),
            replay_family_context=_family_context(),
        )
        assert reason == "composite_snapshot_envelope_missing"

    def test_immutable_snapshots_missing(self):
        reason = _rs._resolve_replay_capability_reason(
            manifest=RunManifest(),
            input_snapshots=[],
            resume_requested=False,
            policy_assessment=_assessment(_envelope()),
            replay_family_context=_family_context(),
        )
        assert reason == "immutable_input_snapshots_missing"


class TestResolveReplayOccurrenceKind:
    def test_historical_composite_incomplete(self):
        kind = _rs._resolve_replay_occurrence_kind(
            manifest=RunManifest(),
            input_snapshots=[
                {"materialization_mode": HISTORICAL_COMPOSITE_REPLAY_ENVELOPE_CERTIFIED}
            ],
            policy_assessment=_assessment(_envelope(any_input=True, full=False)),
        )
        assert kind == "historical_composite_certification_incomplete"

    def test_historical_composite_certified_parent(self):
        kind = _rs._resolve_replay_occurrence_kind(
            manifest=RunManifest(),
            input_snapshots=[
                {"materialization_mode": HISTORICAL_COMPOSITE_REPLAY_ENVELOPE_CERTIFIED}
            ],
            policy_assessment=_assessment(_envelope(any_input=True, full=True)),
        )
        assert kind == "historical_composite_replay_certified_parent"

    def test_historical_source_certified_parent(self):
        kind = _rs._resolve_replay_occurrence_kind(
            manifest=RunManifest(),
            input_snapshots=[
                {"materialization_mode": HISTORICAL_SOURCE_SNAPSHOT_CERTIFIED}
            ],
            policy_assessment=_assessment(_envelope(any_input=True, full=True)),
        )
        assert kind == "historical_source_replay_certified_parent"

    def test_historical_source_incomplete(self):
        kind = _rs._resolve_replay_occurrence_kind(
            manifest=RunManifest(),
            input_snapshots=[
                {"materialization_mode": HISTORICAL_SOURCE_SNAPSHOT_CERTIFIED}
            ],
            policy_assessment=_assessment(_envelope(any_input=True, full=False)),
        )
        assert kind == "historical_source_certification_incomplete"

    def test_materialized_parent_incomplete(self):
        kind = _rs._resolve_replay_occurrence_kind(
            manifest=RunManifest(),
            input_snapshots=[
                {"materialization_mode": LIVE_CAPTURE_SNAPSHOT_MATERIALIZED}
            ],
            policy_assessment=_assessment(_envelope(any_input=True, full=False)),
        )
        assert kind == "materialized_parent_incomplete"

    def test_materialized_replayable_parent(self):
        kind = _rs._resolve_replay_occurrence_kind(
            manifest=RunManifest(),
            input_snapshots=[
                {"materialization_mode": LIVE_CAPTURE_SNAPSHOT_MATERIALIZED}
            ],
            policy_assessment=_assessment(_envelope(any_input=True, full=True)),
        )
        assert kind == "materialized_replayable_parent"

    def test_ordinary_live_capture(self):
        kind = _rs._resolve_replay_occurrence_kind(
            manifest=RunManifest(),
            input_snapshots=[],
            policy_assessment=_assessment(_envelope()),
        )
        assert kind == "ordinary_live_capture"

    def test_launch_time_snapshot_backed(self):
        kind = _rs._resolve_replay_occurrence_kind(
            manifest=RunManifest(),
            input_snapshots=[],
            policy_assessment=_assessment(_envelope(full=True)),
        )
        assert kind == "launch_time_snapshot_backed_run"


class TestResolveHistoricalLiveRunUpgradeState:
    def test_composite_is_not_applicable(self):
        state = _rs._resolve_historical_live_run_upgrade_state(
            manifest=_composite_manifest(),
            input_snapshots=[],
            policy_assessment=_assessment(_envelope()),
            replay_family_context=_family_context(),
        )
        assert state == "not_applicable"

    def test_historical_source_certified(self):
        state = _rs._resolve_historical_live_run_upgrade_state(
            manifest=RunManifest(),
            input_snapshots=[
                {"materialization_mode": HISTORICAL_SOURCE_SNAPSHOT_CERTIFIED}
            ],
            policy_assessment=_assessment(_envelope(any_input=True, full=True)),
            replay_family_context=_family_context(),
        )
        assert state == "historical_source_replay_certified"

    def test_historical_source_incomplete(self):
        state = _rs._resolve_historical_live_run_upgrade_state(
            manifest=RunManifest(),
            input_snapshots=[
                {"materialization_mode": HISTORICAL_SOURCE_SNAPSHOT_CERTIFIED}
            ],
            policy_assessment=_assessment(_envelope(any_input=True, full=False)),
            replay_family_context=_family_context(),
        )
        assert state == "historical_source_certification_incomplete"

    def test_already_materialized(self):
        state = _rs._resolve_historical_live_run_upgrade_state(
            manifest=RunManifest(),
            input_snapshots=[
                {"materialization_mode": LIVE_CAPTURE_SNAPSHOT_MATERIALIZED}
            ],
            policy_assessment=_assessment(_envelope(any_input=True, full=True)),
            replay_family_context=_family_context(),
        )
        assert state == "already_materialized_replayable_parent"

    def test_incomplete_materialization(self):
        state = _rs._resolve_historical_live_run_upgrade_state(
            manifest=RunManifest(),
            input_snapshots=[
                {"materialization_mode": LIVE_CAPTURE_SNAPSHOT_MATERIALIZED}
            ],
            policy_assessment=_assessment(_envelope(any_input=True, full=False)),
            replay_family_context=_family_context(),
        )
        assert state == "incomplete_materialization_evidence"

    def test_not_needed_when_snapshot_backed(self):
        state = _rs._resolve_historical_live_run_upgrade_state(
            manifest=RunManifest(),
            input_snapshots=[],
            policy_assessment=_assessment(_envelope(full=True)),
            replay_family_context=_family_context(),
        )
        assert state == "not_needed_snapshot_backed_at_launch"


class TestResolveBroaderHistoricalExactReplayState:
    def _state(self, snapshots, full):
        return _rs._resolve_broader_historical_exact_replay_state(
            manifest=RunManifest(),
            input_snapshots=snapshots,
            policy_assessment=_assessment(_envelope(any_input=bool(snapshots), full=full)),
        )

    def test_historical_composite_certified(self):
        assert self._state(
            [{"materialization_mode": HISTORICAL_COMPOSITE_REPLAY_ENVELOPE_CERTIFIED}],
            True,
        ) == "historical_composite_replay_certified"

    def test_historical_composite_incomplete(self):
        assert self._state(
            [{"materialization_mode": HISTORICAL_COMPOSITE_REPLAY_ENVELOPE_CERTIFIED}],
            False,
        ) == "historical_composite_certification_incomplete"

    def test_historical_source_certified(self):
        assert self._state(
            [{"materialization_mode": HISTORICAL_SOURCE_SNAPSHOT_CERTIFIED}], True
        ) == "historical_source_replay_certified"

    def test_within_post_capture_boundary(self):
        assert self._state(
            [{"materialization_mode": LIVE_CAPTURE_SNAPSHOT_MATERIALIZED}], False
        ) == "within_post_capture_parent_boundary"

    def test_within_launch_time_boundary(self):
        assert self._state([], True) == "within_launch_time_snapshot_boundary"

    def test_awaiting_certification(self):
        assert self._state([], False) == "awaiting_historical_snapshot_certification"


class TestResolveReplayMode:
    def test_exact_replay(self):
        mode = _rs._resolve_replay_mode(
            manifest=RunManifest(
                replay_capability=ReplayCapability.EXACT_REPLAY_SUPPORTED
            ),
            requested_exact_replay=True,
            resume_requested=False,
            replay_family_context=_family_context(),
        )
        assert mode == "exact_replay"

    def test_same_data_state_recovery(self):
        mode = _rs._resolve_replay_mode(
            manifest=RunManifest(
                replay_capability=ReplayCapability.EXACT_REPLAY_SUPPORTED
            ),
            requested_exact_replay=False,
            resume_requested=False,
            replay_family_context=_family_context(),
        )
        assert mode == "same_data_state_recovery"

    def test_resume(self):
        mode = _rs._resolve_replay_mode(
            manifest=RunManifest(replay_capability=ReplayCapability.RESUME_ONLY),
            requested_exact_replay=False,
            resume_requested=False,
            replay_family_context=_family_context(),
        )
        assert mode == "resume"

    def test_resume_requested(self):
        mode = _rs._resolve_replay_mode(
            manifest=RunManifest(),
            requested_exact_replay=False,
            resume_requested=True,
            replay_family_context=_family_context(),
        )
        assert mode == "resume"

    def test_rebuild(self):
        mode = _rs._resolve_replay_mode(
            manifest=RunManifest(),
            requested_exact_replay=False,
            resume_requested=False,
            replay_family_context=_family_context(),
        )
        assert mode == "rebuild"


class TestResolveContinuationMode:
    def test_exact_replay(self):
        mode = _rs._resolve_continuation_mode(
            manifest=RunManifest(
                replay_capability=ReplayCapability.EXACT_REPLAY_SUPPORTED
            ),
            requested_exact_replay=True,
            resume_requested=False,
            replay_family_context=_family_context(),
        )
        assert mode == "exact_replay"

    def test_full_scan_idempotent_rebuild(self):
        mode = _rs._resolve_continuation_mode(
            manifest=RunManifest(
                launch_context={"full_scan_idempotent_rebuild": True}
            ),
            requested_exact_replay=False,
            resume_requested=False,
            replay_family_context=_family_context(),
        )
        assert mode == "full_scan_idempotent_rebuild"

    def test_composite_resume(self):
        mode = _rs._resolve_continuation_mode(
            manifest=_composite_manifest(),
            requested_exact_replay=False,
            resume_requested=True,
            replay_family_context=_family_context(),
        )
        assert mode == "checkpoint_snapshot_plus_ledger_suffix_resume"

    def test_snapshot_only_resume(self):
        mode = _rs._resolve_continuation_mode(
            manifest=RunManifest(),
            requested_exact_replay=False,
            resume_requested=True,
            replay_family_context=_family_context(),
        )
        assert mode == "checkpoint_snapshot_only_resume"

    def test_rebuild_only(self):
        mode = _rs._resolve_continuation_mode(
            manifest=RunManifest(),
            requested_exact_replay=False,
            resume_requested=False,
            replay_family_context=_family_context(),
        )
        assert mode == "rebuild_only"


class TestReplayStateResidualBranches:
    def test_append_mode_sinks_block_exact_replay(self):
        reason = _rs._resolve_replay_capability_reason(
            manifest=RunManifest(
                runtime_config={"sink": {"gold": {"mode": "append"}}}
            ),
            input_snapshots=[],
            resume_requested=False,
            policy_assessment=_assessment(_envelope()),
            replay_family_context=_family_context(),
        )
        assert reason == "append_mode_semantic_outputs_block_exact_replay"

    def test_resume_without_snapshot_inputs(self):
        reason = _rs._resolve_replay_capability_reason(
            manifest=RunManifest(),
            input_snapshots=[],
            resume_requested=True,
            policy_assessment=_assessment(_envelope()),
            replay_family_context=_family_context(),
        )
        assert reason == "resume_requested_without_snapshot_backed_inputs"

    def test_exact_replay_child_occurrence_kind(self):
        kind = _rs._resolve_replay_occurrence_kind(
            manifest=RunManifest(replay_of_manifest_id="m0"),
            input_snapshots=[],
            policy_assessment=_assessment(_envelope()),
        )
        assert kind == "exact_replay_child_run"

    def test_exact_replay_child_upgrade_not_applicable(self):
        state = _rs._resolve_historical_live_run_upgrade_state(
            manifest=RunManifest(replay_of_manifest_id="m0"),
            input_snapshots=[],
            policy_assessment=_assessment(_envelope()),
            replay_family_context=_family_context(),
        )
        assert state == "not_applicable"

    def test_exact_replay_child_broader_state(self):
        state = _rs._resolve_broader_historical_exact_replay_state(
            manifest=RunManifest(replay_of_run_id="r0"),
            input_snapshots=[],
            policy_assessment=_assessment(_envelope()),
        )
        assert state == "exact_replay_child_run"

    def test_outside_supported_boundary(self):
        profile = SimpleNamespace(
            strict_exact_replay_supported=True,
            post_capture_replayable_parent_supported=False,
        )
        state = _rs._resolve_historical_live_run_upgrade_state(
            manifest=RunManifest(),
            input_snapshots=[],
            policy_assessment=_assessment(_envelope()),
            replay_family_context=_family_context(profile),
        )
        assert state == "outside_supported_boundary"

    def test_awaiting_input_snapshot_evidence(self):
        state = _rs._resolve_historical_live_run_upgrade_state(
            manifest=RunManifest(),
            input_snapshots=[],
            policy_assessment=_assessment(_envelope()),
            replay_family_context=_family_context(),
        )
        assert state == "awaiting_input_snapshot_published_evidence"

    def test_broader_source_incomplete(self):
        state = _rs._resolve_broader_historical_exact_replay_state(
            manifest=RunManifest(),
            input_snapshots=[
                {"materialization_mode": HISTORICAL_SOURCE_SNAPSHOT_CERTIFIED}
            ],
            policy_assessment=_assessment(_envelope(any_input=True, full=False)),
        )
        assert state == "historical_source_certification_incomplete"

    def test_broader_awaiting_certified_source_lineage(self):
        state = _rs._resolve_broader_historical_exact_replay_state(
            manifest=_composite_manifest(),
            input_snapshots=[],
            policy_assessment=_assessment(_envelope()),
        )
        assert state == "awaiting_certified_source_lineage"


class TestBuildReplayStateProjection:
    def test_projection_keys(self):
        projection = _rs._build_replay_state_projection(
            manifest=RunManifest(),
            input_snapshots=[],
            policy_assessment=_assessment(_envelope()),
            replay_family_context=_family_context(),
        )
        assert projection["replay_occurrence_kind"] == "ordinary_live_capture"
        assert projection["historical_live_run_upgrade_state"] in (
            "awaiting_input_snapshot_published_evidence",
            "outside_supported_boundary",
        )
        assert (
            projection["broader_historical_exact_replay_state"]
            == "awaiting_historical_snapshot_certification"
        )
        assert "source_posture" in projection


# ---------------------------------------------------------------------------
# ops._metrics_service_gateway_support
# ---------------------------------------------------------------------------


class _GatewayHost(_MetricsGatewayMixin):
    def __init__(self, logger=None, publisher=None, tracer=None):
        self.logger = logger if logger is not None else MagicMock()
        self._publisher = publisher
        self.tracer = tracer


class TestPushToGateway:
    def test_unconfigured_publisher_reports_unavailable(self):
        host = _GatewayHost()
        result = host.push_to_gateway(gateway="http://pushgateway:9091")
        assert result.success is False
        assert result.error == "Metrics publisher is not configured"
        host.logger.warning.assert_called_once()

    def test_https_gateway_class_reported(self):
        host = _GatewayHost()
        host.push_to_gateway(gateway="https://pushgateway:9091")
        _, kwargs = host.logger.warning.call_args
        assert kwargs["gateway_class"] == "https"

    def test_publisher_exception_reports_failure(self):
        publisher = MagicMock()
        publisher.push_to_gateway.side_effect = OSError("conn refused")
        host = _GatewayHost(publisher=publisher)
        result = host.push_to_gateway(gateway="http://gw", run_label="r1")
        assert result.success is False
        assert result.error == "conn refused"
        assert result.run_label == "r1"

    def test_publisher_success(self):
        publisher = MagicMock()
        publisher.push_to_gateway.return_value = True
        host = _GatewayHost(publisher=publisher)
        result = host.push_to_gateway(
            gateway="http://gw", grouping_key={"job": "j"}, metric_names=("m",)
        )
        assert result.success is True
        assert result.error is None
        host.logger.info.assert_called_once()
        publisher.push_to_gateway.assert_called_once_with(
            gateway="http://gw",
            run_label="bioetl",
            grouping_key={"job": "j"},
            metric_names=("m",),
        )

    def test_publisher_unsuccessful_result(self):
        publisher = MagicMock()
        publisher.push_to_gateway.return_value = False
        host = _GatewayHost(publisher=publisher)
        result = host.push_to_gateway(gateway="http://gw")
        assert result.success is False
        assert result.error == "Publisher returned unsuccessful result"

    def test_traced_push_records_span(self):
        publisher = MagicMock()
        publisher.push_to_gateway.return_value = True
        host = _GatewayHost(publisher=publisher, tracer=MagicMock())
        result = host.push_to_gateway(gateway="http://gw", run_label="r1")
        assert result.success is True
        host.logger.info.assert_called_once()

    def test_traced_delete_records_span(self):
        publisher = MagicMock()
        publisher.delete_from_gateway.return_value = True
        host = _GatewayHost(publisher=publisher, tracer=MagicMock())
        result = host.delete_from_gateway(gateway="http://gw", run_label="r1")
        assert result.success is True
        host.logger.info.assert_called_once()


class TestMetricsProtocolStubs:
    def test_host_protocol_bodies_execute(self):
        from bioetl.application.services.ops._metrics_service_gateway_support import (
            _MetricsGatewayHost,
            _MetricsTracingHost,
        )

        host = _GatewayHost()
        assert (
            _MetricsTracingHost._build_span_attributes(host, operation="x") is None
        )
        assert (
            _MetricsTracingHost._set_result_attributes(host, success=True) is None
        )
        assert (
            _MetricsGatewayHost._push_to_gateway_impl(
                host, gateway="g", run_label="r", labels={}, metric_names=None
            )
            is None
        )
        assert (
            _MetricsGatewayHost._delete_from_gateway_impl(
                host, gateway="g", run_label="r", labels={}
            )
            is None
        )


class TestDeleteFromGateway:
    def test_unconfigured_publisher_reports_unavailable(self):
        host = _GatewayHost()
        result = host.delete_from_gateway(gateway="http://pushgateway:9091")
        assert result.success is False
        assert result.error == "Metrics publisher is not configured"

    def test_publisher_exception_reports_failure(self):
        publisher = MagicMock()
        publisher.delete_from_gateway.side_effect = ValueError("bad gateway")
        host = _GatewayHost(publisher=publisher)
        result = host.delete_from_gateway(gateway="https://gw")
        assert result.success is False
        assert result.error == "bad gateway"
        _, kwargs = host.logger.warning.call_args
        assert kwargs["gateway_class"] == "https"

    def test_publisher_success(self):
        publisher = MagicMock()
        publisher.delete_from_gateway.return_value = True
        host = _GatewayHost(publisher=publisher)
        result = host.delete_from_gateway(
            gateway="http://gw", grouping_key={"job": "j"}
        )
        assert result.success is True
        host.logger.info.assert_called_once()

    def test_publisher_unsuccessful_result(self):
        publisher = MagicMock()
        publisher.delete_from_gateway.return_value = False
        host = _GatewayHost(publisher=publisher)
        result = host.delete_from_gateway(gateway="http://gw")
        assert result.success is False
        assert result.error == "Publisher returned unsuccessful result"


class TestMetricsTracingHelpers:
    def test_span_attributes_and_result(self):
        host = _GatewayHost()
        attributes = host._build_span_attributes(operation="push_to_gateway", extra=1)
        assert attributes["bioetl.component"] == "metrics_service"
        assert attributes["bioetl.operation"] == "push_to_gateway"
        span = MagicMock()
        _MetricsGatewayMixin._set_result_attributes(
            span, success=True, error="e", attributes={"k": "v"}
        )
        span.set_attribute.assert_any_call("bioetl.success", True)
        span.set_attribute.assert_any_call("error", True)

    def test_result_attributes_without_error(self):
        span = MagicMock()
        _MetricsGatewayMixin._set_result_attributes(span, success=False)
        span.set_attribute.assert_called_once_with("bioetl.success", False)
