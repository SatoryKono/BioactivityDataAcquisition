"""Behavioral coverage for remaining small composition seams in #10469."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from bioetl.composition.bootstrap.runtime import _composite_control_plane_support
from bioetl.composition.bootstrap.runtime import tracing_bootstrap
from bioetl.composition.factories.pipeline import assembler
from bioetl.composition.factories.pipeline_support import checkpoint_metadata_resolution
from bioetl.composition.factories.storage import _layer_writers
from bioetl.composition import observability_backend, observability_runtime
from bioetl.composition.providers import _config_helpers
from bioetl.composition.runtime_builders import _config_access_loaders
from bioetl.composition.runtime_builders._run_manifest_snapshot_resolution import (
    resolve_replay_parentage_mapping_value,
)
from bioetl.composition.runtime_builders.runner_input_assembly import (
    _bind_resolved_cached_bronze_context,
)


pytestmark = pytest.mark.unit


def test_composite_replay_rejects_strict_context_gap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        _composite_control_plane_support,
        "assess_reproducibility_policy",
        lambda **_kwargs: SimpleNamespace(
            required_profile_satisfied=False,
            blocking_gaps=("strict_replay_execution_context_support",),
        ),
    )

    with pytest.raises(RuntimeError, match="outside the strict exact-replay"):
        _composite_control_plane_support.resolve_composite_replay_capability(
            source_refs=(),
            required_persistence_profile="replay_ready",
            resume_requested=False,
        )


def test_default_tracer_factory_delegates_service_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tracer = object()
    factory = Mock(return_value=tracer)
    monkeypatch.setattr(
        tracing_bootstrap.observability_adapters, "OpenTelemetryTracer", factory
    )

    assert tracing_bootstrap._default_tracer_factory("coverage-test") is tracer
    factory.assert_called_once_with(service_name="coverage-test")


def test_transformer_compatibility_seam_delegates_all_dependencies() -> None:
    created = object()
    factory = SimpleNamespace(create_transformer=Mock(return_value=created))
    dependencies = SimpleNamespace()

    result = assembler.create_transformer(factory, dependencies=dependencies)

    assert result is created
    assert factory.create_transformer.call_args.args[-1] is dependencies


def test_checkpoint_snapshot_resolution_requires_provider_and_entity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pipeline = SimpleNamespace(
        runtime=SimpleNamespace(cached_bronze=SimpleNamespace(enabled=True)),
        config=SimpleNamespace(provider="demo", entity_type=None),
    )
    monkeypatch.setattr(
        checkpoint_metadata_resolution,
        "_resolve_run_context_metadata",
        lambda _pipeline: {"manifest_id": "manifest-1"},
    )
    monkeypatch.setattr(
        checkpoint_metadata_resolution,
        "resolve_manifest_input_snapshot_refs",
        lambda **_kwargs: (),
    )

    assert checkpoint_metadata_resolution._resolve_input_snapshot_refs(pipeline) == ()


def test_contract_rollout_policy_loader_converts_pipeline_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rollout = object()
    policy = SimpleNamespace(to_contract_rollout_policy=Mock(return_value=rollout))
    loader = Mock(return_value=policy)
    monkeypatch.setattr(_layer_writers, "load_pipeline_contract_policy", loader)
    config = SimpleNamespace(provider="demo", entity_type="item")

    assert _layer_writers.load_contract_rollout_policy(config) is rollout
    loader.assert_called_once_with("demo", "item")


def test_observability_backend_delegates_detached_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = object()
    start = Mock(return_value=process)
    popen_factory = Mock()
    monkeypatch.setattr(
        observability_backend, "_infra_start_detached_ops_http_backend", start
    )

    result = observability_backend.start_detached_ops_http_backend(
        bind_host="127.0.0.1",
        port=8123,
        current_env={"BIOETL_ENV": "test"},
        popen_factory=popen_factory,
    )

    assert result is process
    assert start.call_args.kwargs["port"] == 8123
    assert start.call_args.kwargs["popen_factory"] is popen_factory


def test_workflow_metrics_bind_context_before_publication(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bound_logger = Mock()
    logger = Mock()
    logger.bind.return_value = bound_logger
    publisher = Mock()
    publisher.push_to_gateway.return_value = SimpleNamespace(success=True)
    monkeypatch.setattr(
        observability_runtime._config_access,
        "get_settings",
        lambda: SimpleNamespace(pushgateway_url="http://push.test"),
    )
    monkeypatch.setattr(
        observability_runtime,
        "bootstrap_metrics_service",
        lambda **_kwargs: publisher,
    )

    assert observability_runtime.push_metrics_to_gateway(
        pipeline_name="chembl_assay",
        run_type="incremental",
        metric_names=("records",),
        workflow_name="chembl-baseline",
        pipeline_names=("chembl_assay",),
        logger=logger,
    )
    logger.bind.assert_called_once_with(
        workflow_name="chembl-baseline",
        pipeline_names=("chembl_assay",),
        run_type="incremental",
    )


def test_fallback_wiring_is_optional_without_source_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_source = SimpleNamespace(provider_name="demo")
    monkeypatch.setattr(_config_helpers, "_get_source_config", lambda _provider: None)

    assert _config_helpers._wire_composable_fallback(data_source) is None


def test_bound_dq_loader_uses_resolved_config_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    load = Mock(return_value={"rules": []})
    monkeypatch.setattr(
        _config_access_loaders, "resolve_configs_root", lambda _root: tmp_path
    )
    monkeypatch.setattr(_config_access_loaders, "_load_dq_config_for_pipeline", load)

    bound = _config_access_loaders.create_dq_config_loader(tmp_path / "input")

    assert bound("chembl_assay") == {"rules": []}
    load.assert_called_once_with("chembl_assay", configs_root=tmp_path)


def test_replay_parentage_searches_nested_control_plane_mapping() -> None:
    assert (
        resolve_replay_parentage_mapping_value(
            {"pipeline": {"control_plane": {"replay_of_run_id": "parent-run"}}},
            "replay_of_run_id",
        )
        == "parent-run"
    )


def test_cached_bronze_context_updates_dataclass_context() -> None:
    @dataclass(frozen=True)
    class Context:
        cached_bronze: object

    original = object()
    resolved = object()
    context = Context(cached_bronze=original)
    inputs = SimpleNamespace(cached_bronze=resolved)

    updated = _bind_resolved_cached_bronze_context(context, inputs)

    assert isinstance(updated, Context)
    assert updated.cached_bronze is resolved
