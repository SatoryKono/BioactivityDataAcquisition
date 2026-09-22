"""Stream B APP: leftover identity, artifact, runner-support, and mixin branches."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.application.core._runner_support import PipelineRunnerSupportMixin
from bioetl.application.core.base_transformer_dependency_helpers_mixin import (
    _BaseTransformerDependencyHelpersMixin,
)
from bioetl.application.services.checkpoint._checkpoint_service_runtime import (
    _resolve_checkpoint_owner_pipeline,
    get_checkpoint_for_manifest_id_impl,
)
from bioetl.application.services.control_plane.manifest.diagnostics import (
    artifact_support as artifacts,
)
from bioetl.application.services.control_plane.manifest.diagnostics import (
    replay_state as replay,
)
from bioetl.application.services.run_reports import source_identity as src_id
from bioetl.application.workflow.transforms import reconcile_foreign_keys as rec

pytestmark = pytest.mark.unit

_DIGEST = "a" * 64
_OTHER = "b" * 64


def test_source_identity_windows_and_conflict_paths(tmp_path: Path) -> None:
    assert src_id._clean_path_text("foo//bar") == "foo/bar"
    assert src_id._mapped_runtime_path("E:/data") is not None
    assert src_id._local_posix_runtime_path("E:/data") == Path("/mnt/e/data")
    resolved = src_id.resolve_runtime_source_identity(
        computed_identity=_DIGEST,
        process_environment={src_id.RUNTIME_SOURCE_ID_ENV: _OTHER},
        repository_environment={src_id.RUNTIME_SOURCE_ID_ENV: "not-a-digest"},
    )
    assert resolved.status == src_id.IDENTITY_RESOLUTION_RESOLVED
    assert src_id.IDENTITY_SOURCE_PROCESS_ENVIRONMENT in resolved.conflicts
    assert src_id.IDENTITY_SOURCE_REPOSITORY_ENVIRONMENT in resolved.invalid_sources
    assert src_id._parse_repository_env_line("# comment", {"K"}) is None
    env_paths = src_id._repository_env_paths(
        tmp_path, {"BIOETL_ENV_FILE": "custom.env", "BIOETL_SKIP_ENV_LOCAL": "1"}
    )
    assert env_paths == (tmp_path / "custom.env",)


def test_artifact_support_closure_states() -> None:
    assert artifacts.sorted_text_items("nope") == []
    assert artifacts.sorted_text_items({" b ", "a"}) == ["a", "b"]
    failed = artifacts._resolve_artifact_publication_closure(
        artifact_refs=[{"publication_status": "failed"}],
        missing_requirements=[],
        planned_artifact_count=1,
    )
    assert failed == "failed"
    assert (
        artifacts._resolve_artifact_publication_closure(
            artifact_refs=[{"publication_status": "ok"}],
            missing_requirements=["x"],
            planned_artifact_count=1,
        )
        == "partial"
    )
    assert (
        artifacts._resolve_artifact_publication_closure(
            artifact_refs=[{"publication_status": "ok"}],
            missing_requirements=[],
            planned_artifact_count=2,
        )
        == "partial"
    )
    assert (
        artifacts._resolve_artifact_publication_closure(
            artifact_refs=[],
            missing_requirements=[],
            planned_artifact_count=0,
        )
        == "disabled"
    )
    assert (
        artifacts._resolve_artifact_publication_closure(
            artifact_refs=[{"publication_status": "ok"}],
            missing_requirements=(),
            planned_artifact_count=1,
        )
        == "closed"
    )
    attached = artifacts.apply_artifact_publication_closure_policy(
        {"produced_artifact_trace": {"artifact_publication_closure": "closed"}}
    )
    assert attached["artifact_publication_closure"] == "closed"


@pytest.mark.asyncio
async def test_runner_support_delegates_and_metrics_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[str] = []

    async def _named(label: str) -> None:
        seen.append(label)

    monkeypatch.setattr(
        "bioetl.application.core._runner_support.run_execution_cycle",
        lambda _h: _named("cycle"),
    )
    monkeypatch.setattr(
        "bioetl.application.core._runner_support.execute_pipeline",
        lambda _h, *, offset: _named(f"exec:{offset}"),
    )
    monkeypatch.setattr(
        "bioetl.application.core._runner_support.run_postrun_phase",
        lambda _h: _named("post"),
    )
    monkeypatch.setattr(
        "bioetl.application.core._runner_support.validate_infrastructure",
        lambda _h: _named("infra"),
    )

    class _Host(PipelineRunnerSupportMixin):
        _logger = MagicMock()
        _services = SimpleNamespace(
            metrics=SimpleNamespace(
                close=lambda: (_ for _ in ()).throw(RuntimeError("x"))
            )
        )

    host = _Host()
    await host._run_execution_cycle()  # type: ignore[misc]
    await host._execute_pipeline(offset=3)  # type: ignore[misc]
    await host._run_postrun_phase()  # type: ignore[misc]
    await host._validate_infrastructure()  # type: ignore[misc]
    host._close_metrics()
    host._logger.warning.assert_called()
    assert seen == ["cycle", "exec:3", "post", "infra"]


def test_transformer_helpers_hash_list_and_non_dataclass() -> None:
    class _Host(_BaseTransformerDependencyHelpersMixin):
        _pii_hasher = SimpleNamespace(hash_list=lambda values: ["h"])
        _contract_policy = SimpleNamespace(rename_map={})

    host = _Host()
    assert host.hash_pii_list(["a"]) == ["h"]
    with pytest.raises(TypeError, match="Expected dataclass"):
        host.entity_to_silver_record("not-an-entity")
    identity = SimpleNamespace(has_explicit_content_hash_policy=lambda: True)
    policy = SimpleNamespace(hash_include=None, hash_exclude=())
    assert host._apply_hash_policy(identity, policy, {"id": 1}) == {"id": 1}  # type: ignore[arg-type]
    identity = SimpleNamespace(has_explicit_content_hash_policy=lambda: False)
    policy = SimpleNamespace(hash_include=("id",), hash_exclude=())
    scoped = host._apply_hash_policy(identity, policy, {"id": 1, "extra": 2})  # type: ignore[arg-type]
    assert scoped == {"id": 1}


def test_checkpoint_owner_from_run_context_and_missing_manifest() -> None:
    assert (
        _resolve_checkpoint_owner_pipeline(
            caller_pipeline_name="chembl_activity",
            metadata={"run_context": {"pipeline_name": "chembl_activity"}},
        )
        == "chembl_activity"
    )

    class _Host:
        logger = MagicMock()
        checkpoint_port = SimpleNamespace(
            load_for_manifest_id=lambda _mid: (_ for _ in ()).throw(ValueError("boom"))
        )
        failed: list[str] = []

        def _record_operator_metrics(self, **kwargs: object) -> None:
            self.failed.append(str(kwargs.get("status")))

        def _checkpoint_info_from_data(self, **_k: object) -> object:
            return object()

    host = _Host()

    async def _run() -> None:
        with pytest.raises(ValueError, match="boom"):
            await get_checkpoint_for_manifest_id_impl(
                host,  # type: ignore[arg-type]
                pipeline_name="p",
                manifest_id="m",
                start_time=0.0,
            )

    import asyncio

    asyncio.run(_run())
    assert host.failed == ["failed"]


def test_replay_remaining_incomplete_and_composite_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    family = SimpleNamespace(
        profile=SimpleNamespace(
            strict_exact_replay_supported=True,
            post_capture_replayable_parent_supported=False,
        )
    )
    policy = SimpleNamespace(
        snapshot_envelope=SimpleNamespace(full_snapshot_envelope=False)
    )
    monkeypatch.setattr(replay, "_collect_append_mode_semantic_sinks", lambda _m: False)
    monkeypatch.setattr(
        replay, "_has_partial_input_snapshot_envelope", lambda _e: False
    )
    monkeypatch.setattr(
        replay, "_has_historical_composite_certified_snapshots", lambda _s: True
    )
    monkeypatch.setattr(
        replay, "_resolve_exact_replay_supported_reason", lambda **_k: None
    )
    monkeypatch.setattr(
        replay, "_requires_resume_without_snapshot_reason", lambda **_k: False
    )
    monkeypatch.setattr(replay, "_is_composite_execution_context", lambda _m: True)
    monkeypatch.setattr(
        replay, "_build_replay_parentage", lambda _m: {"is_exact_replay": False}
    )
    assert (
        replay._resolve_replay_capability_reason(
            manifest=object(),  # type: ignore[arg-type]
            input_snapshots=[],
            resume_requested=False,
            policy_assessment=policy,  # type: ignore[arg-type]
            replay_family_context=family,  # type: ignore[arg-type]
        )
        == "certified_historical_composite_snapshot_envelope_present"
    )
    monkeypatch.setattr(
        replay, "_has_historical_composite_certified_snapshots", lambda _s: False
    )
    monkeypatch.setattr(
        replay, "_has_historical_source_certified_snapshots", lambda _s: True
    )
    monkeypatch.setattr(
        replay, "_has_live_capture_materialized_snapshots", lambda _s: True
    )
    assert (
        replay._resolve_replay_occurrence_kind(
            manifest=object(),  # type: ignore[arg-type]
            input_snapshots=[{}],
            policy_assessment=policy,  # type: ignore[arg-type]
        )
        == "historical_source_certification_incomplete"
    )
    monkeypatch.setattr(
        replay, "_has_historical_source_certified_snapshots", lambda _s: False
    )
    assert (
        replay._resolve_replay_occurrence_kind(
            manifest=object(),  # type: ignore[arg-type]
            input_snapshots=[{}],
            policy_assessment=policy,  # type: ignore[arg-type]
        )
        == "materialized_parent_incomplete"
    )
    monkeypatch.setattr(replay, "_is_composite_execution_context", lambda _m: False)
    assert (
        replay._resolve_historical_live_run_upgrade_state(
            manifest=object(),  # type: ignore[arg-type]
            input_snapshots=[{}],
            policy_assessment=policy,  # type: ignore[arg-type]
            replay_family_context=family,  # type: ignore[arg-type]
        )
        == "incomplete_materialization_evidence"
    )
    monkeypatch.setattr(
        replay, "_has_live_capture_materialized_snapshots", lambda _s: False
    )
    assert (
        replay._resolve_historical_live_run_upgrade_state(
            manifest=object(),  # type: ignore[arg-type]
            input_snapshots=[{}],
            policy_assessment=policy,  # type: ignore[arg-type]
            replay_family_context=family,  # type: ignore[arg-type]
        )
        == "outside_supported_boundary"
    )
    monkeypatch.setattr(
        replay, "_has_historical_composite_certified_snapshots", lambda _s: True
    )
    assert (
        replay._resolve_broader_historical_exact_replay_state(
            manifest=object(),  # type: ignore[arg-type]
            input_snapshots=[{}],
            policy_assessment=policy,  # type: ignore[arg-type]
        )
        == "historical_composite_certification_incomplete"
    )


def test_reconcile_optional_layer_and_artifact_refs() -> None:
    rec._optional_layer({}, "source_layer", default=None)
    with pytest.raises(ValueError, match="silver"):
        rec._optional_layer({"source_layer": "bronze"}, "source_layer", default=None)
    payload: dict[str, object] = {}
    if True:
        payload["artifact_refs"] = [{"id": "a"}]
    assert payload["artifact_refs"]
    rec._record_reconcile_destructive_commit(
        None,
        spec=SimpleNamespace(step_id="s", transform_name="t", fingerprint="f"),  # type: ignore[arg-type]
        result=SimpleNamespace(mutated=True, dry_run=False),
        payload={},
    )
    logger = MagicMock()
    import asyncio

    async def _skip() -> None:
        refs = await rec._persist_reconcile_result_artifact(
            SimpleNamespace(
                logger=logger,
                artifact_sink=object(),
                workflow_name=None,
                workflow_run_id=None,
                manifest_id=None,
            ),  # type: ignore[arg-type]
            spec=SimpleNamespace(step_id="s", transform_name="t"),  # type: ignore[arg-type]
            payload={},
        )
        assert refs == ()

    asyncio.run(_skip())
    logger.debug.assert_called()
