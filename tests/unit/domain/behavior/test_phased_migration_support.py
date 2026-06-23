"""Unit tests for phased migration support behavior."""

from __future__ import annotations

import pytest

from bioetl.domain.behavior.phased_migration_support import (
    PhasedMigrationCoordinator,
    _normalized_version_parts,
    _phase_matches_version,
    create_phased_migration_support_service,
)

pytestmark = pytest.mark.unit


def test_status_lists_supported_phases_and_current_version() -> None:
    coordinator = create_phased_migration_support_service()

    status = coordinator.get_current_migration_status()

    assert status.current_phase in {"v1.0", "v1.1", "v1.2"}
    assert status.supported_phases == ["v1.0", "v1.1", "v1.2"]
    assert isinstance(status.current_version, str)
    assert status.is_migration_mode is False


def test_version_compare_handles_padding_invalid_and_unknown_versions() -> None:
    coordinator = PhasedMigrationCoordinator()

    assert coordinator._version_compare("1.2", "1.2.0") == 0
    assert coordinator._version_compare("1.2.1", "1.2.0") == 1
    assert coordinator._version_compare("1.1.9", "1.2.0") == -1
    assert coordinator._version_compare("invalid", "1.2.0") == 0
    assert _normalized_version_parts("1.2", "1.2.3") == ([1, 2, 0], [1, 2, 3])


def test_phase_matching_respects_start_and_end_boundaries() -> None:
    coordinator = PhasedMigrationCoordinator()
    phase = coordinator._find_phase("v1.1")
    assert phase is not None

    assert _phase_matches_version("1.1.0", phase, coordinator._version_compare)
    assert _phase_matches_version("1.2.9", phase, coordinator._version_compare)
    assert not _phase_matches_version("1.3.0", phase, coordinator._version_compare)
    assert not _phase_matches_version("1.0.9", phase, coordinator._version_compare)


def test_backward_compatibility_reports_unknown_and_non_compatible_phases() -> None:
    coordinator = PhasedMigrationCoordinator()

    assert coordinator.check_backward_compatibility({}, "missing") == {
        "phase_not_found": "Phase missing not found"
    }

    # Replace phases locally to cover the non-backward-compatible branch.
    phase = coordinator._migration_phases[0]
    coordinator._migration_phases = [
        type(phase)(
            phase_name="breaking",
            start_version="9.0.0",
            backward_compatible=False,
        )
    ]
    assert coordinator.check_backward_compatibility({}, "breaking") == {
        "backward_compatibility": "Phase breaking is not backward compatible"
    }


def test_migration_guide_covers_invalid_and_known_transitions() -> None:
    coordinator = PhasedMigrationCoordinator()

    invalid = coordinator.get_migration_guide("v1.0", "missing")
    assert invalid["steps"] == ["Invalid phase names provided"]

    guide = coordinator.get_migration_guide("v1.0", "v1.1")
    assert "Upgrade to version 1.1.0 or later" in guide["steps"]
    assert "Enhanced cross-validation governance" in guide["new_features"]

    guide = coordinator.get_migration_guide("v1.1", "v1.2")
    assert "Merged metadata explainability" in guide["new_features"]
    assert "Phased migration support" in guide["new_features"]


def test_apply_migration_fallback_adds_phase_specific_defaults() -> None:
    coordinator = PhasedMigrationCoordinator()

    updated, warnings = coordinator.apply_migration_fallback(
        {"aggregation": {}, "cross_validation": {}},
        "v1.0",
    )
    assert updated["aggregation"]["provenance_tracking"] is False
    assert warnings == ["Added missing provenance_tracking field with default value"]

    updated, warnings = coordinator.apply_migration_fallback(
        {"cross_validation": {}},
        "v1.1",
    )
    assert updated["cross_validation"]["strict_mode"] is True
    assert warnings == ["Added missing strict_mode field with default value"]


def test_apply_migration_fallback_reports_missing_phase_and_error_mode() -> None:
    coordinator = PhasedMigrationCoordinator()

    unchanged, warnings = coordinator.apply_migration_fallback({"x": 1}, "missing")
    assert unchanged == {"x": 1}
    assert warnings == ["Target phase missing not found"]

    with pytest.raises(ValueError, match="Migration fallback errors"):
        coordinator.apply_migration_fallback(
            {"aggregation": {}},
            "v1.0",
            fallback_behavior="error",
        )


def test_supported_phases_are_report_friendly() -> None:
    phases = PhasedMigrationCoordinator().get_supported_phases()

    assert phases[0]["phase_name"] == "v1.0"
    assert phases[-1]["end_version"] == "current"
    assert phases[-1]["backward_compatible"] == "yes"
