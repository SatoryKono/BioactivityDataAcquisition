"""Unit tests for runtime runner builder leaf module."""

from __future__ import annotations

import json
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from bioetl.composition.runtime_builders import _run_manifest_builder_policy
from bioetl.composition.observability import ObservabilityBundle
from bioetl.composition.runtime_builders import inputs_resolver
from bioetl.composition.runtime_builders import runner_builder
from bioetl.composition.runtime_builders import runner_control_plane_assembly
from bioetl.composition.runtime_builders._runner_builder_orchestration import (
    attach_runner_control_plane_collaborators,
)
from bioetl.composition.services import versioning
from bioetl.domain.ports import PipelineCreateRunnerRequest
from bioetl.domain.ports.noop import NoOpAudit, NoOpTracing

SILVER_OUTPUT_PATH = "test-output/silver/chembl/activity"
SILVER_METADATA_PATH = "test-output/silver/chembl/activity/_metadata.yaml"


class _FakeRunner:
    def __init__(self) -> None:
        self.attached_run_ledger_service: object | None = None
        self.services = SimpleNamespace(
            metadata_writer=_RecorderAwareMetadataWriter(),
            storage=None,
        )

    def attach_run_ledger_service(self, service: object) -> None:
        self.attached_run_ledger_service = service

    def __eq__(self, other: object) -> bool:
        return other == "runner-instance" or other is self


class _FakeFactory:
    def __init__(self) -> None:
        self.request: PipelineCreateRunnerRequest | None = None
        self.kwargs: dict[str, object] | None = None
        self.runner = _FakeRunner()

    def create_runner(self, request: PipelineCreateRunnerRequest) -> object:
        self.request = request
        control_plane = request.control_plane
        self.kwargs = {
            "run_id": request.run_id,
            "runtime": request.runtime,
            "started_at": request.started_at,
            "settings": request.settings,
            "observability": request.observability,
            "manifest_id": control_plane.manifest_id,
            "execution_fingerprint": control_plane.execution_fingerprint,
            "config_hash": control_plane.config_hash,
            "resolved_config_hash": control_plane.resolved_config_hash,
            "effective_config_hash": control_plane.effective_config_hash,
            "dq_contract_compatibility_hash": (
                control_plane.dq_contract_compatibility_hash
            ),
            "effective_config_artifact_id": (
                control_plane.effective_config_artifact_id
            ),
            "filter_config": request.filter_config,
            "config": request.config,
            "cached_bronze": request.cached_bronze,
        }
        return self.runner


class _RecorderAwareMetadataWriter:
    def __init__(self) -> None:
        self.recorder = None

    def attach_artifact_recorder(self, recorder) -> None:
        self.recorder = recorder


class _FakeRegistry:
    def __init__(self, factory: _FakeFactory) -> None:
        self._factory = factory

    def get(self, pipeline_name: str) -> SimpleNamespace:
        return SimpleNamespace(factory=self._factory, pipeline_name=pipeline_name)


def _namespace_observability(logger: object | None = None) -> SimpleNamespace:
    effective_logger = (
        logger if logger is not None else SimpleNamespace(info=lambda *_, **__: None)
    )
    return SimpleNamespace(
        logger=effective_logger,
        metrics=MagicMock(),
        tracer=NoOpTracing(),
        audit=NoOpAudit(),
        dq_monitor=None,
    )


def _runtime_config_stub() -> dict[str, object]:
    return {"runtime_profile": "stub"}


def _build_factory_registry() -> tuple[_FakeFactory, _FakeRegistry]:
    fake_factory = _FakeFactory()
    return fake_factory, _FakeRegistry(factory=fake_factory)


def _clean_provenance_context_if_unpatched():
    if (
        _run_manifest_builder_policy.get_code_revision_provenance
        is versioning.get_code_revision_provenance
    ):
        return patch(
            "bioetl.composition.runtime_builders._run_manifest_builder_policy.get_code_revision_provenance",
            return_value=versioning.CodeRevisionProvenance(
                git_commit="a" * 40,
                source_revision_state="clean",
                dependency_lock_hash="sha256:test-lock",
            ),
        )
    return nullcontext()


def _build_context(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "pipeline_name": "chembl_activity",
        "run_id": uuid4(),
        "log_level": "INFO",
        "vacuum": None,
        "run_type": "incremental",
        "resume": False,
        "limit": None,
        "query": None,
        "dry_run": False,
        "skip_gold": False,
        "start_offset": None,
        "input_filter": SimpleNamespace(enabled=False),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _build_settings(
    *,
    data_dir: str | None = "/tmp/bioetl-test-data",
    heartbeat_interval: int = 30,
    health_check_mode: str | None = None,
    control_plane: object | None = None,
    test_mode: bool = False,
) -> SimpleNamespace:
    pipeline_values: dict[str, object] = {
        "heartbeat_interval": heartbeat_interval,
    }
    if health_check_mode is not None:
        pipeline_values["health_check_mode"] = health_check_mode
    pipeline_values["control_plane"] = (
        control_plane
        if control_plane is not None
        else SimpleNamespace(
            required_persistence_profile="degraded_observable",
            checkpoint_compatibility_policy="hard_fail",
            run_manifest_enabled=True,
            run_ledger_enabled=True,
        )
    )

    settings_values: dict[str, object] = {
        "pipeline": SimpleNamespace(**pipeline_values),
        "test_mode": test_mode,
        "bronze_path": data_dir if data_dir is not None else "/tmp/bioetl-test-data",
    }
    if data_dir is not None:
        settings_values["data_dir"] = data_dir
    return SimpleNamespace(**settings_values)


def _build_pipeline_config(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "provider": "chembl",
        "entity_type": "activity",
        "version": "2.0.0",
        "maintenance": None,
        "input_filter": SimpleNamespace(),
        "business_primary_keys": ["activity_id"],
        "technical_primary_key": "entity_id",
        "sink": {
            "bronze": SimpleNamespace(enabled=True, save_metadata=True),
            "silver": SimpleNamespace(enabled=True, save_metadata=True),
            "gold": SimpleNamespace(enabled=True, save_metadata=True),
        },
    }
    sink_override = overrides.pop("sink", None)
    values.update(overrides)
    if sink_override is not None:
        base_sink = values["sink"]
        if isinstance(base_sink, dict) and isinstance(sink_override, dict):
            values["sink"] = {**base_sink, **sink_override}
        else:
            values["sink"] = sink_override
    return SimpleNamespace(**values)


def _default_build_observability_bundle_fn(**_: object) -> SimpleNamespace:
    return _namespace_observability(SimpleNamespace(info=lambda *_, **__: None))


def _ensure_default_cached_bronze_fixture(
    *,
    settings: object,
    pipeline_config: object,
) -> SimpleNamespace:
    bronze_base = Path(
        str(
            getattr(
                settings,
                "bronze_path",
                getattr(settings, "data_dir", "/tmp/bioetl-test-data"),
            )
        )
    )
    provider = str(getattr(pipeline_config, "provider", "chembl"))
    entity = str(getattr(pipeline_config, "entity_type", "activity"))
    bronze_root = bronze_base / provider / entity
    bronze_date = "2026-01-01"
    bronze_day = bronze_root / bronze_date
    bronze_day.mkdir(parents=True, exist_ok=True)
    batch_file = bronze_day / "batch_2026-01-01_default.jsonl.zst"
    if not batch_file.exists():
        batch_file.write_bytes(b"default-snapshot-bytes")
    return SimpleNamespace(
        enabled=True,
        bronze_path=str(bronze_root),
        bronze_date=bronze_date,
    )


def _call_build_pipeline_runner(
    context: SimpleNamespace | None = None,
    *,
    registry: _FakeRegistry | None = None,
    create_registry_fn: object | None = None,
    ensure_providers_loaded_fn: object | None = None,
    register_all_pipelines_fn: object | None = None,
    settings: object | None = None,
    pipeline_config: object | None = None,
    build_observability_bundle_fn: object | None = None,
    assemble_vacuum_settings_fn: object | None = None,
    assemble_runtime_config_fn: object | None = None,
    assemble_filter_config_fn: object | None = None,
    assemble_cached_bronze_context_fn: object | None = None,
) -> object:
    resolved_settings = settings if settings is not None else _build_settings()
    resolved_pipeline_config = (
        pipeline_config if pipeline_config is not None else _build_pipeline_config()
    )
    kwargs: dict[str, object] = {
        "ensure_providers_loaded_fn": ensure_providers_loaded_fn
        if ensure_providers_loaded_fn is not None
        else (lambda: None),
        "register_all_pipelines_fn": register_all_pipelines_fn
        if register_all_pipelines_fn is not None
        else (lambda registry=None: None),
        "get_settings_fn": lambda: resolved_settings,
        "load_pipeline_config_fn": lambda _: resolved_pipeline_config,
        "build_observability_bundle_fn": build_observability_bundle_fn
        if build_observability_bundle_fn is not None
        else _default_build_observability_bundle_fn,
        "assemble_vacuum_settings_fn": assemble_vacuum_settings_fn
        if assemble_vacuum_settings_fn is not None
        else (lambda **_: None),
        "assemble_runtime_config_fn": assemble_runtime_config_fn
        if assemble_runtime_config_fn is not None
        else (lambda **_: _runtime_config_stub()),
        "assemble_filter_config_fn": assemble_filter_config_fn
        if assemble_filter_config_fn is not None
        else (lambda **_: None),
        "assemble_cached_bronze_context_fn": assemble_cached_bronze_context_fn
        if assemble_cached_bronze_context_fn is not None
        else (
            lambda _: _ensure_default_cached_bronze_fixture(
                settings=resolved_settings,
                pipeline_config=resolved_pipeline_config,
            )
        ),
    }
    if registry is not None:
        kwargs["registry"] = registry
    if create_registry_fn is not None:
        kwargs["create_registry_fn"] = create_registry_fn
    with _clean_provenance_context_if_unpatched():
        return runner_builder.build_pipeline_runner(
            context if context is not None else _build_context(),
            **kwargs,
        )




__all__ = [
    name
    for name in globals()
    if name
    not in {
        "__builtins__",
        "__cached__",
        "__doc__",
        "__file__",
        "__loader__",
        "__name__",
        "__package__",
        "__spec__",
    }
]
