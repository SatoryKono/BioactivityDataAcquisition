"""Composition binds real derived sources and rejects unsupported replay storage."""

from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from bioetl.application.core.data_sources.assay_parameters import (
    AssayParametersDataSource,
)
from bioetl.composition.factories.services import (
    composite_support_services_factory as composite,
)
from bioetl.composition.providers import registration_bio as providers
from bioetl.composition.runtime_builders import _runner_input_preparation as inputs
from bioetl.domain.config import RuntimeConfig
from bioetl.domain.types import RunType
from tests.unit.composition.bootstrap.runtime.test_composite_support_services_factory import (
    _make_factory,
)

pytestmark = pytest.mark.unit


def test_supported_replay_composite_rejects_non_bundle_storage(monkeypatch):
    factory = _make_factory()
    factory._config.name = next(iter(composite.SUPPORTED_COMPOSITES))
    factory._infra = replace(factory._infra, storage=object())
    context = SimpleNamespace(
        logger=Mock(),
        delta_reader=Mock(),
        control_plane_bundle=Mock(),
        field_group_registry=None,
    )
    monkeypatch.setattr(
        composite, "resolve_composite_support_runtime_context", lambda **kwargs: context
    )
    monkeypatch.setattr(composite, "build_execution_support_services", Mock())
    merge = Mock()
    monkeypatch.setattr(composite, "build_composite_merge_service", merge)
    with pytest.raises(TypeError, match="assay_replay_requires_storage_bundle"):
        factory.build()
    merge.assert_not_called()


def test_chembl_assay_parameter_pipeline_wraps_the_source_as_derived_records(
    monkeypatch,
):
    support = Mock()
    source = object()
    support.create_adapter.return_value = source
    monkeypatch.setattr(
        providers, "resolve_provider_assembly_support", lambda _support: support
    )
    monkeypatch.setattr(
        providers, "_get_adapter_config", lambda *args, **kwargs: object()
    )
    config = SimpleNamespace(entity_type="assay_parameters", extraction_params={})
    result = providers._create_chembl_data_source(object(), config, Mock())
    assert isinstance(result, AssayParametersDataSource)
    assert result._data_source is source
    support.create_adapter.assert_called_once()


def test_derived_inputs_record_actual_extraction_preflight_provenance(monkeypatch):
    runtime = RuntimeConfig(run_type=RunType.INCREMENTAL, query="aspirin")
    logger = Mock()
    prepared = inputs.PreparedRunnerContext(
        settings=Mock(),
        effective_ctx=Mock(),
        cached_bronze=Mock(),
        yaml_config=SimpleNamespace(
            pipeline_name="pubchem_compound", provider="pubchem"
        ),
        observability=SimpleNamespace(logger=logger),
    )
    monkeypatch.setattr(
        inputs, "_resolve_runner_runtime_config", lambda **kwargs: runtime
    )
    monkeypatch.setattr(inputs, "_resolve_runner_filter_config", lambda **kwargs: None)
    result = inputs.resolve_runner_derived_inputs(
        prepared=prepared,
        default_health_check_mode="strict",
        assemble_vacuum_settings_fn=Mock(),
        assemble_runtime_config_fn=Mock(),
        assemble_filter_config_fn=Mock(),
        adjust_batch_size_for_filter_fn=Mock(),
    )
    assert result.runtime_config is runtime and result.filter_config is None
    logger.info.assert_called_once_with(
        "extraction_input_preflight_passed",
        pipeline="pubchem_compound",
        provider="pubchem",
        input_kind="query",
        source_path=None,
        column_name=None,
        filter_field=None,
        id_count=None,
    )
