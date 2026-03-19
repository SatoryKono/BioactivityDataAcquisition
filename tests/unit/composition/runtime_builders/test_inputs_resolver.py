"""Direct unit tests for runtime input resolution helpers."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from bioetl.composition.runtime_builders import inputs_resolver


def _make_context(**overrides: object) -> SimpleNamespace:
    base = {
        "pipeline_name": "chembl_activity",
        "run_id": uuid4(),
        "log_level": "INFO",
        "vacuum": SimpleNamespace(enabled=None, retention_days=7),
        "run_type": "incremental",
        "resume": False,
        "limit": None,
        "query": None,
        "dry_run": False,
        "skip_gold": False,
        "start_offset": None,
        "ignore_yaml_filter": False,
        "cached_bronze": SimpleNamespace(
            enabled=False,
            bronze_path=None,
            bronze_date=None,
        ),
        "input_filter": SimpleNamespace(
            enabled=False,
            source_path=None,
            column_name=None,
            filter_field=None,
            fallback_column=None,
            filter_ids=(),
            fallback_mapping=None,
            multi_filter_ids=None,
            valid_combinations=None,
        ),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _make_yaml_config(**overrides: object) -> SimpleNamespace:
    base = {
        "pipeline_name": "chembl_activity",
        "maintenance": SimpleNamespace(auto_vacuum=False, vacuum_retention_days=7),
        "input_filter": SimpleNamespace(
            enabled=False,
            source_path=None,
            column_name=None,
            filter_field=None,
            fallback_column=None,
            batch_size=100,
        ),
        "business_primary_keys": ["activity_id"],
        "technical_primary_key": "entity_id",
        "batch_size": 100,
        "provider": "chembl",
        "sink": {"gold": SimpleNamespace(enabled=True)},
    }
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.mark.unit
def test_prepare_runner_inputs_projects_probe_mode_and_sink_disabled_skip_gold() -> (
    None
):
    logger = SimpleNamespace(info=lambda *_, **__: None)
    settings = SimpleNamespace(
        test_mode=True,
        pipeline=SimpleNamespace(heartbeat_interval=30, health_check_mode="strict"),
    )
    yaml_config = _make_yaml_config(sink={"gold": SimpleNamespace(enabled=False)})

    result = inputs_resolver.prepare_runner_inputs(
        ctx=_make_context(),
        get_settings_fn=lambda: settings,
        load_pipeline_config_fn=lambda _pipeline: yaml_config,
        build_observability_bundle_fn=lambda **_: SimpleNamespace(logger=logger),
        assemble_vacuum_settings_fn=inputs_resolver.assemble_vacuum_settings,
        assemble_runtime_config_fn=inputs_resolver.assemble_runtime_config,
        assemble_filter_config_fn=inputs_resolver.assemble_filter_config,
        assemble_cached_bronze_context_fn=inputs_resolver.assemble_cached_bronze_context,
    )

    assert result.runtime_config.health_check_mode == "probe"
    assert result.runtime_config.skip_gold is True


@pytest.mark.unit
def test_resolve_health_check_mode_defaults_to_strict_when_pipeline_mode_missing() -> (
    None
):
    settings = SimpleNamespace(
        test_mode=False,
        pipeline=SimpleNamespace(),
    )

    result = inputs_resolver.resolve_health_check_mode(settings=settings)

    assert result == "strict"
