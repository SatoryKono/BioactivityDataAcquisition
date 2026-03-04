"""Unit tests for composite runner bootstrap orchestration."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID
from unittest.mock import MagicMock, patch

import pytest

import bioetl.composition.bootstrap.runtime.composite as composite_runtime


def _make_runtime(**overrides: object) -> SimpleNamespace:
    base = {
        "seed_limit": 100,
        "resume": True,
        "use_cached_bronze": True,
        "cached_bronze_path": "data/bronze",
        "cached_bronze_date": "2026-01-01",
        "cached_bronze_enrichers": None,
        "cached_bronze_dependencies": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _make_config(*, cross_validation_enabled: bool) -> SimpleNamespace:
    seed = SimpleNamespace(pipeline="chembl_publication")
    enrichers = [
        SimpleNamespace(
            pipeline="crossref_publication",
            join_keys=("doi", "title"),
            is_many_to_one=False,
        )
    ]
    dependencies = [
        SimpleNamespace(
            pipeline="pubchem_single",
            join_keys=("compound_id",),
            is_multi_field_filter=False,
            effective_filter_fields=(),
            filter_field="cid",
            key_source=None,
        ),
        SimpleNamespace(
            pipeline="pubchem_multi",
            join_keys=("compound_id", "document_id"),
            is_multi_field_filter=True,
            effective_filter_fields=("compound_id", "document_id"),
            filter_field=None,
            key_source="pubchem_single",
        ),
    ]

    return SimpleNamespace(
        name="composite_publication",
        seed=seed,
        enrichers=enrichers,
        dependencies=dependencies,
        dq=SimpleNamespace(),
        execution=SimpleNamespace(max_concurrency=3),
        merge=SimpleNamespace(),
        cross_validation=SimpleNamespace(enabled=cross_validation_enabled),
    )


@pytest.mark.unit
@patch("bioetl.composition.bootstrap.runtime.composite.CompositePipelineRunner")
@patch("bioetl.composition.bootstrap.runtime.composite.CompositeSupportServicesFactory")
@patch("bioetl.composition.bootstrap.runtime.composite.RunnerFactoryBuilderService")
@patch("bioetl.composition.bootstrap.runtime.composite.MemoryLock")
@patch("bioetl.composition.bootstrap.runtime.composite.bootstrap_storage_adapter")
@patch("bioetl.composition.bootstrap.runtime.composite.bootstrap_logger_port")
@patch("bioetl.composition.bootstrap.runtime.composite.get_settings")
def test_bootstrap_composite_runner_orchestrates_builders(
    mock_get_settings: MagicMock,
    mock_bootstrap_logger: MagicMock,
    mock_bootstrap_storage: MagicMock,
    mock_memory_lock: MagicMock,
    mock_runner_builder_cls: MagicMock,
    mock_support_factory_cls: MagicMock,
    mock_runner_cls: MagicMock,
) -> None:
    config = _make_config(cross_validation_enabled=True)
    runtime = _make_runtime()
    logger = MagicMock()
    storage = MagicMock()
    lock = MagicMock()

    mock_get_settings.return_value = SimpleNamespace(data_dir="data")
    mock_bootstrap_logger.return_value = logger
    mock_bootstrap_storage.return_value = storage
    mock_memory_lock.return_value = lock

    seed_runner_factory = MagicMock(name="seed_runner_factory")
    enricher_runner_factory = MagicMock(name="enricher_runner_factory")
    dependency_runner_factory = MagicMock(name="dependency_runner_factory")

    runner_builder = MagicMock()
    runner_builder.build_seed_factory.return_value = seed_runner_factory
    runner_builder.build_enricher_factory.return_value = enricher_runner_factory
    runner_builder.build_dependency_factory.return_value = dependency_runner_factory
    mock_runner_builder_cls.return_value = runner_builder

    support_bundle = SimpleNamespace(
        key_extractor=MagicMock(),
        dependency_coordinator=MagicMock(),
        coordinator=MagicMock(),
        merger=MagicMock(),
        checkpoint_manager=MagicMock(),
        dq_report_service=MagicMock(),
        fsm_state_helper=MagicMock(),
        quarantine_port=MagicMock(),
    )
    support_factory = MagicMock()
    support_factory.build.return_value = support_bundle
    mock_support_factory_cls.return_value = support_factory

    composite_runner = MagicMock(name="composite_runner")
    mock_runner_cls.return_value = composite_runner

    result = composite_runtime.bootstrap_composite_runner(
        config=config,
        runtime=runtime,
        run_id="00000000-0000-0000-0000-000000000001",
    )

    assert result is composite_runner
    mock_runner_builder_cls.assert_called_once()
    mock_support_factory_cls.assert_called_once()

    runner_builder.build_seed_factory.assert_called_once_with(
        seed_pipeline="chembl_publication",
        seed_limit=100,
        bronze_opts={
            "use_cached_bronze": True,
            "cached_bronze_path": "data/bronze",
            "cached_bronze_date": "2026-01-01",
        },
    )
    runner_builder.build_enricher_factory.assert_called_once_with(
        enrichers=list(config.enrichers),
        bronze_opts={
            "use_cached_bronze": True,
            "cached_bronze_path": "data/bronze",
            "cached_bronze_date": "2026-01-01",
        },
    )
    runner_builder.build_dependency_factory.assert_called_once_with(
        dependencies=list(config.dependencies),
        bronze_opts={
            "use_cached_bronze": True,
            "cached_bronze_path": "data/bronze",
            "cached_bronze_date": "2026-01-01",
        },
    )

    call_kwargs = mock_runner_cls.call_args.kwargs
    assert call_kwargs["seed_runner_factory"] is seed_runner_factory
    assert call_kwargs["enricher_runner_factory"] is enricher_runner_factory
    assert call_kwargs["dependencies_runner_factory"] is dependency_runner_factory
    assert call_kwargs["logger"] is logger
    assert call_kwargs["lock"] is lock
    assert call_kwargs["run_id"] == "00000000-0000-0000-0000-000000000001"


@pytest.mark.unit
@patch("bioetl.composition.bootstrap.runtime.composite.CompositePipelineRunner")
@patch("bioetl.composition.bootstrap.runtime.composite.CompositeSupportServicesFactory")
@patch("bioetl.composition.bootstrap.runtime.composite.RunnerFactoryBuilderService")
@patch("bioetl.composition.bootstrap.runtime.composite.MemoryLock")
@patch("bioetl.composition.bootstrap.runtime.composite.bootstrap_storage_adapter")
@patch("bioetl.composition.bootstrap.runtime.composite.bootstrap_logger_port")
@patch("bioetl.composition.bootstrap.runtime.composite.get_settings")
@patch("bioetl.composition.bootstrap.runtime.composite.uuid4")
def test_bootstrap_composite_runner_generates_run_id(
    mock_uuid4: MagicMock,
    mock_get_settings: MagicMock,
    mock_bootstrap_logger: MagicMock,
    mock_bootstrap_storage: MagicMock,
    mock_memory_lock: MagicMock,
    mock_runner_builder_cls: MagicMock,
    mock_support_factory_cls: MagicMock,
    mock_runner_cls: MagicMock,
) -> None:
    config = _make_config(cross_validation_enabled=False)
    runtime = _make_runtime(use_cached_bronze=False)

    generated_run_id = UUID("00000000-0000-0000-0000-000000000002")
    mock_uuid4.return_value = generated_run_id
    mock_get_settings.return_value = SimpleNamespace(data_dir="data")
    mock_bootstrap_logger.return_value = MagicMock()
    mock_bootstrap_storage.return_value = MagicMock()
    mock_memory_lock.return_value = MagicMock()

    runner_builder = MagicMock()
    runner_builder.build_seed_factory.return_value = MagicMock()
    runner_builder.build_enricher_factory.return_value = MagicMock()
    runner_builder.build_dependency_factory.return_value = MagicMock()
    mock_runner_builder_cls.return_value = runner_builder

    support_bundle = SimpleNamespace(
        key_extractor=MagicMock(),
        dependency_coordinator=MagicMock(),
        coordinator=MagicMock(),
        merger=MagicMock(),
        checkpoint_manager=MagicMock(),
        dq_report_service=MagicMock(),
        fsm_state_helper=MagicMock(),
        quarantine_port=None,
    )
    support_factory = MagicMock()
    support_factory.build.return_value = support_bundle
    mock_support_factory_cls.return_value = support_factory
    mock_runner_cls.return_value = MagicMock()

    composite_runtime.bootstrap_composite_runner(
        config=config,
        runtime=runtime,
        run_id=None,
    )

    support_factory_call = mock_support_factory_cls.call_args.kwargs
    assert support_factory_call["run_id"] == str(generated_run_id)
    runner_call = mock_runner_cls.call_args.kwargs
    assert runner_call["run_id"] == str(generated_run_id)


@pytest.mark.unit
def test_create_dq_report_service_builds_writer_and_service() -> None:
    logger = MagicMock()
    settings = SimpleNamespace(data_dir="data")

    with (
        patch(
            "bioetl.infrastructure.export.dq_report_writer.DQReportWriter"
        ) as mock_writer,
        patch(
            "bioetl.application.services.dq_report_service.DQReportService"
        ) as mock_service,
    ):
        writer_instance = MagicMock()
        service_instance = MagicMock()
        mock_writer.return_value = writer_instance
        mock_service.return_value = service_instance

        result = composite_runtime._create_dq_report_service(
            logger=logger,
            settings=settings,
        )

    assert result is service_instance
    assert mock_writer.call_args.kwargs["base_path"] == (
        composite_runtime.Path("data") / "output" / "reports" / "dq"
    )
    assert mock_writer.call_args.kwargs["logger"] is logger
    assert mock_service.call_args.kwargs == {
        "logger": logger,
        "report_writer": writer_instance,
    }


@pytest.mark.unit
def test_bootstrap_composite_pipeline_alias_calls_runner() -> None:
    config = _make_config(cross_validation_enabled=False)
    runtime = _make_runtime()

    with patch(
        "bioetl.composition.bootstrap.runtime.composite.bootstrap_composite_runner"
    ) as mock_runner:
        mock_runner.return_value = MagicMock()

        composite_runtime.bootstrap_composite_pipeline(
            config=config,
            runtime=runtime,
            run_id="00000000-0000-0000-0000-000000000003",
        )

    mock_runner.assert_called_once_with(
        config=config,
        runtime=runtime,
        run_id="00000000-0000-0000-0000-000000000003",
    )
