"""Phased migration coordinator for composite pipelines."""

from __future__ import annotations

from collections.abc import Callable
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
    """Coordinator for phased migrations and backward compatibility."""

    def __init__(self) -> None:
        self._current_version = get_version()
        self._migration_phases = self._define_migration_phases()

    def _define_migration_phases(self) -> list[MigrationPhaseConfig]:
        return [
            MigrationPhaseConfig(
                phase_name="v1.0",
                start_version="1.0.0",
                end_version="1.2.0",
                backward_compatible=True,
                migration_strategy="immediate",
                fallback_behavior="warn",
            ),
            MigrationPhaseConfig(
                phase_name="v1.1",
                start_version="1.1.0",
                end_version="1.3.0",
                backward_compatible=True,
                migration_strategy="gradual",
                fallback_behavior="warn",
            ),
            MigrationPhaseConfig(
                phase_name="v1.2",
                start_version="1.2.0",
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
        if self._current_version in ("", "unknown", None):
            return self._migration_phases[-1].phase_name
        matching = [
            phase
            for phase in self._migration_phases
            if _phase_matches_version(
                self._current_version, phase, self._version_compare
            )
        ]
        return (
            matching[-1].phase_name
            if matching
            else self._migration_phases[-1].phase_name
        )

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
        guide = _empty_migration_guide()
        from_phase_config = self._find_phase(from_phase)
        to_phase_config = self._find_phase(to_phase)
        if from_phase_config is None or to_phase_config is None:
            guide["steps"].append("Invalid phase names provided")
            return guide
        if (
            self._version_compare(
                to_phase_config.start_version,
                from_phase_config.start_version,
            )
            > 0
        ):
            guide["steps"].append(
                f"Upgrade to version {to_phase_config.start_version} or later"
            )
        _extend_transition_guidance(guide, from_phase, to_phase)
        return guide

    def apply_migration_fallback(
        self,
        config: JsonDict,
        target_phase: str,
        fallback_behavior: Literal["warn", "error", "silent"] = "warn",
    ) -> tuple[JsonDict, list[str]]:
        """Apply compatibility defaults needed for an older target phase."""
        warnings: list[str] = []
        modified_config = config.copy()
        phase_config = self._find_phase(target_phase)
        if phase_config is None:
            warnings.append(f"Target phase {target_phase} not found")
            return modified_config, warnings
        _apply_phase_specific_fallback(modified_config, target_phase, warnings)
        if warnings and fallback_behavior == "error":
            raise ValueError(f"Migration fallback errors: {', '.join(warnings)}")
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


def _extend_transition_guidance(
    guide: dict[str, list[str]],
    from_phase: str,
    to_phase: str,
) -> None:
    transition = (from_phase, to_phase)
    if transition == ("v1.0", "v1.1"):
        guide["steps"].extend(
            [
                "Update composite validation configurations",
                "Review field priority settings",
                "Test cross-validation configurations",
            ]
        )
        guide["new_features"].append("Enhanced cross-validation governance")
        return
    if transition == ("v1.1", "v1.2"):
        guide["steps"].extend(
            [
                "Update to latest aggregation validator",
                "Review merged metadata explainability settings",
                "Test phased migration support",
            ]
        )
        guide["new_features"].extend(
            ["Merged metadata explainability", "Phased migration support"]
        )


def _apply_phase_specific_fallback(
    config: JsonDict,
    target_phase: str,
    warnings: list[str],
) -> None:
    if target_phase == "v1.0":
        _ensure_aggregation_provenance_tracking(config, warnings)
        return
    if target_phase == "v1.1":
        _ensure_cross_validation_strict_mode(config, warnings)


def _ensure_aggregation_provenance_tracking(
    config: JsonDict,
    warnings: list[str],
) -> None:
    aggregation = config.get("aggregation")
    if not isinstance(aggregation, dict) or "provenance_tracking" in aggregation:
        return
    aggregation["provenance_tracking"] = False
    warnings.append("Added missing provenance_tracking field with default value")


def _ensure_cross_validation_strict_mode(
    config: JsonDict,
    warnings: list[str],
) -> None:
    cross_validation = config.get("cross_validation")
    if not isinstance(cross_validation, dict) or "strict_mode" in cross_validation:
        return
    cross_validation["strict_mode"] = True
    warnings.append("Added missing strict_mode field with default value")


def create_phased_migration_support_service() -> PhasedMigrationCoordinator:
    """Factory function for the canonical phased migration coordinator."""
    return PhasedMigrationCoordinator()
