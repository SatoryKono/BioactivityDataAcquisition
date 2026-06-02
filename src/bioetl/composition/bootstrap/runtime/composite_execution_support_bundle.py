"""Execution-facing support bundle for composite runtime assembly."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.application.composite.runtime_wiring_api import (
        DependencyCoordinatorService,
        EnrichmentCoordinatorService,
        KeyExtractorService,
    )


@dataclass(slots=True)
class ExecutionSupportServicesBundle:
    """Execution-facing services shared across composite runtime phases."""

    key_extractor: KeyExtractorService
    dependency_coordinator: DependencyCoordinatorService
    coordinator: EnrichmentCoordinatorService


__all__ = ["ExecutionSupportServicesBundle"]
