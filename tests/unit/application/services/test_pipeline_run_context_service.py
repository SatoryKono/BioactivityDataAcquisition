"""Focused unit tests for PipelineRunContextService."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID
from tests.helpers.deterministic_ids import (
    deterministic_run_uuid_from_callsite,
    deterministic_uuid_string_from_callsite,
)

import pytest

from bioetl.application.services.execution.pipeline_run_context_service import (
    PipelineRunContextService,
)
from bioetl.application.services.execution.pipeline_runner_models import RunOptions
from bioetl.domain.types import RunID

FIXED_STARTED_AT = datetime(2026, 4, 24, 12, 0, 0, tzinfo=UTC)


@pytest.mark.unit
class TestMergeOptions:
    """Direct branch coverage for option merge semantics."""

    def test_returns_explicit_options_without_factory_call(self) -> None:
        service = PipelineRunContextService()
        options = RunOptions(run_type="backfill", dry_run=True)
        calls: list[bool] = []

        def default_options_factory(dry_run: bool) -> RunOptions:
            calls.append(dry_run)
            return RunOptions(dry_run=dry_run)

        result = service.merge_options(
            options=options,
            dry_run=False,
            default_options_factory=default_options_factory,
        )

        assert result is options
        assert calls == []

    def test_builds_default_options_when_explicit_options_missing(self) -> None:
        service = PipelineRunContextService()
        calls: list[bool] = []

        def default_options_factory(dry_run: bool) -> RunOptions:
            calls.append(dry_run)
            return RunOptions(dry_run=dry_run, limit=25)

        result = service.merge_options(
            options=None,
            dry_run=True,
            default_options_factory=default_options_factory,
        )

        assert result == RunOptions(dry_run=True, limit=25)
        assert calls == [True]


@pytest.mark.unit
class TestBuildContext:
    """Direct coverage for PipelineRunContext assembly branches."""

    def test_build_context_with_csv_filter_uses_fallback_column(self) -> None:
        service = PipelineRunContextService()

        context = service.build_context(
            pipeline_name="chembl_publication",
            run_id=deterministic_run_uuid_from_callsite(
                "test_pipeline_run_context_service"
            ),
            options=RunOptions(
                run_type="backfill",
                input_csv="ids.csv",
                filter_column="publication_id",
                filter_field="doi",
                fallback_column="pmid",
                vacuum_after_run=True,
            ),
            started_at=FIXED_STARTED_AT,
        )

        assert context.pipeline_name == "chembl_publication"
        assert context.run_type.value == "backfill"
        assert context.has_input_filter is True
        assert context.input_filter.source_path == "ids.csv"
        assert context.input_filter.column_name == "publication_id"
        assert context.input_filter.filter_field == "doi"
        assert context.input_filter.fallback_column == "pmid"
        assert context.vacuum_enabled_override is True
        assert context.vacuum.retention_days == 7

    def test_build_context_with_filter_ids_defaults_filter_field_to_doi(self) -> None:
        service = PipelineRunContextService()

        context = service.build_context(
            pipeline_name="crossref_publication",
            run_id=deterministic_run_uuid_from_callsite(
                "test_pipeline_run_context_service"
            ),
            options=RunOptions(
                filter_ids=("10.1000/1", "10.1000/2"),
                fallback_mapping={"10.1000/1": "PMID:1"},
                use_cached_bronze=True,
                cached_bronze_path="bronze/cache",
                cached_bronze_date="2026-03-18",
            ),
            started_at=FIXED_STARTED_AT,
        )

        assert context.has_input_filter is True
        assert context.input_filter.filter_ids == ("10.1000/1", "10.1000/2")
        assert context.input_filter.filter_field == "doi"
        assert context.input_filter.fallback_mapping == {"10.1000/1": "PMID:1"}
        assert context.has_cached_bronze is True
        assert context.cached_bronze.bronze_path == "bronze/cache"
        assert context.cached_bronze.bronze_date == "2026-03-18"

    def test_build_context_disables_filter_and_cached_bronze_by_default(self) -> None:
        service = PipelineRunContextService()

        context = service.build_context(
            pipeline_name="pubmed_publication",
            run_id=deterministic_run_uuid_from_callsite(
                "test_pipeline_run_context_service"
            ),
            options=RunOptions(),
            started_at=FIXED_STARTED_AT,
        )

        assert context.has_input_filter is False
        assert context.has_cached_bronze is False
        assert context.vacuum_enabled_override is None
        assert context.vacuum.retention_days == 7
        assert context.log_level == "INFO"

    def test_build_context_propagates_tracing_override(self) -> None:
        service = PipelineRunContextService()

        context = service.build_context(
            pipeline_name="chembl_activity",
            run_id=deterministic_run_uuid_from_callsite(
                "test_pipeline_run_context_service"
            ),
            options=RunOptions(enable_tracing=True),
            started_at=FIXED_STARTED_AT,
        )

        assert context.tracing_enabled_override is True
        assert context.workflow_id == "standalone"

    def test_build_context_propagates_workflow_id_for_debug_export_paths(self) -> None:
        service = PipelineRunContextService()

        context = service.build_context(
            pipeline_name="chembl_activity",
            run_id=deterministic_run_uuid_from_callsite(
                "test_pipeline_run_context_service"
            ),
            options=RunOptions(
                debug_export_enabled=True,
                workflow_id="chembl_baseline",
            ),
            started_at=FIXED_STARTED_AT,
        )

        assert context.debug_export_enabled is True
        assert context.workflow_id == "chembl_baseline"

    @pytest.mark.unit
    def test_build_context_propagates_required_persistence_profile(self) -> None:
        service = PipelineRunContextService()

        context = service.build_context(
            pipeline_name="chembl_publication",
            run_id=RunID(UUID("00000000-0000-0000-0000-000000000123")),
            options=RunOptions(
                required_persistence_profile="degraded_observable",
            ),
            started_at=FIXED_STARTED_AT,
        )

        assert context.required_persistence_profile == "degraded_observable"

    def test_build_context_propagates_exact_replay(self) -> None:
        service = PipelineRunContextService()

        context = service.build_context(
            pipeline_name="chembl_activity",
            run_id=deterministic_run_uuid_from_callsite(
                "test_pipeline_run_context_service"
            ),
            options=RunOptions(
                use_cached_bronze=True,
                cached_bronze_path="bronze/cache",
                cached_bronze_date="2026-03-18",
                exact_replay=True,
            ),
            started_at=FIXED_STARTED_AT,
        )

        assert context.exact_replay is True
        assert context.has_cached_bronze is True

    def test_build_context_propagates_replay_parentage(self) -> None:
        service = PipelineRunContextService()

        context = service.build_context(
            pipeline_name="chembl_activity",
            run_id=deterministic_run_uuid_from_callsite(
                "test_pipeline_run_context_service"
            ),
            options=RunOptions(
                use_cached_bronze=True,
                cached_bronze_path="bronze/cache",
                cached_bronze_date="2026-03-18",
                replay_of_run_id="run-parent",
                replay_of_manifest_id="manifest-parent",
                exact_replay=True,
            ),
            started_at=FIXED_STARTED_AT,
        )

        assert context.replay_of_run_id == "run-parent"
        assert context.replay_of_manifest_id == "manifest-parent"

    def test_build_context_rejects_exact_replay_without_cached_bronze_or_parentage(
        self,
    ) -> None:
        service = PipelineRunContextService()

        with pytest.raises(
            ValueError,
            match="exact replay currently requires --use-cached-bronze or",
        ):
            service.build_context(
                pipeline_name="chembl_activity",
                run_id=deterministic_run_uuid_from_callsite(
                    "test_pipeline_run_context_service"
                ),
                options=RunOptions(exact_replay=True),
                started_at=FIXED_STARTED_AT,
            )

    def test_build_context_allows_exact_replay_with_replay_parentage_only(
        self,
    ) -> None:
        service = PipelineRunContextService()

        context = service.build_context(
            pipeline_name="chembl_activity",
            run_id=deterministic_run_uuid_from_callsite(
                "test_pipeline_run_context_service"
            ),
            options=RunOptions(
                replay_of_run_id=deterministic_uuid_string_from_callsite(
                    "test_pipeline_run_context_service"
                ),
                replay_of_manifest_id="manifest-parent",
                exact_replay=True,
            ),
            started_at=FIXED_STARTED_AT,
        )

        assert context.exact_replay is True
        assert context.has_cached_bronze is False
        assert context.replay_of_manifest_id == "manifest-parent"
