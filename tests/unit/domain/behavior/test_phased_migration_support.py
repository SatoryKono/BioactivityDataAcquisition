"""Unit tests for phased migration support behavior."""

from __future__ import annotations

from copy import deepcopy

import pytest

from bioetl.domain.behavior.phased_migration_support import (
    PhasedMigrationCoordinator,
    _normalized_version_parts,
    _phase_matches_version,
    create_phased_migration_support_service,
)

pytestmark = pytest.mark.unit


def test_status_reports_stable_phase_and_current_version() -> None:
    coordinator = create_phased_migration_support_service()

    status = coordinator.get_current_migration_status()

    assert status.current_phase == "stable"
    assert status.supported_phases == ["stable"]
    assert isinstance(status.current_version, str)
    assert status.is_migration_mode is False
    assert status.migration_warnings == []


def test_version_compare_handles_padding_invalid_and_unknown_versions() -> None:
    coordinator = PhasedMigrationCoordinator()

    assert coordinator._version_compare("1.2", "1.2.0") == 0
    assert coordinator._version_compare("1.2.1", "1.2.0") == 1
    assert coordinator._version_compare("1.1.9", "1.2.0") == -1
    assert coordinator._version_compare("invalid", "1.2.0") == 0
    assert _normalized_version_parts("1.2", "1.2.3") == ([1, 2, 0], [1, 2, 3])


def test_phase_matching_respects_start_and_end_boundaries() -> None:
    coordinator = PhasedMigrationCoordinator()
    phase = coordinator._find_phase("stable")
    assert phase is not None

    assert _phase_matches_version("6.0.0", phase, coordinator._version_compare)
    assert _phase_matches_version("6.1.0", phase, coordinator._version_compare)
    assert not _phase_matches_version("5.9.9", phase, coordinator._version_compare)


def test_backward_compatibility_reports_retired_and_missing_phases() -> None:
    coordinator = PhasedMigrationCoordinator()

    assert coordinator.check_backward_compatibility({}, "v1.1") == {
        "phase_retired": (
            "Legacy phased migration phase v1.1 is retired; use the governed "
            "config compatibility registry instead"
        )
    }
    assert coordinator.check_backward_compatibility({}, "missing") == {
        "phase_not_found": "Phase missing not found"
    }


def test_migration_guide_marks_retired_phases_and_points_to_registry() -> None:
    coordinator = PhasedMigrationCoordinator()

    invalid = coordinator.get_migration_guide("missing", "stable")
    assert invalid["steps"] == ["Invalid phase names provided"]

    guide = coordinator.get_migration_guide("v1.0", "stable")
    assert "Legacy phased migration phase v1.0 is retired" in guide["steps"][0]
    assert "config_compatibility_registry.yaml" in guide["steps"][1]
    assert guide["new_features"] == ["Legacy v1.x phased runtime fallback retired"]


def test_apply_migration_fallback_is_retired_and_does_not_mutate_nested_payload() -> (
    None
):
    coordinator = PhasedMigrationCoordinator()
    config = {"aggregation": {"provenance_tracking": True}}
    original = deepcopy(config)

    updated, warnings = coordinator.apply_migration_fallback(config, "v1.0")

    assert updated == original
    assert updated is not config
    assert updated["aggregation"] is not config["aggregation"]
    assert warnings == [
        "Legacy phased migration phase v1.0 is retired; use the governed config "
        "compatibility registry instead"
    ]


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

    assert phases == [
        {
            "phase_name": "stable",
            "start_version": "6.0.0",
            "end_version": "current",
            "backward_compatible": "yes",
            "migration_strategy": "gradual",
        }
    ]
