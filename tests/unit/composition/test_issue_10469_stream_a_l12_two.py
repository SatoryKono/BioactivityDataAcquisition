"""Stream A leftover L12 composition residuals for #10469 / #10516."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from bioetl.composition.bootstrap.runtime import observability_assembly as observability
from bioetl.composition.bootstrap.runtime import pipeline as pipeline_runtime
from bioetl.composition.factories.batch_id_generator import UuidBatchIdGenerator
from bioetl.composition.factories.pipeline import _runner_assembly_support as assembly
from bioetl.composition.factories.pipeline import runner_constructor as constructor
from bioetl.composition.factories.pipeline.runner_constructor import (
    RunnerAssemblyParts,
    RunnerConstructorPayload,
)
from bioetl.composition.factories.pipeline_support.checkpoint_policy_helpers import (
    DEFAULT_REQUIRED_PERSISTENCE_PROFILE,
    _resolve_required_persistence_profile,
)
from bioetl.composition.factories.services import bundle as bundle_mod
from bioetl.composition.occurrence_identity import create_runtime_occurrence_batch_id
from bioetl.composition.runtime_builders import _config_access_loaders as loaders
from bioetl.composition.runtime_builders.cached_bronze_snapshot_support import (
    build_cached_bronze_input_snapshot_refs,
)
from bioetl.composition.runtime_builders.ledger_collaborator import (
    _canonical_lineage_fragment_id,
)


pytestmark = pytest.mark.unit


def test_default_audit_bootstrapper_delegates_to_create_audit_port(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = object()
    monkeypatch.setattr(observability, "create_audit_port", lambda **_kwargs: sentinel)
    result = observability.default_audit_bootstrapper(
        MagicMock(), MagicMock(), MagicMock(), MagicMock()
    )
    assert result is sentinel


def test_fail_fast_cached_bronze_requires_snapshot_refs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        pipeline_runtime,
        "require_cached_bronze_input_snapshot_refs",
        lambda **kwargs: captured.update(kwargs),
    )
    context = SimpleNamespace(
        cached_bronze=SimpleNamespace(
            enabled=True,
            bronze_path="/tmp/bronze",
            bronze_date="2026-01-01",
        )
    )
    pipeline_runtime._fail_fast_empty_explicit_cached_bronze(context)
    assert captured["bronze_root"] == Path("/tmp/bronze")
    assert captured["bronze_date"] == "2026-01-01"


def test_uuid_batch_id_generator_creates_batch_id() -> None:
    batch_id = UuidBatchIdGenerator().create()
    assert UUID(str(batch_id))


def test_build_batch_executor_reads_dq_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        assembly,
        "extract_dq_output_paths",
        lambda _cfg: SimpleNamespace(
            bronze_path=None,
            silver_path=None,
            gold_path=None,
            flat_structure=False,
        ),
    )
    monkeypatch.setattr(
        assembly, "extract_pipeline_callbacks", lambda _pipeline: MagicMock()
    )
    monkeypatch.setattr(
        assembly.ServicesBuilder,
        "create_batch_executor_from_pipeline",
        staticmethod(lambda _request: "executor"),
    )
    context = MagicMock()
    result = assembly.build_batch_executor(
        context,
        checkpoint_manager=MagicMock(),
        lock_runtime_service=MagicMock(),
        observer=MagicMock(),
    )
    assert result == "executor"


def test_create_pipeline_runner_from_payload_delegates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(constructor, "create_pipeline_runner", lambda **_k: "runner")
    payload = RunnerConstructorPayload(
        pipeline=MagicMock(),
        observability=MagicMock(),
        parts=RunnerAssemblyParts(
            checkpoint_manager=MagicMock(),
            lifecycle_service=MagicMock(),
            lock_runtime_service=MagicMock(),
            preflight_service=MagicMock(),
            postrun_service=MagicMock(),
            observer=MagicMock(),
            batch_executor=MagicMock(),
        ),
    )
    assert constructor.create_pipeline_runner_from_payload(payload) == "runner"


def test_required_persistence_profile_falls_back_to_default() -> None:
    pipeline = SimpleNamespace(settings=None)
    assert (
        _resolve_required_persistence_profile(pipeline=pipeline)  # type: ignore[arg-type]
        == DEFAULT_REQUIRED_PERSISTENCE_PROFILE
    )


def test_yaml_config_to_domain_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        bundle_mod, "_yaml_config_to_domain_direct", lambda **_kwargs: "domain"
    )
    assert bundle_mod.yaml_config_to_domain(MagicMock()) == "domain"


def test_create_runtime_occurrence_batch_id_returns_batch_id() -> None:
    batch_id = create_runtime_occurrence_batch_id("batch_id")
    assert UUID(str(batch_id))


def test_pipeline_config_loader_inner_uses_resolved_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(loaders, "resolve_configs_root", lambda path: path)
    monkeypatch.setattr(
        loaders,
        "load_pipeline_config_from_root",
        lambda pipeline_name, configs_root: f"{pipeline_name}:{configs_root}",
    )
    loader = loaders.create_pipeline_config_loader(tmp_path)
    assert loader("chembl_activity") == f"chembl_activity:{tmp_path}"


def test_cached_bronze_snapshot_refs_empty_when_no_batch_files(tmp_path: Path) -> None:
    (tmp_path / "2026-01-01").mkdir()
    refs = build_cached_bronze_input_snapshot_refs(
        bronze_root=tmp_path, bronze_date="2026-01-01"
    )
    assert refs == ()


def test_canonical_lineage_fragment_id_rejects_layer_aliases() -> None:
    assert _canonical_lineage_fragment_id("bronze") is None
    assert _canonical_lineage_fragment_id("SILVER") is None
    assert _canonical_lineage_fragment_id("gold") is None
