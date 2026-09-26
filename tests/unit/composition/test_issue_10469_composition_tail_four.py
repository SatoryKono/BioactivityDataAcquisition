"""Behavioral coverage for composition one-line residuals in issue #10469."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import bioetl.composition.factories.services as services_facade
import bioetl.composition.factories.transformer_factory as transformer_factory
import bioetl.composition.services.versioning as versioning
from bioetl.composition.bootstrap.runtime.pipeline import (
    _fail_fast_empty_explicit_cached_bronze,
)
from bioetl.composition.factories.services.pipeline_record_processor_builder import (
    _build_debug_export_config,
)
from bioetl.composition.factories.storage._bronze import create_bronze_writer
from bioetl.composition.runtime_builders._run_manifest_context_updates import (
    iter_optional_control_plane_updates,
)
from bioetl.composition.runtime_builders._run_manifest_replay_support import (
    _resolve_replay_id,
)
from bioetl.composition.runtime_builders._run_manifest_snapshot_support import (
    _determine_fallbacks,
)
from bioetl.composition.runtime_builders.runner_control_plane_assembly import (
    _log_effective_required_persistence_profile,
)

pytestmark = pytest.mark.unit


def test_cached_bronze_without_path_requires_no_snapshot_lookup() -> None:
    context = SimpleNamespace(
        cached_bronze=SimpleNamespace(enabled=True, bronze_path="  ")
    )

    assert _fail_fast_empty_explicit_cached_bronze(context) is None


def test_pipeline_without_runtime_has_no_debug_export_config() -> None:
    assert _build_debug_export_config(SimpleNamespace()) is None


def test_service_factory_facade_loads_reviewed_submodule() -> None:
    assert services_facade.__getattr__("bundle").__name__.endswith(".bundle")


def test_bronze_writer_requires_explicit_tracing(tmp_path: Path) -> None:
    with pytest.raises(TypeError, match="requires explicit tracing injection"):
        create_bronze_writer(
            writer_cls=MagicMock(),
            base_path=tmp_path,
            config=None,
            logger=MagicMock(),
            metrics=MagicMock(),
            tracing=None,
            metadata_coordinator=None,
            audit=MagicMock(),
            flat_structure=False,
        )


def test_transformer_loader_rejects_non_class_attribute(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        transformer_factory,
        "import_module",
        lambda _module: SimpleNamespace(NotAClass=object()),
    )

    with pytest.raises(TypeError, match="Expected class"):
        transformer_factory._load_transformer_class("fake.module", "NotAClass")


def test_optional_control_plane_updates_delegate_mapping_projection() -> None:
    assert iter_optional_control_plane_updates(execution_fingerprint="sha256:abc") == (
        ("execution_fingerprint", "sha256:abc"),
    )


def test_replay_parentage_prefers_context_value() -> None:
    context = SimpleNamespace(replay_of_run_id="parent-run")

    assert _resolve_replay_id(context, "replay_of_run_id", {}) == "parent-run"


def test_single_component_pipeline_name_is_both_provider_and_entity() -> None:
    assert _determine_fallbacks("chembl") == ("chembl", "chembl")


def test_control_plane_profile_logging_is_optional() -> None:
    inputs = SimpleNamespace(observability=SimpleNamespace(logger=object()))

    assert (
        _log_effective_required_persistence_profile(
            inputs=inputs,
            configured_profile="best_effort",
            effective_profile="best_effort",
            manifest_enabled=False,
            ledger_enabled=False,
            exact_replay=False,
        )
        is None
    )


def test_repo_lock_hash_returns_none_without_files_or_git_payload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(versioning, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(versioning, "_run_git_command", lambda *_args: None)

    assert versioning._get_repo_dependency_lock_hash() is None
