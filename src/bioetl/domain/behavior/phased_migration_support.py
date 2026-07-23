"""Deprecated compatibility facade for retired phased-migration runtime support.

The live v1.x phase-fallback engine is retired. Compatibility review lives in
``configs/quality/config_compatibility_registry.yaml``. This module preserves
the historical public import path with an explicit deprecation warning until
the next breaking release boundary.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Literal

__all__ = [
    "MigrationPhaseConfig",
    "MigrationStatus",
    "PhasedMigrationCoordinator",
]


def _warn_retired() -> None:
    warnings.warn(
        "bioetl.domain.behavior.phased_migration_support.PhasedMigrationCoordinator "
        "is a retired compatibility shim; use "
        "configs/quality/config_compatibility_registry.yaml for compatibility review. "
        "This symbol will be removed in a future breaking release.",
        DeprecationWarning,
        stacklevel=3,
    )


@dataclass(frozen=True, slots=True)
class MigrationPhaseConfig:
    """Historical migration-phase configuration payload (compatibility only)."""

    phase_name: str
    start_version: str
    end_version: str | None = None
    backward_compatible: bool = True
    migration_strategy: Literal["immediate", "gradual", "optional"] = "gradual"
    fallback_behavior: Literal["warn", "error", "silent"] = "warn"


@dataclass(frozen=True, slots=True)
class MigrationStatus:
    """Historical migration status payload (compatibility only)."""

    current_phase: str
    current_version: str
    supported_phases: tuple[str, ...]
    migration_warnings: tuple[str, ...]


class PhasedMigrationCoordinator:
    """Retired compatibility facade for historical phased-migration imports.

    Instantiation and method calls emit ``DeprecationWarning`` and do not mutate
    live configs. Prefer the static compatibility registry for new work.
    """

    def __init__(self) -> None:
        _warn_retired()

    def get_current_migration_status(self) -> MigrationStatus:
        """Return a static retired-status payload for compatibility callers."""
        return MigrationStatus(
            current_phase="retired",
            current_version="0.0.0",
            supported_phases=("retired",),
            migration_warnings=(
                "PhasedMigrationCoordinator runtime fallbacks are retired.",
            ),
        )

    def check_backward_compatibility(
        self,
        config: dict[str, object],
        target_phase: str | None = None,
    ) -> dict[str, object]:
        """Return a non-mutating compatibility report for legacy callers."""
        del config, target_phase
        return {
            "compatible": True,
            "retired": True,
            "message": (
                "Runtime phased-migration checks are retired; consult "
                "configs/quality/config_compatibility_registry.yaml."
            ),
        }
