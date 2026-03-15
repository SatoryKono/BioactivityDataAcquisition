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
def test_bootstrap_composite_runner_orchestrates_builders() -> None:
    config = _make_config(cross_validation_enabled=True)
    runtime = _make_runtime()
    logger = MagicMock()
    lock = MagicMock()

    seed_runner_factory = MagicMock(name="seed_runner_factory")
    enricher_runner_factory = MagicMock(name="enricher_runner_factory")
    dependency_runner_factory = MagicMock(name="dependency_runner_factory")
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
    composite_runner = MagicMock(name="composite_runner")

    runtime_basics = SimpleNamespace(
        run_id="00000000-0000-0000-0000-000000000001",
        settings=MagicMock(),
        logger=logger,
        storage=MagicMock(),
        lock=lock,
    )

    with (
        patch(
            "bioetl.composition.bootstrap.runtime.composite._bootstrap_runtime_basics"
        ) as mock_runtime_basics,
        patch(
            "bioetl.composition.bootstrap.runtime.composite._build_runner_factories"
        ) as mock_build_runner_factories,
        patch(
            "bioetl.composition.bootstrap.runtime.composite._build_support_services"
        ) as mock_build_support_services,
        patch(
            "bioetl.composition.bootstrap.runtime.composite.create_composite_runner_with_legacy_fsm_adapter"
        ) as mock_runner_cls,
    ):
        mock_runtime_basics.return_value = runtime_basics
        mock_build_runner_factories.return_value = (
            seed_runner_factory,
            dependency_runner_factory,
            enricher_runner_factory,
        )
        mock_build_support_services.return_value = support_bundle
        mock_runner_cls.return_value = composite_runner

        result = composite_runtime.bootstrap_composite_runner(
            config=config,
            runtime=runtime,
            run_id="00000000-0000-0000-0000-000000000001",
        )

    assert result is composite_runner
    mock_runtime_basics.assert_called_once_with(
        config=config,
        run_id="00000000-0000-0000-0000-000000000001",
    )
    mock_build_runner_factories.assert_called_once_with(
        config=config,
        runtime=runtime,
        logger=runtime_basics.logger,
    )
    mock_build_support_services.assert_called_once_with(
        config=config,
        runtime=runtime,
        runtime_basics=runtime_basics,
    )

    call_kwargs = mock_runner_cls.call_args.kwargs
    assert call_kwargs["seed_runner_factory"] is seed_runner_factory
    assert call_kwargs["enricher_runner_factory"] is enricher_runner_factory
    assert call_kwargs["dependencies_runner_factory"] is dependency_runner_factory
    assert call_kwargs["logger"] is logger
    assert call_kwargs["lock"] is lock
    assert call_kwargs["run_id"] == "00000000-0000-0000-0000-000000000001"
    assert call_kwargs["key_extractor"] is support_bundle.key_extractor
    assert call_kwargs["coordinator"] is support_bundle.coordinator
    assert call_kwargs["merger"] is support_bundle.merger
    assert call_kwargs["checkpoint_manager"] is support_bundle.checkpoint_manager
    assert call_kwargs["dq_report_service"] is support_bundle.dq_report_service
    assert call_kwargs["fsm_state_helper"] is support_bundle.fsm_state_helper


@pytest.mark.unit
def test_bootstrap_composite_runner_generates_run_id() -> None:
    config = _make_config(cross_validation_enabled=False)
    runtime = _make_runtime(use_cached_bronze=False)

    generated_run_id = UUID("00000000-0000-0000-0000-000000000002")
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
    runtime_basics = SimpleNamespace(
        run_id=str(generated_run_id),
        settings=MagicMock(),
        logger=MagicMock(),
        storage=MagicMock(),
        lock=MagicMock(),
    )

    with (
        patch(
            "bioetl.composition.bootstrap.runtime.composite._bootstrap_runtime_basics"
        ) as mock_runtime_basics,
        patch(
            "bioetl.composition.bootstrap.runtime.composite._build_runner_factories"
        ) as mock_build_runner_factories,
        patch(
            "bioetl.composition.bootstrap.runtime.composite._build_support_services"
        ) as mock_build_support_services,
        patch(
            "bioetl.composition.bootstrap.runtime.composite.create_composite_runner_with_legacy_fsm_adapter"
        ) as mock_runner_cls,
    ):
        mock_runtime_basics.return_value = runtime_basics
        mock_build_runner_factories.return_value = (
            MagicMock(),
            MagicMock(),
            MagicMock(),
        )
        mock_build_support_services.return_value = support_bundle
        mock_runner_cls.return_value = MagicMock()

        composite_runtime.bootstrap_composite_runner(
            config=config,
            runtime=runtime,
            run_id=None,
        )

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
def test_bootstrap_composite_runner_delegates_final_assembly_to_plan_helper() -> None:
    config = _make_config(cross_validation_enabled=False)
    runtime = _make_runtime()
    plan = SimpleNamespace(
        run_id="00000000-0000-0000-0000-000000000004",
        logger=MagicMock(),
        lock=MagicMock(),
        seed_runner_factory=MagicMock(),
        dependencies_runner_factory=MagicMock(),
        enricher_runner_factory=MagicMock(),
        support_services=MagicMock(),
    )

    with (
        patch(
            "bioetl.composition.bootstrap.runtime.composite._build_composite_bootstrap_plan"
        ) as mock_build_plan,
        patch(
            "bioetl.composition.bootstrap.runtime.composite._create_composite_runner_from_plan"
        ) as mock_create_from_plan,
    ):
        mock_build_plan.return_value = plan
        runner = MagicMock()
        mock_create_from_plan.return_value = runner

        result = composite_runtime.bootstrap_composite_runner(
            config=config,
            runtime=runtime,
            run_id="00000000-0000-0000-0000-000000000004",
        )

    assert result is runner
    mock_build_plan.assert_called_once_with(
        config=config,
        runtime=runtime,
        run_id="00000000-0000-0000-0000-000000000004",
    )
    mock_create_from_plan.assert_called_once_with(
        config=config,
        runtime=runtime,
        plan=plan,
    )


@pytest.mark.unit
def test_build_composite_bootstrap_plan_uses_named_runtime_basics_context() -> None:
    config = _make_config(cross_validation_enabled=False)
    runtime = _make_runtime()
    runtime_basics = SimpleNamespace(
        run_id="00000000-0000-0000-0000-000000000005",
        settings=MagicMock(),
        logger=MagicMock(),
        storage=MagicMock(),
        lock=MagicMock(),
    )
    seed_runner_factory = MagicMock()
    dependencies_runner_factory = MagicMock()
    enricher_runner_factory = MagicMock()
    support_services = MagicMock()

    with (
        patch(
            "bioetl.composition.bootstrap.runtime.composite._bootstrap_runtime_basics"
        ) as mock_runtime_basics,
        patch(
            "bioetl.composition.bootstrap.runtime.composite._build_runner_factories"
        ) as mock_build_runner_factories,
        patch(
            "bioetl.composition.bootstrap.runtime.composite._build_support_services"
        ) as mock_build_support_services,
    ):
        mock_runtime_basics.return_value = runtime_basics
        mock_build_runner_factories.return_value = (
            seed_runner_factory,
            dependencies_runner_factory,
            enricher_runner_factory,
        )
        mock_build_support_services.return_value = support_services

        plan = composite_runtime._build_composite_bootstrap_plan(
            config=config,
            runtime=runtime,
            run_id="00000000-0000-0000-0000-000000000005",
        )

    assert plan.run_id == runtime_basics.run_id
    assert plan.logger is runtime_basics.logger
    assert plan.lock is runtime_basics.lock
    assert plan.seed_runner_factory is seed_runner_factory
    assert plan.dependencies_runner_factory is dependencies_runner_factory
    assert plan.enricher_runner_factory is enricher_runner_factory
    assert plan.support_services is support_services
    mock_build_runner_factories.assert_called_once_with(
        config=config,
        runtime=runtime,
        logger=runtime_basics.logger,
    )
    mock_build_support_services.assert_called_once_with(
        config=config,
        runtime=runtime,
        runtime_basics=runtime_basics,
    )
