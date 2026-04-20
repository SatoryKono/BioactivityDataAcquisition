"""Shared PostrunService test support helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.core.postrun.service import PostrunService
from bioetl.composition.factories.pipeline.postrun_assembly import (
    build_postrun_dependency_context,
)
from bioetl.domain.ports.noop import (
    NoOpMetrics,
    NoOpTracing,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


@dataclass(frozen=True)
class PostrunDependencyOverrides:
    """Optional dependency overrides for PostrunService test assembly."""

    metadata_coordinator: object | None = None
    metadata_writer: object | None = None
    dq_report_service: object | None = None
    bronze_dq_config: object | None = None
    silver_dq_config: object | None = None
    gold_dq_config: object | None = None


def build_test_postrun_service(
    *,
    config: object,
    runtime: object,
    context: object,
    dq_service: object,
    lifecycle_service: object,
    storage: object,
    logger: LoggerPort,
    metrics: object | None = None,
    tracer: object | None = None,
    metadata_coordinator: object | None = None,
    metadata_writer: object | None = None,
    dq_report_service: object | None = None,
    bronze_dq_config: object | None = None,
    silver_dq_config: object | None = None,
    gold_dq_config: object | None = None,
    overrides: PostrunDependencyOverrides | None = None,
) -> PostrunService:
    """Build PostrunService with explicit injected collaborators for tests.

    The helper accepts either a pre-built ``overrides`` bundle or direct keyword
    overrides for older tests that injected collaborators individually.
    """
    dependency_overrides = overrides or PostrunDependencyOverrides(
        metadata_coordinator=metadata_coordinator,
        metadata_writer=metadata_writer,
        dq_report_service=dq_report_service,
        bronze_dq_config=bronze_dq_config,
        silver_dq_config=silver_dq_config,
        gold_dq_config=gold_dq_config,
    )
    return PostrunService(
        config=config,
        runtime=runtime,
        context=context,
        dq_service=dq_service,
        lifecycle_service=lifecycle_service,
        storage=storage,
        metrics=metrics if metrics is not None else NoOpMetrics(warn_on_use=False),
        logger=logger,
        tracer=tracer if tracer is not None else NoOpTracing(),
        dependencies=build_postrun_dependency_context(
            config=config,
            runtime=runtime,
            context=context,
            storage=storage,
            logger_port=logger,
            dq_report_service=dependency_overrides.dq_report_service,
            bronze_dq_config=dependency_overrides.bronze_dq_config,
            silver_dq_config=dependency_overrides.silver_dq_config,
            gold_dq_config=dependency_overrides.gold_dq_config,
            metadata_coordinator=dependency_overrides.metadata_coordinator,
            metadata_writer=dependency_overrides.metadata_writer,
        ),
    )
