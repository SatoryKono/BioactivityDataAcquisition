"""Factory fallback and optional metadata binding preserve explicit dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from bioetl.application.pipelines.common.base_publication_transformer import (
    BasePublicationTransformer,
)
from bioetl.composition.bootstrap import (
    composite_infrastructure_context as composite_context,
)
from bioetl.composition.factories import transformer_dependencies
from bioetl.composition.factories.datasource import pubchem
from bioetl.composition.factories.storage._context_resolution import _csv_path_override
from bioetl.composition.runtime_builders import run_manifest_data_roots
from bioetl.composition.runtime_builders._exact_replay_cached_bronze_context import (
    bind_cached_bronze_context,
)
from bioetl.domain.resilience import RetryConfig

pytestmark = pytest.mark.unit


def test_absent_pubchem_configuration_keeps_documented_local_defaults(monkeypatch):
    def missing(provider):
        raise ValueError("provider is not configured")

    monkeypatch.setattr(pubchem, "load_source_config", missing)
    assert pubchem._resolve_executor_timeout("absent") == 30.0
    assert pubchem._resolve_retry_config("absent") == RetryConfig()


def test_cached_bronze_binding_rejects_a_context_class_without_mutating_it():
    @dataclass
    class Context:
        cached_bronze: object = None

    with pytest.raises(TypeError, match="dataclass instance"):
        bind_cached_bronze_context(Context, object())
    assert Context.cached_bronze is None


def test_missing_csv_export_does_not_create_an_override(tmp_path):
    assert _csv_path_override(None, tmp_path) is None


def test_opaque_transformer_metadata_does_not_load_vocabulary(monkeypatch):
    loader = Mock(side_effect=AssertionError("unexpected config read"))
    monkeypatch.setattr(transformer_dependencies, "resolve_configs_root", loader)
    assert (
        transformer_dependencies.publication_vocabulary_kwargs(
            SimpleNamespace(__mro__=[])
        )
        == {}
    )
    loader.assert_not_called()


def test_publication_factory_receives_the_loaded_registry_instances(
    tmp_path, monkeypatch
):
    vocabulary, classification = object(), object()
    monkeypatch.setattr(
        transformer_dependencies, "resolve_configs_root", lambda root: tmp_path
    )
    monkeypatch.setattr(
        transformer_dependencies,
        "load_publication_controlled_vocabulary",
        lambda root: vocabulary,
    )
    monkeypatch.setattr(
        transformer_dependencies,
        "_load_publication_type_classification_data",
        lambda root: classification,
    )
    assert transformer_dependencies.publication_vocabulary_kwargs(
        BasePublicationTransformer
    ) == {
        "publication_vocabulary": vocabulary,
        "publication_classification": classification,
    }


def test_optional_protein_mapping_tracks_installation_without_inventing_data(
    monkeypatch,
):
    monkeypatch.setattr(
        composite_context,
        "is_protein_class_target_type_mapping_initialized",
        lambda: False,
    )
    assert composite_context.current_target_protein_classification_mapping() is None
    expected = object()
    monkeypatch.setattr(
        composite_context,
        "is_protein_class_target_type_mapping_initialized",
        lambda: True,
    )
    monkeypatch.setattr(
        composite_context, "current_protein_class_target_type_mapping", lambda: expected
    )
    assert composite_context.current_target_protein_classification_mapping() is expected


def test_windows_private_directory_check_does_not_apply_posix_mode_policy(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(run_manifest_data_roots, "os", SimpleNamespace(name="nt"))
    assert run_manifest_data_roots._assert_private_runtime_dir(tmp_path) is None


def test_non_strict_cached_bronze_defers_validation_until_manifest_is_persisted(
    monkeypatch,
):
    from bioetl.composition.factories.pipeline_support import checkpoint_policy_helpers

    validator = Mock(side_effect=AssertionError("premature snapshot validation"))
    monkeypatch.setattr(
        checkpoint_policy_helpers,
        "require_cached_bronze_input_snapshot_refs",
        validator,
    )
    context = SimpleNamespace(
        cached_bronze=SimpleNamespace(enabled=True),
        exact_replay=False,
        required_persistence_profile="degraded_observable",
    )
    assert (
        checkpoint_policy_helpers._fail_fast_empty_explicit_cached_bronze(context)
        is None
    )
    validator.assert_not_called()
