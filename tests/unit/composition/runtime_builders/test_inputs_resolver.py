"""Direct unit tests for runtime input resolution helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from bioetl.composition.runtime_builders import inputs_resolver
from bioetl.application.services.control_plane import RunLedgerService
from bioetl.domain.types import RunID
from bioetl.infrastructure.control_plane import FileRunLedgerStore, FileRunManifestStore
from tests.unit.application.services.run_manifest_test_support import (
    make_run_manifest,
)


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
        "exact_replay": False,
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


def _raise_value_error(_provider: str) -> object:
    raise ValueError("invalid provider config")


def _missing_pagination(_provider: str) -> object:
    return SimpleNamespace()


def _non_int_pagination(_provider: str) -> object:
    return SimpleNamespace(pagination=SimpleNamespace(id_batch_size="50"))


@pytest.mark.unit
def test_prepare_runner_inputs_projects_probe_mode_and_sink_disabled_skip_gold() -> (
    None
):
    logger = SimpleNamespace(info=lambda *_, **__: None)
    settings = SimpleNamespace(
        test_mode=True,
        data_dir="data",
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
def test_prepare_runner_inputs_applies_tracing_override_before_bundle_build() -> None:
    logger = SimpleNamespace(info=lambda *_, **__: None)
    settings = SimpleNamespace(
        test_mode=False,
        data_dir="data",
        pipeline=SimpleNamespace(heartbeat_interval=30, health_check_mode="strict"),
        observability=SimpleNamespace(tracing_enabled=False),
    )
    yaml_config = _make_yaml_config()
    observed: dict[str, object] = {}

    def _build_observability_bundle(**kwargs: object) -> SimpleNamespace:
        observed["tracing_enabled"] = kwargs["settings"].observability.tracing_enabled
        return SimpleNamespace(logger=logger)

    result = inputs_resolver.prepare_runner_inputs(
        ctx=_make_context(tracing_enabled_override=True),
        get_settings_fn=lambda: settings,
        load_pipeline_config_fn=lambda _pipeline: yaml_config,
        build_observability_bundle_fn=_build_observability_bundle,
        assemble_vacuum_settings_fn=inputs_resolver.assemble_vacuum_settings,
        assemble_runtime_config_fn=inputs_resolver.assemble_runtime_config,
        assemble_filter_config_fn=inputs_resolver.assemble_filter_config,
        assemble_cached_bronze_context_fn=inputs_resolver.assemble_cached_bronze_context,
    )

    assert observed["tracing_enabled"] is True
    assert result.settings.observability.tracing_enabled is True


@pytest.mark.unit
def test_prepare_runner_inputs_auto_resolves_cached_bronze_for_exact_replay_parent(
    tmp_path: Path,
) -> None:
    logger = SimpleNamespace(info=lambda *_, **__: None)
    bronze_root = tmp_path / "output" / "bronze"
    settings = SimpleNamespace(
        data_dir=tmp_path,
        bronze_path=bronze_root,
        test_mode=False,
        pipeline=SimpleNamespace(heartbeat_interval=30, health_check_mode="strict"),
        observability=SimpleNamespace(tracing_enabled=False),
    )
    yaml_config = _make_yaml_config()
    parent_manifest = make_run_manifest(
        manifest_id="manifest-parent",
        run_id=RunID(uuid4()),
        created_at=datetime(2026, 5, 8, 18, 0, tzinfo=UTC),
    )
    manifest_store = FileRunManifestStore(
        base_path=tmp_path / "output" / "control" / "run_manifest"
    )
    manifest_store.save(parent_manifest)
    ledger_store = FileRunLedgerStore(
        base_path=tmp_path / "output" / "control" / "run_ledger"
    )
    ledger_service = RunLedgerService(
        ledger_port=ledger_store,
        manifest_id=parent_manifest.manifest_id,
        run_id=parent_manifest.run_id,
        _entry_id_factory=lambda: "entry-input-snapshot",
    )
    ledger_service.record_input_snapshot_published(
        provider="chembl",
        entity="activity",
        pipeline_name="chembl_activity",
        snapshot_id="sha256:snapshot-1",
        content_hash="snapshot-1",
        immutable_uri="bronze://2026-05-08/batch_2026-05-08_abc.jsonl.zst",
        bronze_batch_ref=str(bronze_root / "chembl" / "activity"),
    )

    result = inputs_resolver.prepare_runner_inputs(
        ctx=_make_context(
            exact_replay=True,
            replay_of_manifest_id=parent_manifest.manifest_id,
        ),
        get_settings_fn=lambda: settings,
        load_pipeline_config_fn=lambda _pipeline: yaml_config,
        build_observability_bundle_fn=lambda **_: SimpleNamespace(logger=logger),
        assemble_vacuum_settings_fn=inputs_resolver.assemble_vacuum_settings,
        assemble_runtime_config_fn=inputs_resolver.assemble_runtime_config,
        assemble_filter_config_fn=inputs_resolver.assemble_filter_config,
        assemble_cached_bronze_context_fn=inputs_resolver.assemble_cached_bronze_context,
    )

    assert result.cached_bronze.enabled is True
    assert result.cached_bronze.bronze_path == str(bronze_root / "chembl" / "activity")
    assert result.cached_bronze.bronze_date == "2026-05-08"
    assert result.runtime_config.replay_anchor_date == "2026-05-08"


@pytest.mark.unit
def test_assemble_runtime_config_propagates_replay_anchor_date_for_exact_replay() -> (
    None
):
    result = inputs_resolver.assemble_runtime_config(
        ctx=_make_context(
            exact_replay=True,
            cached_bronze=SimpleNamespace(
                enabled=True,
                bronze_path="test-output/bronze",
                bronze_date="2026-04-10",
            ),
        ),
        heartbeat_interval=30,
        vacuum=inputs_resolver.ResolvedVacuumSettings(
            enabled=False,
            retention_days=7,
        ),
        health_check_mode="strict",
        skip_gold=False,
    )

    assert result.exact_replay is True
    assert result.replay_anchor_date == "2026-04-10"


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


@pytest.mark.unit
def test_resolve_filter_batch_size_falls_back_to_source_config_pagination() -> None:
    calls: list[str] = []
    yaml_config = _make_yaml_config()

    result = inputs_resolver.resolve_filter_batch_size(
        yaml_config,
        load_source_config_fn=lambda provider: (
            calls.append(provider)
            or SimpleNamespace(pagination=SimpleNamespace(id_batch_size=40))
        ),
    )

    assert result == 40
    assert calls == ["chembl"]


@pytest.mark.unit
@pytest.mark.parametrize(
    "loader",
    [_raise_value_error, _missing_pagination, _non_int_pagination],
)
def test_resolve_filter_batch_size_returns_none_on_loader_error_or_invalid_value(
    loader: object,
) -> None:
    yaml_config = _make_yaml_config()

    result = inputs_resolver.resolve_filter_batch_size(
        yaml_config,
        load_source_config_fn=loader,
    )

    assert result is None


@pytest.mark.unit
def test_adjust_batch_size_for_filter_mutates_yaml_and_logs_when_filter_is_active() -> (
    None
):
    events: list[tuple[str, dict[str, object]]] = []
    yaml_config = _make_yaml_config(batch_size=100)
    observability = SimpleNamespace(
        logger=SimpleNamespace(
            info=lambda event, **kwargs: events.append((event, kwargs))
        )
    )

    inputs_resolver.adjust_batch_size_for_filter(
        yaml_config=yaml_config,
        filter_config=SimpleNamespace(source_path="ids.csv"),
        observability=observability,
        load_source_config_fn=lambda _provider: SimpleNamespace(
            pagination=SimpleNamespace(id_batch_size=25)
        ),
    )

    assert yaml_config.batch_size == 25
    assert events == [
        (
            "batch_size_auto_adjusted",
            {
                "original": 100,
                "adjusted": 25,
                "reason": "input_filter_active",
            },
        )
    ]


@pytest.mark.unit
@pytest.mark.parametrize(
    ("filter_config", "loader", "expected_batch_size"),
    [
        (
            None,
            lambda _provider: SimpleNamespace(
                pagination=SimpleNamespace(id_batch_size=25)
            ),
            100,
        ),
        (
            SimpleNamespace(source_path="ids.csv"),
            _non_int_pagination,
            100,
        ),
    ],
)
def test_adjust_batch_size_for_filter_noops_without_active_filter_or_resolved_size(
    filter_config: object,
    loader: object,
    expected_batch_size: int,
) -> None:
    events: list[tuple[str, dict[str, object]]] = []
    yaml_config = _make_yaml_config(batch_size=100)
    observability = SimpleNamespace(
        logger=SimpleNamespace(
            info=lambda event, **kwargs: events.append((event, kwargs))
        )
    )

    inputs_resolver.adjust_batch_size_for_filter(
        yaml_config=yaml_config,
        filter_config=filter_config,
        observability=observability,
        load_source_config_fn=loader,
    )

    assert yaml_config.batch_size == expected_batch_size
    assert events == []


@pytest.mark.unit
def test_prepare_runner_inputs_adjusts_batch_size_from_source_config_when_filter_enabled() -> (
    None
):
    events: list[tuple[str, dict[str, object]]] = []
    logger = SimpleNamespace(
        info=lambda event, **kwargs: events.append((event, kwargs)),
    )
    settings = SimpleNamespace(
        test_mode=False,
        data_dir="data",
        pipeline=SimpleNamespace(heartbeat_interval=30, health_check_mode="strict"),
    )
    yaml_config = _make_yaml_config(batch_size=100)
    filter_config = SimpleNamespace(
        source_path="ids.csv",
        column_name="chembl_id",
        filter_field="chembl_id",
    )

    result = inputs_resolver.prepare_runner_inputs(
        ctx=_make_context(
            input_filter=SimpleNamespace(
                enabled=True,
                source_path="ids.csv",
                column_name="chembl_id",
                filter_field="chembl_id",
                fallback_column=None,
                filter_ids=(),
                fallback_mapping=None,
                multi_filter_ids=None,
                valid_combinations=None,
            )
        ),
        get_settings_fn=lambda: settings,
        load_pipeline_config_fn=lambda _pipeline: yaml_config,
        build_observability_bundle_fn=lambda **_: SimpleNamespace(logger=logger),
        assemble_vacuum_settings_fn=inputs_resolver.assemble_vacuum_settings,
        assemble_runtime_config_fn=inputs_resolver.assemble_runtime_config,
        assemble_filter_config_fn=lambda **_: filter_config,
        assemble_cached_bronze_context_fn=inputs_resolver.assemble_cached_bronze_context,
        load_source_config_fn=lambda _provider: SimpleNamespace(
            pagination=SimpleNamespace(id_batch_size=25)
        ),
    )

    assert result.yaml_config.batch_size == 25
    assert [event for event, _payload in events] == [
        "input_filter_enabled",
        "batch_size_auto_adjusted",
    ]
    assert events[0][1] == {
        "csv_path": "ids.csv",
        "column": "chembl_id",
        "filter_field": "chembl_id",
        "source": "cli",
    }
    assert events[1][1] == {
        "original": 100,
        "adjusted": 25,
        "reason": "input_filter_active",
    }


def test_validate_pk_contract_requires_business_primary_keys() -> None:
    config = SimpleNamespace(
        business_primary_keys=[],
        technical_primary_key="entity_id",
    )

    with pytest.raises(ValueError, match="business_primary_keys must be non-empty"):
        inputs_resolver.validate_pk_contract(config)


def test_validate_pk_contract_ignores_legacy_attribute_when_present() -> None:
    config = SimpleNamespace(
        business_primary_keys=["entity_id"],
        primary_keys=["legacy_id"],
        technical_primary_key="entity_id",
    )

    inputs_resolver.validate_pk_contract(config)


def test_validate_pk_contract_requires_technical_primary_key() -> None:
    config = SimpleNamespace(
        business_primary_keys=["entity_id"],
        technical_primary_key="",
    )

    with pytest.raises(ValueError, match="technical_primary_key must be non-empty"):
        inputs_resolver.validate_pk_contract(config)
