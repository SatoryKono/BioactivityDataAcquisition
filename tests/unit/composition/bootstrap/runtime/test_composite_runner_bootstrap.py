"""Unit tests for composite runner bootstrap wiring paths."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID
from unittest.mock import MagicMock, patch

import pytest

try:
    import polars as pl

    HAS_POLARS = True
except ImportError:  # pragma: no cover
    HAS_POLARS = False

import bioetl.composition.bootstrap.runtime.composite as composite_runtime

pytestmark = pytest.mark.skipif(not HAS_POLARS, reason="polars not installed")


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
@patch("bioetl.composition.bootstrap.runtime.composite._create_dq_report_service")
@patch("bioetl.composition.bootstrap.runtime.composite._resolve_composite_gold_schema")
@patch("bioetl.composition.bootstrap.runtime.composite._load_field_group_registry")
@patch("bioetl.composition.bootstrap.runtime.composite.CompositeCheckpointManager")
@patch("bioetl.composition.bootstrap.runtime.composite.MergeService")
@patch("bioetl.composition.bootstrap.runtime.composite.EnrichmentCrossValidator")
@patch("bioetl.composition.bootstrap.runtime.composite.EnrichmentCoordinator")
@patch("bioetl.composition.bootstrap.runtime.composite.DependencyCoordinator")
@patch("bioetl.composition.bootstrap.runtime.composite.KeyExtractorService")
@patch("bioetl.composition.bootstrap.runtime.composite.DeltaReader")
@patch("bioetl.composition.bootstrap.runtime.composite.MemoryLock")
@patch("bioetl.composition.bootstrap.runtime.composite.bootstrap_storage_adapter")
@patch("bioetl.composition.bootstrap.runtime.composite.bootstrap_logger_port")
@patch("bioetl.composition.bootstrap.runtime.composite.get_settings")
@patch("bioetl.composition.bootstrap.runtime.composite.bootstrap_pipeline_runner")
@patch("bioetl.composition.entrypoints.build_pipeline_context")
@patch("bioetl.composition.entrypoints.RunOptions")
@patch("bioetl.composition.bootstrap.assembly.checkpoint.bootstrap_quarantine_port")
def test_bootstrap_composite_runner_wires_factories(
    mock_bootstrap_quarantine_port: MagicMock,
    mock_run_options: MagicMock,
    mock_build_pipeline_context: MagicMock,
    mock_bootstrap_pipeline_runner: MagicMock,
    mock_get_settings: MagicMock,
    mock_bootstrap_logger: MagicMock,
    mock_bootstrap_storage: MagicMock,
    mock_memory_lock: MagicMock,
    mock_delta_reader: MagicMock,
    mock_key_extractor: MagicMock,
    mock_dependency_coordinator: MagicMock,
    mock_enrichment_coordinator: MagicMock,
    mock_cross_validator: MagicMock,
    mock_merge_service: MagicMock,
    mock_checkpoint_manager: MagicMock,
    mock_load_field_groups: MagicMock,
    mock_resolve_gold_schema: MagicMock,
    mock_create_dq_report_service: MagicMock,
    mock_runner_cls: MagicMock,
) -> None:
    config = _make_config(cross_validation_enabled=True)
    runtime = _make_runtime()
    logger = MagicMock()

    mock_get_settings.return_value = SimpleNamespace(data_dir="data")
    mock_bootstrap_logger.return_value = logger
    mock_bootstrap_storage.return_value = MagicMock()
    mock_memory_lock.return_value = MagicMock()
    mock_delta_reader.return_value = MagicMock()
    mock_key_extractor.return_value = MagicMock()
    mock_dependency_coordinator.return_value = MagicMock()
    mock_enrichment_coordinator.return_value = MagicMock()
    mock_cross_validator.return_value = MagicMock()
    mock_merge_service.return_value = MagicMock()
    mock_checkpoint_manager.return_value = MagicMock()
    mock_load_field_groups.return_value = MagicMock()
    mock_resolve_gold_schema.return_value = MagicMock()
    mock_create_dq_report_service.return_value = MagicMock()
    mock_bootstrap_quarantine_port.return_value = MagicMock()
    mock_run_options.side_effect = lambda **kwargs: SimpleNamespace(**kwargs)
    mock_build_pipeline_context.side_effect = lambda pipeline, options: {
        "pipeline": pipeline,
        "options": options,
    }
    mock_bootstrap_pipeline_runner.side_effect = lambda ctx: ctx

    runner_instance = MagicMock(name="composite_runner")
    mock_runner_cls.return_value = runner_instance

    result = composite_runtime.bootstrap_composite_runner(
        config=config,
        runtime=runtime,
        run_id="00000000-0000-0000-0000-000000000001",
    )

    assert result is runner_instance
    call_kwargs = mock_runner_cls.call_args.kwargs

    seed_runner = call_kwargs["seed_runner_factory"]()
    keys = pl.DataFrame(
        {
            "doi": ["10.1000/test"],
            "title": ["Test title"],
            "compound_id": [123],
            "document_id": ["DOC-1"],
        }
    )
    enricher_runner = call_kwargs["enricher_runner_factory"](
        "crossref_publication", keys
    )
    dependency_single = call_kwargs["dependencies_runner_factory"](
        "pubchem_single", keys
    )
    dependency_multi = call_kwargs["dependencies_runner_factory"]("pubchem_multi", keys)

    assert seed_runner["pipeline"] == "chembl_publication"
    assert enricher_runner["pipeline"] == "crossref_publication"
    assert dependency_single["pipeline"] == "pubchem_single"
    assert dependency_multi["pipeline"] == "pubchem_multi"

    options_calls = [c.kwargs for c in mock_run_options.call_args_list]
    assert any(c.get("execution_context") == "enricher" for c in options_calls)
    assert any(c.get("execution_context") == "dependency" for c in options_calls)
    assert any(c.get("filter_field") == "cid" for c in options_calls)
    assert any(c.get("multi_filter_ids") for c in options_calls)

    assert mock_bootstrap_quarantine_port.called


@pytest.mark.unit
@patch("bioetl.composition.bootstrap.runtime.composite.CompositePipelineRunner")
@patch("bioetl.composition.bootstrap.runtime.composite._create_dq_report_service")
@patch("bioetl.composition.bootstrap.runtime.composite._resolve_composite_gold_schema")
@patch("bioetl.composition.bootstrap.runtime.composite._load_field_group_registry")
@patch("bioetl.composition.bootstrap.runtime.composite.CompositeCheckpointManager")
@patch("bioetl.composition.bootstrap.runtime.composite.MergeService")
@patch("bioetl.composition.bootstrap.runtime.composite.EnrichmentCrossValidator")
@patch("bioetl.composition.bootstrap.runtime.composite.EnrichmentCoordinator")
@patch("bioetl.composition.bootstrap.runtime.composite.DependencyCoordinator")
@patch("bioetl.composition.bootstrap.runtime.composite.KeyExtractorService")
@patch("bioetl.composition.bootstrap.runtime.composite.DeltaReader")
@patch("bioetl.composition.bootstrap.runtime.composite.MemoryLock")
@patch("bioetl.composition.bootstrap.runtime.composite.bootstrap_storage_adapter")
@patch("bioetl.composition.bootstrap.runtime.composite.bootstrap_logger_port")
@patch("bioetl.composition.bootstrap.runtime.composite.get_settings")
@patch("bioetl.composition.bootstrap.runtime.composite.bootstrap_pipeline_runner")
@patch("bioetl.composition.entrypoints.build_pipeline_context")
@patch("bioetl.composition.entrypoints.RunOptions")
@patch("bioetl.composition.bootstrap.runtime.composite.uuid4")
@patch("bioetl.composition.bootstrap.assembly.checkpoint.bootstrap_quarantine_port")
def test_bootstrap_composite_runner_without_cross_validation(
    mock_bootstrap_quarantine_port: MagicMock,
    mock_uuid4: MagicMock,
    mock_run_options: MagicMock,
    mock_build_pipeline_context: MagicMock,
    mock_bootstrap_pipeline_runner: MagicMock,
    mock_get_settings: MagicMock,
    mock_bootstrap_logger: MagicMock,
    mock_bootstrap_storage: MagicMock,
    mock_memory_lock: MagicMock,
    mock_delta_reader: MagicMock,
    mock_key_extractor: MagicMock,
    mock_dependency_coordinator: MagicMock,
    mock_enrichment_coordinator: MagicMock,
    mock_cross_validator: MagicMock,
    mock_merge_service: MagicMock,
    mock_checkpoint_manager: MagicMock,
    mock_load_field_groups: MagicMock,
    mock_resolve_gold_schema: MagicMock,
    mock_create_dq_report_service: MagicMock,
    mock_runner_cls: MagicMock,
) -> None:
    config = _make_config(cross_validation_enabled=False)
    runtime = _make_runtime(use_cached_bronze=False)

    mock_get_settings.return_value = SimpleNamespace(data_dir="data")
    mock_bootstrap_logger.return_value = MagicMock()
    mock_bootstrap_storage.return_value = MagicMock()
    mock_memory_lock.return_value = MagicMock()
    mock_delta_reader.return_value = MagicMock()
    mock_key_extractor.return_value = MagicMock()
    mock_dependency_coordinator.return_value = MagicMock()
    mock_enrichment_coordinator.return_value = MagicMock()
    mock_merge_service.return_value = MagicMock()
    mock_checkpoint_manager.return_value = MagicMock()
    mock_load_field_groups.return_value = None
    mock_resolve_gold_schema.return_value = None
    mock_create_dq_report_service.return_value = MagicMock()
    mock_run_options.side_effect = lambda **kwargs: SimpleNamespace(**kwargs)
    mock_build_pipeline_context.side_effect = lambda pipeline, options: {
        "pipeline": pipeline,
        "options": options,
    }
    mock_bootstrap_pipeline_runner.side_effect = lambda ctx: ctx

    generated_run_id = UUID("00000000-0000-0000-0000-000000000002")
    mock_uuid4.return_value = generated_run_id

    composite_runtime.bootstrap_composite_runner(
        config=config,
        runtime=runtime,
        run_id=None,
    )

    mock_cross_validator.assert_not_called()
    mock_bootstrap_quarantine_port.assert_not_called()
    assert mock_checkpoint_manager.call_args.kwargs["run_id"] == str(generated_run_id)


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
