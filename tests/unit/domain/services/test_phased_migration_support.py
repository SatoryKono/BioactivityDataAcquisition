"""Unit tests for PhasedMigrationCoordinator."""

from __future__ import annotations

from copy import deepcopy
from unittest.mock import patch

import pytest

from bioetl.domain.behavior.phased_migration_support import (
    MigrationPhaseConfig,
    MigrationStatus,
    PhasedMigrationCoordinator,
    create_phased_migration_support_service,
)

pytestmark = pytest.mark.unit


class TestPhasedMigrationCoordinator:
    """Tests for PhasedMigrationCoordinator."""

    @pytest.fixture
    def service(self) -> PhasedMigrationCoordinator:
        return PhasedMigrationCoordinator()

    def test_migration_phase_config_creation(self) -> None:
        config = MigrationPhaseConfig(
            phase_name="test_phase",
            start_version="1.0.0",
            end_version="2.0.0",
            backward_compatible=True,
            migration_strategy="gradual",
            fallback_behavior="warn",
        )

        assert config.phase_name == "test_phase"
        assert config.start_version == "1.0.0"
        assert config.end_version == "2.0.0"
        assert config.backward_compatible is True
        assert config.migration_strategy == "gradual"
        assert config.fallback_behavior == "warn"

    def test_migration_phase_config_current_phase(self) -> None:
        config = MigrationPhaseConfig(
            phase_name="current",
            start_version="2.0.0",
            end_version=None,
            backward_compatible=True,
        )

        assert config.end_version is None

    def test_get_current_migration_status(
        self, service: PhasedMigrationCoordinator
    ) -> None:
        status = service.get_current_migration_status()

        assert isinstance(status, MigrationStatus)
        assert status.current_phase == "stable"
        assert status.supported_phases == ["stable"]
        assert status.current_version is not None
        assert status.migration_warnings == []
        assert status.is_migration_mode is False

    def test_get_current_migration_status_specific_version(self) -> None:
        with patch(
            "bioetl.domain.behavior.phased_migration_support.get_version",
            return_value="6.1.0",
        ):
            service = PhasedMigrationCoordinator()
            status = service.get_current_migration_status()
            assert status.current_version == "6.1.0"
            assert status.current_phase == "stable"

    def test_get_current_migration_status_unknown_version(self) -> None:
        with patch(
            "bioetl.domain.behavior.phased_migration_support.get_version",
            return_value="unknown",
        ):
            service = PhasedMigrationCoordinator()
            status = service.get_current_migration_status()
            assert status.current_version == "unknown"
            assert status.current_phase == "stable"

    def test_check_backward_compatibility_current_phase(
        self, service: PhasedMigrationCoordinator
    ) -> None:
        issues = service.check_backward_compatibility({"test": "config"})
        assert issues == {}

    def test_check_backward_compatibility_retired_phase(
        self, service: PhasedMigrationCoordinator
    ) -> None:
        issues = service.check_backward_compatibility({"test": "config"}, "v1.2")

        assert issues == {
            "phase_retired": (
                "Legacy phased migration phase v1.2 is retired; use the governed "
                "config compatibility registry instead"
            )
        }

    def test_check_backward_compatibility_invalid_phase(
        self, service: PhasedMigrationCoordinator
    ) -> None:
        issues = service.check_backward_compatibility({"test": "config"}, "invalid")

        assert issues["phase_not_found"] == "Phase invalid not found"

    def test_get_migration_guide_same_phase(
        self, service: PhasedMigrationCoordinator
    ) -> None:
        guide = service.get_migration_guide("stable", "stable")

        assert guide == {
            "steps": [],
            "breaking_changes": [],
            "deprecations": [],
            "new_features": [],
        }

    def test_get_migration_guide_retired_phase_points_to_registry(
        self, service: PhasedMigrationCoordinator
    ) -> None:
        guide = service.get_migration_guide("v1.0", "stable")

        assert "Legacy phased migration phase v1.0 is retired" in guide["steps"][0]
        assert "config_compatibility_registry.yaml" in guide["steps"][1]
        assert guide["new_features"] == ["Legacy v1.x phased runtime fallback retired"]

    def test_get_migration_guide_invalid_phases(
        self, service: PhasedMigrationCoordinator
    ) -> None:
        guide = service.get_migration_guide("invalid_from", "invalid_to")
        assert guide["steps"] == ["Invalid phase names provided"]

    def test_apply_migration_fallback_retired_phase_is_noop_deep_copy(
        self, service: PhasedMigrationCoordinator
    ) -> None:
        config = {"aggregation": {"provenance_tracking": True}}
        original = deepcopy(config)

        modified_config, warnings = service.apply_migration_fallback(config, "v1.0")

        assert modified_config == original
        assert modified_config is not config
        assert modified_config["aggregation"] is not config["aggregation"]
        assert warnings == [
            "Legacy phased migration phase v1.0 is retired; use the governed "
            "config compatibility registry instead"
        ]

    def test_apply_migration_fallback_error_behavior(
        self, service: PhasedMigrationCoordinator
    ) -> None:
        with pytest.raises(ValueError) as exc_info:
            service.apply_migration_fallback({}, "v1.0", fallback_behavior="error")

        assert "Migration fallback errors" in str(exc_info.value)

    def test_apply_migration_fallback_silent_behavior(
        self, service: PhasedMigrationCoordinator
    ) -> None:
        modified_config, warnings = service.apply_migration_fallback(
            {"aggregation": {}},
            "v1.1",
            fallback_behavior="silent",
        )

        assert modified_config == {"aggregation": {}}
        assert warnings == [
            "Legacy phased migration phase v1.1 is retired; use the governed "
            "config compatibility registry instead"
        ]

    def test_apply_migration_fallback_invalid_phase(
        self, service: PhasedMigrationCoordinator
    ) -> None:
        config = {}
        modified_config, warnings = service.apply_migration_fallback(
            config, "invalid_phase"
        )

        assert modified_config == config
        assert len(warnings) == 1
        assert "Target phase invalid_phase not found" in warnings[0]

    def test_get_supported_phases(self, service: PhasedMigrationCoordinator) -> None:
        phases = service.get_supported_phases()

        assert phases == [
            {
                "phase_name": "stable",
                "start_version": "6.0.0",
                "end_version": "current",
                "backward_compatible": "yes",
                "migration_strategy": "gradual",
            }
        ]

    def test_version_comparison_equal(
        self, service: PhasedMigrationCoordinator
    ) -> None:
        assert service._version_compare("1.2.3", "1.2.3") == 0

    def test_version_comparison_greater(
        self, service: PhasedMigrationCoordinator
    ) -> None:
        assert service._version_compare("1.2.4", "1.2.3") == 1

    def test_version_comparison_less(self, service: PhasedMigrationCoordinator) -> None:
        assert service._version_compare("1.2.2", "1.2.3") == -1

    def test_version_comparison_major_difference(
        self, service: PhasedMigrationCoordinator
    ) -> None:
        assert service._version_compare("2.0.0", "1.2.3") == 1

    def test_version_comparison_minor_difference(
        self, service: PhasedMigrationCoordinator
    ) -> None:
        assert service._version_compare("1.3.0", "1.2.3") == 1

    def test_version_comparison_patch_difference(
        self, service: PhasedMigrationCoordinator
    ) -> None:
        assert service._version_compare("1.2.4", "1.2.3") == 1

    def test_version_comparison_different_lengths(
        self, service: PhasedMigrationCoordinator
    ) -> None:
        assert service._version_compare("1.2", "1.2.3") == -1

    def test_migration_coordinator__factory_function__be3763f8(self) -> None:
        service = create_phased_migration_support_service()
        assert isinstance(service, PhasedMigrationCoordinator)
