"""Phased migration coordinator for composite pipelines."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from typing import Literal

from bioetl.domain.types import JsonDict
from bioetl.domain.version import get_version


@dataclass(frozen=True)
class MigrationPhaseConfig:
    """Configuration for a migration phase."""

    phase_name: str
    start_version: str
    end_version: str | None = None
    backward_compatible: bool = True
    migration_strategy: Literal["immediate", "gradual", "optional"] = "gradual"
    fallback_behavior: Literal["warn", "error", "silent"] = "warn"


@dataclass(frozen=True)
class MigrationStatus:
    """Current migration status."""

    current_phase: str
    supported_phases: list[str]
    current_version: str
    migration_warnings: list[str]
    is_migration_mode: bool = False


class PhasedMigrationCoordinator:
    """Retired compatibility shim for phased-migration public API callers."""

    def __init__(self) -> None:
        self._current_version = get_version()
        self._migration_phases = self._define_migration_phases()

    def _define_migration_phases(self) -> list[MigrationPhaseConfig]:
        return [
            MigrationPhaseConfig(
                phase_name="stable",
                start_version="6.0.0",
                end_version=None,
                backward_compatible=True,
                migration_strategy="gradual",
                fallback_behavior="warn",
            ),
        ]

    def get_current_migration_status(self) -> MigrationStatus:
        """Return the active migration phase and any compatibility warnings."""
        current_phase = self._determine_current_phase()
        warnings: list[str] = []
        if self._has_migration_issues():
            warnings.append(f"Migration issues detected in phase {current_phase}")
        return MigrationStatus(
            current_phase=current_phase,
            supported_phases=[phase.phase_name for phase in self._migration_phases],
            current_version=self._current_version,
            migration_warnings=warnings,
            is_migration_mode=self._is_migration_mode(),
        )

    def _determine_current_phase(self) -> str:
        return self._migration_phases[-1].phase_name

    def _version_compare(self, v1: str, v2: str) -> int:
        """Compare two version strings (-1 if v1<v2, 0 if equal, 1 if v1>v2)."""
        try:
            v1_parts, v2_parts = _normalized_version_parts(v1, v2)
        except (ValueError, AttributeError):
            return 0
        if v1_parts < v2_parts:
            return -1
        if v1_parts > v2_parts:
            return 1
        return 0

    def _has_migration_issues(self) -> bool:
        return False

    def _is_migration_mode(self) -> bool:
        return False

    def check_backward_compatibility(
        self,
        _config: JsonDict,
        target_phase: str | None = None,
    ) -> dict[str, str]:
        """Report backward-compatibility issues for the target migration phase."""
        phase_name = target_phase or self._determine_current_phase()
        if phase_name in _RETIRED_PHASE_MESSAGES:
            return {"phase_retired": _RETIRED_PHASE_MESSAGES[phase_name]}
        phase_config = self._find_phase(phase_name)
        if phase_config is None:
            return {"phase_not_found": f"Phase {phase_name} not found"}
        if phase_config.backward_compatible:
            return {}
        return {
            "backward_compatibility": f"Phase {phase_name} is not backward compatible"
        }

    def get_migration_guide(
        self,
        from_phase: str,
        to_phase: str,
    ) -> dict[str, list[str]]:
        """Build transition guidance between two named migration phases."""
        retired_guide = _retired_phase_migration_guide(from_phase, to_phase)
        if retired_guide is not None:
            return retired_guide

        guide = _empty_migration_guide()
        from_phase_config = self._find_phase(from_phase)
        to_phase_config = self._find_phase(to_phase)
        if from_phase_config is None or to_phase_config is None:
            guide["steps"].append("Invalid phase names provided")
            return guide
        if _is_upgrade_transition(
            from_phase_config=from_phase_config,
            to_phase_config=to_phase_config,
            compare=self._version_compare,
        ):
            guide["steps"].append(
                f"Upgrade to version {to_phase_config.start_version} or later"
            )
        return guide

    def apply_migration_fallback(
        self,
        config: JsonDict,
        target_phase: str,
        fallback_behavior: Literal["warn", "error", "silent"] = "warn",
    ) -> tuple[JsonDict, list[str]]:
        """Apply compatibility defaults needed for an older target phase."""
        warnings: list[str] = []
        modified_config = deepcopy(config)
        if target_phase in _RETIRED_PHASE_MESSAGES:
            warnings.append(_RETIRED_PHASE_MESSAGES[target_phase])
            _raise_migration_fallback_errors(
                warnings=warnings,
                fallback_behavior=fallback_behavior,
            )
            return modified_config, warnings
        phase_config = self._find_phase(target_phase)
        if phase_config is None:
            warnings.append(f"Target phase {target_phase} not found")
            return modified_config, warnings
        _raise_migration_fallback_errors(
            warnings=warnings,
            fallback_behavior=fallback_behavior,
        )
        return modified_config, warnings

    def get_supported_phases(self) -> list[dict[str, str]]:
        """List supported migration phases in a CLI/report-friendly shape."""
        return [
            {
                "phase_name": phase.phase_name,
                "start_version": phase.start_version,
                "end_version": phase.end_version or "current",
                "backward_compatible": "yes" if phase.backward_compatible else "no",
                "migration_strategy": phase.migration_strategy,
            }
            for phase in self._migration_phases
        ]

    def _find_phase(self, phase_name: str) -> MigrationPhaseConfig | None:
        for phase in self._migration_phases:
            if phase.phase_name == phase_name:
                return phase
        return None


def _phase_matches_version(
    current_version: str,
    phase: MigrationPhaseConfig,
    compare: Callable[[str, str], int],
) -> bool:
    if compare(current_version, phase.start_version) < 0:
        return False
    if phase.end_version is None:
        return True
    return compare(current_version, phase.end_version) < 0


def _normalized_version_parts(v1: str, v2: str) -> tuple[list[int], list[int]]:
    v1_parts = [int(part) for part in v1.split(".")]
    v2_parts = [int(part) for part in v2.split(".")]
    max_len = max(len(v1_parts), len(v2_parts))
    v1_parts.extend([0] * (max_len - len(v1_parts)))
    v2_parts.extend([0] * (max_len - len(v2_parts)))
    return v1_parts, v2_parts


def _empty_migration_guide() -> dict[str, list[str]]:
    return {
        "steps": [],
        "breaking_changes": [],
        "deprecations": [],
        "new_features": [],
    }


def _retired_phase_migration_guide(
    from_phase: str,
    to_phase: str,
) -> dict[str, list[str]] | None:
    retired_message = _RETIRED_PHASE_MESSAGES.get(from_phase)
    if retired_message is None:
        return None

    guide = _empty_migration_guide()
    guide["steps"].append(retired_message)
    guide["steps"].append(
        "Use configs/quality/config_compatibility_registry.yaml for any "
        "remaining compatibility review instead of runtime phased fallbacks"
    )
    if to_phase == "stable":
        guide["new_features"].append("Legacy v1.x phased runtime fallback retired")
    return guide


def _is_upgrade_transition(
    *,
    from_phase_config: MigrationPhaseConfig,
    to_phase_config: MigrationPhaseConfig,
    compare: Callable[[str, str], int],
) -> bool:
    return compare(
        to_phase_config.start_version,
        from_phase_config.start_version,
    ) > 0


def _raise_migration_fallback_errors(
    *,
    warnings: list[str],
    fallback_behavior: Literal["warn", "error", "silent"],
) -> None:
    if warnings and fallback_behavior == "error":
        raise ValueError(f"Migration fallback errors: {', '.join(warnings)}")

_RETIRED_PHASE_MESSAGES = {
    "v1.0": "Legacy phased migration phase v1.0 is retired; use the governed config compatibility registry instead",
    "v1.1": "Legacy phased migration phase v1.1 is retired; use the governed config compatibility registry instead",
    "v1.2": "Legacy phased migration phase v1.2 is retired; use the governed config compatibility registry instead",
}


def create_phased_migration_support_service() -> PhasedMigrationCoordinator:
    """Factory function for the canonical phased migration coordinator."""
    return PhasedMigrationCoordinator()
