"""Stream B APP: leftover config, quarantine-async, resume, and diagnostics branches."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.application.services.control_plane.forensic import (
    diagnostics_support as forensic,
)
from bioetl.application.services.control_plane.manifest.diagnostics import (
    source_refs as refs,
)
from bioetl.application.services.control_plane.manifest.inspection_service import (
    RunManifestInspectionService,
)
from bioetl.application.services.execution import _pipeline_runner_support as runner
from bioetl.application.services.ops.config_service import ConfigService
from bioetl.application.services.quality._quarantine_service_async_mixin import (
    QuarantineServiceAsyncMixin,
)
from bioetl.application.services.run_reports import query as reports
from bioetl.application.services.workflow.control_plane import (
    _execution_resume_support as resume,
)

pytestmark = pytest.mark.unit


class _AsyncHost(QuarantineServiceAsyncMixin):
    tracer = None
    logger = MagicMock()
    TRACER_NAME = "test"

    def __init__(self, *, fail: bool = False) -> None:
        self.quarantine_port = SimpleNamespace(
            inspect=self._inspect,
            get_stats=self._stats,
        )
        self._fail = fail
        self.failed: list[str] = []

    async def _inspect(self, **_k: object) -> list[dict[str, object]]:
        if self._fail:
            raise RuntimeError("inspect failed")
        return [{"error_code": "E", "payload": {}}]

    async def _stats(self, *_a: object, **_k: object) -> dict[str, object]:
        if self._fail:
            raise ValueError("stats failed")
        return {"count": 1}

    def _record_operator_metrics(self, **kwargs: object) -> None:
        self.failed.append(str(kwargs.get("operation")))

    def _trace_attributes(self, **kwargs: object) -> dict[str, object]:
        return dict(kwargs)

    def _set_trace_result(self, *_a: object, **_k: object) -> None:
        return None


def test_config_service_dq_and_yaml_type_errors() -> None:
    service = ConfigService(
        logger=MagicMock(),
        _settings_loader=lambda: SimpleNamespace(),  # type: ignore[arg-type]
        _pipeline_config_loader=lambda _name: object(),  # type: ignore[arg-type]
        _domain_config_mapper=lambda _cfg: SimpleNamespace(),  # type: ignore[arg-type]
        _registry_accessor=lambda: SimpleNamespace(),  # type: ignore[arg-type]
    )
    with pytest.raises(ValueError, match="not configured"):
        service._require_dq_service()
    with pytest.raises(TypeError, match="model_dump"):
        service.get_pipeline_yaml_config("chembl_activity")
    dq = SimpleNamespace(
        get_dq_config=lambda _n: {"ok": True},
        validate_dq_config=lambda _n, _c: True,
        get_effective_config_artifact=lambda _n, _o: {"artifact": True},
        check_config_compatibility=lambda _a, _b: False,
    )
    service._dq_service = dq  # type: ignore[assignment]
    assert service.get_dq_config("p") == {"ok": True}
    assert service.validate_dq_config("p", {}) is True
    assert service.get_effective_config_artifact("p") == {"artifact": True}
    assert service.check_config_compatibility({}, {}) is False


@pytest.mark.asyncio
async def test_quarantine_async_untraced_and_operator_errors() -> None:
    host = _AsyncHost()
    records = await host.inspect("p")
    assert records[0].error_code == "E"
    assert await host.get_stats("p") == {"count": 1}

    failing = _AsyncHost(fail=True)
    with pytest.raises(RuntimeError, match="inspect failed"):
        await failing.inspect("p")
    with pytest.raises(ValueError, match="stats failed"):
        await failing.get_stats("p")
    assert failing.failed == ["inspect", "stats"]


def test_pipeline_runner_duration_exception() -> None:
    class _Bad:
        @property
        def duration_seconds(self) -> float:
            raise RuntimeError("missing")

    assert runner._result_duration_seconds(_Bad()) is None  # type: ignore[arg-type]


def test_resume_state_missing_and_damaged_guards() -> None:
    port = SimpleNamespace(
        get_by_run_id=lambda _rid: None,
        get_by_manifest_id=lambda _mid: None,
        get_latest=lambda _name: None,
    )
    with pytest.raises(RuntimeError, match="resume-last"):
        resume.load_resume_state(
            workflow_state_port=port,  # type: ignore[arg-type]
            workflow_name="wf",
            resume_manifest_id=None,
            resume_run_id=None,
        )


def test_resume_validators_reject_inconsistent_state() -> None:
    identity = SimpleNamespace(manifest_id=" ", execution_fingerprint="fp")
    with pytest.raises(RuntimeError, match="identity fields"):
        resume._validate_identity_fields(identity)  # type: ignore[arg-type]
    refs_state = SimpleNamespace(
        selected_step_ids=("missing",),
        completed_transform_fingerprints={},
    )
    with pytest.raises(RuntimeError, match="inconsistent"):
        resume._validate_step_references(refs_state, ("s1",))  # type: ignore[arg-type]
    lifecycle = SimpleNamespace(
        status="success",
        steps=(SimpleNamespace(status="weird"),),
    )
    with pytest.raises(RuntimeError, match="unknown lifecycle"):
        resume._validate_lifecycle_status(lifecycle)  # type: ignore[arg-type]
    with pytest.raises(RuntimeError, match="already completed"):
        resume._validate_completion_status(
            SimpleNamespace(status="success"),  # type: ignore[arg-type]
            "wf",
        )


def test_forensic_and_source_ref_helpers() -> None:
    factory = forensic.inspection_service_factory_from_ports(
        manifest_port=MagicMock(),
        ledger_port=None,
        provided_factory=lambda: "ready",  # type: ignore[arg-type,return-value]
    )
    assert factory() == "ready"
    assert forensic.coerce_int(True) == 1
    assert forensic.coerce_int("nope") == 0
    assert forensic.dict_or_empty("x") == {}
    diff = SimpleNamespace(classification="ok", occurrence_only=True)
    assert (
        forensic.resolve_forensic_verdict(
            manifest_diff=diff,  # type: ignore[arg-type]
            forensic_diff={"checkpoint_anchors": {"compatible": False}},
        )
        == "checkpoint_incompatible"
    )
    assert (
        forensic.resolve_forensic_verdict(
            manifest_diff=diff,  # type: ignore[arg-type]
            forensic_diff={},
        )
        == "occurrence_only_replay"
    )
    manifest = SimpleNamespace(
        source_refs=("a",), provider="p", entity="e", pipeline_name="p_e"
    )
    assert (
        refs._build_effective_source_refs(manifest=manifest, input_snapshots=["skip"])  # type: ignore[arg-type]
        == ("a",)
    )
    summary = refs._attach_rich_composite_replay_support({"keep": True}, ())
    assert summary == {"keep": True}


def test_inspection_service_claim_and_artifact_gaps() -> None:
    service = RunManifestInspectionService.__new__(RunManifestInspectionService)
    service.historical_replay_universe_report_loader = None
    diagnostics: dict[str, object] = {}
    service._attach_historical_replay_universe_claim(diagnostics)
    assert diagnostics == {}
    service.historical_replay_universe_report_loader = SimpleNamespace(
        load_latest_report=lambda: "nope"
    )
    service._attach_historical_replay_universe_claim(diagnostics)
    assert diagnostics == {}
    service.show = lambda _identifier: SimpleNamespace(diagnostics={})  # type: ignore[method-assign]
    assert service.resolve_produced_artifacts("m") == ()
    service.show = lambda _identifier: SimpleNamespace(  # type: ignore[method-assign]
        diagnostics={"produced_artifact_trace": {"artifacts": "bad"}}
    )
    assert service.resolve_produced_artifacts("m") == ()
    service.manifest_port = SimpleNamespace(  # type: ignore[attr-defined]
        get=lambda _i: (_ for _ in ()).throw(ValueError("corrupt")),
        get_by_run_id=lambda _i: None,
    )
    with pytest.raises(Exception, match="corrupt|not found"):
        service._resolve_manifest("m")


def test_report_query_int_and_remove_directories(tmp_path: Path) -> None:
    assert reports._int(None) == 0
    assert reports._int(object()) == 0
    assert reports._int("nope") == 0
    store = SimpleNamespace(remove_tree=MagicMock())
    first = SimpleNamespace(json_path=tmp_path / "a" / "report.json")
    second = SimpleNamespace(json_path=tmp_path / "a" / "other.json")
    removed = reports._remove_report_directories(
        [first, second],  # type: ignore[arg-type]
        dry_run=True,
        store=store,  # type: ignore[arg-type]
    )
    assert len(removed) == 1
    store.remove_tree.assert_not_called()
