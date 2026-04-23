"""Execution-support builders for composite runtime composition."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.composite.runtime_wiring_api import (
    JOIN_KEY_NORMALIZATION_POLICIES,
    DependencyCoordinatorService,
    DependencyProgressService,
    DependencyResultService,
    EnrichmentCoordinatorService,
    KeyExtractorService,
    create_chained_key_resolver,
    create_seed_key_resolver,
    validate_join_key_normalization_policies,
)
from bioetl.composition.bootstrap.runtime.composite_support_service_bundles import (
    ExecutionSupportServicesBundle,
)

if TYPE_CHECKING:
    from bioetl.domain.composite.config import CompositeConfig
    from bioetl.domain.ports import ClockPort, LoggerPort
    from bioetl.infrastructure.storage.delta_reader import DeltaReader


def build_execution_support_services(
    *,
    config: CompositeConfig,
    logger: LoggerPort,
    delta_reader: DeltaReader,
    clock: ClockPort | None = None,
) -> ExecutionSupportServicesBundle:
    """Build execution-facing support services shared across runtime stages."""
    validate_join_key_normalization_policies(config)
    return ExecutionSupportServicesBundle(
        key_extractor=KeyExtractorService(
            delta_reader=delta_reader,
            logger=logger,
            normalization_policies=JOIN_KEY_NORMALIZATION_POLICIES,
        ),
        dependency_coordinator=DependencyCoordinatorService(
            logger=logger,
            seed_key_resolver=create_seed_key_resolver(
                logger,
                normalization_policies=JOIN_KEY_NORMALIZATION_POLICIES,
            ),
            chained_key_resolver=create_chained_key_resolver(
                logger,
                normalization_policies=JOIN_KEY_NORMALIZATION_POLICIES,
            ),
            progress_service=DependencyProgressService(logger),
            result_service=DependencyResultService(logger),
            delta_reader=delta_reader,
            clock=clock,
        ),
        coordinator=EnrichmentCoordinatorService(
            logger=logger,
            dq_config=config.dq,
            max_concurrency=config.execution.max_concurrency,
            clock=clock,
        ),
    )


__all__ = ["build_execution_support_services"]
