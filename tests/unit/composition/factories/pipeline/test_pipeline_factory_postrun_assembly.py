"""Unit tests for postrun composition helpers."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import ANY, MagicMock, patch

import pytest

from bioetl.application.core.postrun.cleanup_orchestrator import PostrunCleanupService
from bioetl.application.core.postrun.compact_orchestrator import PostrunCompactService
from bioetl.application.core.postrun.dq_report_orchestrator import (
    PostrunDQReportService,
)
from bioetl.application.core.postrun.metadata_write_service import (
    PostrunMetadataWriteService,
)
from bioetl.application.core.postrun.metadata_version_resolver import (
    PostrunMetadataVersionResolver,
)
from bioetl.application.core.postrun.service import (
    PostrunDependencyContext,
    PostrunService,
)
from bioetl.composition.bootstrap_contexts import DQConfigsContext
from bioetl.composition.factories.pipeline.postrun_assembly import (
    build_postrun_dependency_context,
    build_postrun_service,
)
from bioetl.domain.exceptions import BioETLError


def _make_pipeline() -> SimpleNamespace:
    """Create a minimal pipeline namespace for composition tests."""
    services = SimpleNamespace()
    services.dq_monitor = MagicMock()
    services.metrics = MagicMock()
    services.storage = MagicMock()
    services.dq_report_service = MagicMock()
    services.metadata_coordinator = MagicMock()
    services.metadata_writer = MagicMock()
    services.logger = MagicMock()
    services.tracing = MagicMock()
    services.bronze_dq_analyzer = None
    services.silver_dq_analyzer = None
    services.gold_dq_analyzer = None
    services.dq_report_writer = None

    config = SimpleNamespace(
        dq=MagicMock(),
        pipeline_name="chembl_activity",
        entity_type="activity",
    )
    return SimpleNamespace(
        config=config,
        runtime=MagicMock(),
        context=MagicMock(),
        services=services,
    )


@pytest.mark.unit
class TestBuildPostrunService:
    """Tests for build_postrun_service composition wiring."""

    def test_build_postrun_service_constructs_data_quality_service(self) -> None:
        """DataQualityService should be constructed from pipeline wiring."""
        pipeline = cast(Any, _make_pipeline())
        logger = MagicMock()
        lifecycle_service = MagicMock()
        dq_configs = DQConfigsContext(bronze=None, silver=None, gold=None)
        dq_service = MagicMock()
        dependencies = MagicMock(spec=PostrunDependencyContext)
        postrun_service = MagicMock(spec=PostrunService)

        with (
            patch(
                "bioetl.composition.factories.pipeline.postrun_assembly.DataQualityService",
                return_value=dq_service,
            ) as mock_dq_service_cls,
            patch(
                "bioetl.composition.factories.pipeline.postrun_assembly.build_postrun_dependency_context",
                return_value=dependencies,
            ) as mock_build_dependencies,
            patch(
                "bioetl.composition.factories.pipeline.postrun_assembly.PostrunService",
                return_value=postrun_service,
            ) as mock_postrun_service_cls,
        ):
            service = build_postrun_service(
                pipeline=pipeline,
                logger_port=logger,
                lifecycle_service=lifecycle_service,
                dq_configs=dq_configs,
            )

        assert service is postrun_service
        mock_dq_service_cls.assert_called_once_with(
            dq_monitor=pipeline.services.dq_monitor,
            config=pipeline.config.dq,
            logger=logger,
            metrics=pipeline.services.metrics,
            pipeline_name=pipeline.config.pipeline_name,
            entity_type=pipeline.config.entity_type,
            run_type=pipeline.runtime.run_type.value,
        )
        mock_build_dependencies.assert_called_once()
        mock_postrun_service_cls.assert_called_once_with(
            config=pipeline.config,
            runtime=pipeline.runtime,
            context=pipeline.context,
            dq_service=dq_service,
            lifecycle_service=lifecycle_service,
            dependencies=dependencies,
            services=pipeline.services,
            tracer=ANY,
        )

    def test_build_postrun_service_passes_outer_wiring_to_dependencies(self) -> None:
        """Dependency builder should receive pipeline services and DQ configs."""
        pipeline = cast(Any, _make_pipeline())
        logger = MagicMock()
        lifecycle_service = MagicMock()
        bronze_config = MagicMock()
        silver_config = MagicMock()
        gold_config = MagicMock()
        dq_configs = DQConfigsContext(
            bronze=bronze_config,
            silver=silver_config,
            gold=gold_config,
        )
        dependencies = MagicMock(spec=PostrunDependencyContext)
        postrun_service = MagicMock(spec=PostrunService)

        with (
            patch(
                "bioetl.composition.factories.pipeline.postrun_assembly.build_postrun_dependency_context",
                return_value=dependencies,
            ) as mock_build_dependencies,
            patch(
                "bioetl.composition.factories.pipeline.postrun_assembly.PostrunService",
                return_value=postrun_service,
            ) as mock_postrun_service_cls,
        ):
            service = build_postrun_service(
                pipeline=pipeline,
                logger_port=logger,
                lifecycle_service=lifecycle_service,
                dq_configs=dq_configs,
            )

        mock_build_dependencies.assert_called_once_with(
            config=pipeline.config,
            runtime=pipeline.runtime,
            context=pipeline.context,
            storage=pipeline.services.storage,
            logger_port=logger,
            dq_report_service=pipeline.services.dq_report_service,
            bronze_dq_config=bronze_config,
            silver_dq_config=silver_config,
            gold_dq_config=gold_config,
            metadata_coordinator=pipeline.services.metadata_coordinator,
            metadata_writer=pipeline.services.metadata_writer,
        )
        assert service is postrun_service
        mock_postrun_service_cls.assert_called_once()


@pytest.mark.unit
class TestBuildPostrunDependencyContext:
    """Tests for build_postrun_dependency_context wiring."""

    def test_build_postrun_dependency_context_returns_expected_collaborators(
        self,
    ) -> None:
        """The shared dependency builder should construct all postrun collaborators."""
        config = MagicMock()
        runtime = MagicMock()
        storage = MagicMock()
        logger = MagicMock()
        context = MagicMock()
        cleanup = MagicMock(spec=PostrunCleanupService)
        dq_report = MagicMock(spec=PostrunDQReportService)
        metadata_version = MagicMock(spec=PostrunMetadataVersionResolver)
        metadata_write = MagicMock(spec=PostrunMetadataWriteService)
        compact = MagicMock(spec=PostrunCompactService)

        with (
            patch(
                "bioetl.composition.factories.pipeline.postrun_assembly.PostrunCleanupService",
                return_value=cleanup,
            ),
            patch(
                "bioetl.composition.factories.pipeline.postrun_assembly.PostrunDQReportService",
                return_value=dq_report,
            ),
            patch(
                "bioetl.composition.factories.pipeline.postrun_assembly.PostrunMetadataVersionResolver",
                return_value=metadata_version,
            ),
            patch(
                "bioetl.composition.factories.pipeline.postrun_assembly.PostrunMetadataWriteService",
                return_value=metadata_write,
            ),
            patch(
                "bioetl.composition.factories.pipeline.postrun_assembly.PostrunCompactService",
                return_value=compact,
            ),
        ):
            dependencies = build_postrun_dependency_context(
                config=config,
                runtime=runtime,
                context=context,
                storage=storage,
                logger_port=logger,
            )

        assert isinstance(dependencies, PostrunDependencyContext)
        assert dependencies.cleanup_orchestrator is cleanup
        assert dependencies.dq_report_orchestrator is dq_report
        assert dependencies.metadata_write_orchestrator is metadata_write
        assert dependencies.compact_orchestrator is compact

    def test_build_postrun_dependency_context_propagates_inputs(self) -> None:
        """The shared dependency builder should wire runtime, configs, and allowlists."""
        config = MagicMock()
        runtime = MagicMock()
        context = MagicMock()
        storage = MagicMock()
        logger = MagicMock()
        dq_report_service = MagicMock()
        bronze_config = MagicMock()
        silver_config = MagicMock()
        gold_config = MagicMock()
        metadata_coordinator = MagicMock()
        metadata_writer = MagicMock()
        with (
            patch(
                "bioetl.composition.factories.pipeline.postrun_assembly.PostrunCleanupService",
            ) as mock_cleanup_cls,
            patch(
                "bioetl.composition.factories.pipeline.postrun_assembly.PostrunDQReportService",
            ) as mock_dq_report_cls,
            patch(
                "bioetl.composition.factories.pipeline.postrun_assembly.PostrunMetadataVersionResolver",
            ) as mock_metadata_cls,
            patch(
                "bioetl.composition.factories.pipeline.postrun_assembly.PostrunMetadataWriteService",
            ) as mock_metadata_write_cls,
            patch(
                "bioetl.composition.factories.pipeline.postrun_assembly.PostrunCompactService",
            ) as mock_compact_cls,
        ):
            build_postrun_dependency_context(
                config=config,
                runtime=runtime,
                context=context,
                storage=storage,
                logger_port=logger,
                dq_report_service=dq_report_service,
                bronze_dq_config=bronze_config,
                silver_dq_config=silver_config,
                gold_dq_config=gold_config,
                metadata_coordinator=metadata_coordinator,
                metadata_writer=metadata_writer,
            )

        cleanup_allowlist = mock_cleanup_cls.call_args.kwargs["warning_allowlist"]
        compact_allowlist = mock_compact_cls.call_args.kwargs["warning_allowlist"]
        assert mock_cleanup_cls.call_args.kwargs["logger"] is logger
        assert BioETLError in cleanup_allowlist
        assert mock_dq_report_cls.call_args.kwargs["logger"] is logger
        assert mock_dq_report_cls.call_args.kwargs["runtime"] is runtime
        assert (
            mock_dq_report_cls.call_args.kwargs["dq_report_service"]
            is dq_report_service
        )
        assert mock_dq_report_cls.call_args.kwargs["bronze_dq_config"] is bronze_config
        assert mock_dq_report_cls.call_args.kwargs["silver_dq_config"] is silver_config
        assert mock_dq_report_cls.call_args.kwargs["gold_dq_config"] is gold_config
        assert (
            mock_dq_report_cls.call_args.kwargs["warning_allowlist"]
            == cleanup_allowlist
        )
        assert mock_metadata_cls.call_args.kwargs["logger"] is logger
        assert mock_metadata_cls.call_args.kwargs["runtime"] is runtime
        assert mock_metadata_cls.call_args.kwargs["storage"] is storage
        metadata_allowlist = mock_metadata_cls.call_args.kwargs["warning_allowlist"]
        assert OSError in metadata_allowlist
        assert BioETLError not in metadata_allowlist
        assert mock_metadata_write_cls.call_args.kwargs["config"] is config
        assert mock_metadata_write_cls.call_args.kwargs["runtime"] is runtime
        assert mock_metadata_write_cls.call_args.kwargs["context"] is context
        assert mock_metadata_write_cls.call_args.kwargs["storage"] is storage
        assert (
            mock_metadata_write_cls.call_args.kwargs["metadata_coordinator"]
            is metadata_coordinator
        )
        assert (
            mock_metadata_write_cls.call_args.kwargs["metadata_writer"]
            is metadata_writer
        )
        assert (
            mock_metadata_write_cls.call_args.kwargs["metadata_version_resolver"]
            == mock_metadata_cls.return_value
        )
        assert mock_compact_cls.call_args.kwargs["config"] is config
        assert mock_compact_cls.call_args.kwargs["storage"] is storage
        assert mock_compact_cls.call_args.kwargs["logger"] is logger
        assert compact_allowlist == cleanup_allowlist
