"""Unit tests for PhasedMigrationCoordinator."""

from __future__ import annotations

import pytest
from unittest.mock import patch

from bioetl.domain.behavior.phased_migration_support import (
    MigrationPhaseConfig,
    MigrationStatus,
    PhasedMigrationCoordinator,
)


class TestPhasedMigrationCoordinator:
    """Tests for PhasedMigrationCoordinator."""

    @pytest.fixture
    def service(self) -> PhasedMigrationCoordinator:
        """Create a PhasedMigrationCoordinator instance."""
        return PhasedMigrationCoordinator()

    # ==========================================================================
    # MigrationPhaseConfig tests
    # ==========================================================================

    def test_migration_phase_config_creation(self) -> None:
        """Test creation of MigrationPhaseConfig."""
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
        """Test creation of current phase (no end version)."""
        config = MigrationPhaseConfig(
            phase_name="current",
            start_version="2.0.0",
            end_version=None,  # Current phase
            backward_compatible=True,
        )

        assert config.end_version is None

    # ==========================================================================
    # get_current_migration_status() tests
    # ==========================================================================

    def test_get_current_migration_status(
        self, service: PhasedMigrationCoordinator
    ) -> None:
        """Test getting current migration status."""
        status = service.get_current_migration_status()

        assert isinstance(status, MigrationStatus)
        assert status.current_phase in ["v1.0", "v1.1", "v1.2"]
        assert len(status.supported_phases) == 3
        assert status.current_version is not None
        assert isinstance(status.migration_warnings, list)
        assert isinstance(status.is_migration_mode, bool)

    def test_get_current_migration_status_specific_version(self) -> None:
        """Test migration status with specific version."""
        with patch(
            "bioetl.domain.behavior.phased_migration_support.get_version",
            return_value="1.1.5",
        ):
            service = PhasedMigrationCoordinator()
            status = service.get_current_migration_status()
            assert status.current_version == "1.1.5"
            assert status.current_phase == "v1.1"

    def test_get_current_migration_status_unknown_version(self) -> None:
        """Test migration status with unknown version."""
        with patch(
            "bioetl.domain.behavior.phased_migration_support.get_version",
            return_value="unknown",
        ):
            service = PhasedMigrationCoordinator()
            status = service.get_current_migration_status()
            assert status.current_version == "unknown"
            # Should default to latest phase
            assert status.current_phase == "v1.2"

    # ==========================================================================
    # check_backward_compatibility() tests
    # ==========================================================================

    def test_check_backward_compatibility_current_phase(
        self, service: PhasedMigrationCoordinator
    ) -> None:
        """Test backward compatibility check for current phase."""
        config = {"test": "config"}
        issues = service.check_backward_compatibility(config)

        # Should have no issues for current phase
        assert issues == {}

    def test_check_backward_compatibility_invalid_phase(
        self, service: PhasedMigrationCoordinator
    ) -> None:
        """Test backward compatibility check with invalid phase."""
        config = {"test": "config"}
        issues = service.check_backward_compatibility(config, "invalid_phase")

        assert "phase_not_found" in issues
        assert issues["phase_not_found"] == "Phase invalid_phase not found"

    # ==========================================================================
    # get_migration_guide() tests
    # ==========================================================================

    def test_get_migration_guide_same_phase(
        self, service: PhasedMigrationCoordinator
    ) -> None:
        """Test migration guide for same phase."""
        guide = service.get_migration_guide("v1.1", "v1.1")

        assert "steps" in guide
        assert "breaking_changes" in guide
        assert "deprecations" in guide
        assert "new_features" in guide

    def test_get_migration_guide_v1_0_to_v1_1(
        self, service: PhasedMigrationCoordinator
    ) -> None:
        """Test migration guide from v1.0 to v1.1."""
        guide = service.get_migration_guide("v1.0", "v1.1")

        assert any("Upgrade to version 1.1.0" in step for step in guide["steps"])
        assert "Enhanced cross-validation governance" in guide["new_features"]

    def test_get_migration_guide_v1_1_to_v1_2(
        self, service: PhasedMigrationCoordinator
    ) -> None:
        """Test migration guide from v1.1 to v1.2."""
        guide = service.get_migration_guide("v1.1", "v1.2")

        assert any("Upgrade to version 1.2.0" in step for step in guide["steps"])
        assert "Merged metadata explainability" in guide["new_features"]
        assert "Phased migration support" in guide["new_features"]

    def test_get_migration_guide_invalid_phases(
        self, service: PhasedMigrationCoordinator
    ) -> None:
        """Test migration guide with invalid phase names."""
        guide = service.get_migration_guide("invalid_from", "invalid_to")

        assert "Invalid phase names provided" in guide["steps"]

    # ==========================================================================
    # apply_migration_fallback() tests
    # ==========================================================================

    def test_apply_migration_fallback_v1_0(
        self, service: PhasedMigrationCoordinator
    ) -> None:
        """Test migration fallback to v1.0."""
        config = {"aggregation": {}}
        modified_config, warnings = service.apply_migration_fallback(config, "v1.0")

        assert "provenance_tracking" in modified_config["aggregation"]
        assert modified_config["aggregation"]["provenance_tracking"] is False
        assert len(warnings) == 1
        assert "Added missing provenance_tracking field" in warnings[0]

    def test_apply_migration_fallback_v1_1(
        self, service: PhasedMigrationCoordinator
    ) -> None:
        """Test migration fallback to v1.1."""
        config = {"cross_validation": {}}
        modified_config, warnings = service.apply_migration_fallback(config, "v1.1")

        assert "strict_mode" in modified_config["cross_validation"]
        assert modified_config["cross_validation"]["strict_mode"] is True
        assert len(warnings) == 1
        assert "Added missing strict_mode field" in warnings[0]

    def test_apply_migration_fallback_error_behavior(
        self, service: PhasedMigrationCoordinator
    ) -> None:
        """Test migration fallback with error behavior."""
        config = {"aggregation": {}}

        with pytest.raises(ValueError) as exc_info:
            service.apply_migration_fallback(config, "v1.0", fallback_behavior="error")

        assert "Migration fallback errors" in str(exc_info.value)

    def test_apply_migration_fallback_silent_behavior(
        self, service: PhasedMigrationCoordinator
    ) -> None:
        """Test migration fallback with silent behavior."""
        config = {"aggregation": {}}
        modified_config, warnings = service.apply_migration_fallback(
            config, "v1.0", fallback_behavior="silent"
        )

        assert "provenance_tracking" in modified_config["aggregation"]
        assert len(warnings) == 1  # Still collects warnings, just doesn't raise error

    def test_apply_migration_fallback_invalid_phase(
        self, service: PhasedMigrationCoordinator
    ) -> None:
        """Test migration fallback with invalid phase."""
        config = {}
        modified_config, warnings = service.apply_migration_fallback(
            config, "invalid_phase"
        )

        assert modified_config == config  # Should not modify config
        assert len(warnings) == 1
        assert "Target phase invalid_phase not found" in warnings[0]

    # ==========================================================================
    # get_supported_phases() tests
    # ==========================================================================

    def test_get_supported_phases(self, service: PhasedMigrationCoordinator) -> None:
        """Test getting list of supported phases."""
        phases = service.get_supported_phases()

        assert len(phases) == 3
        assert all("phase_name" in phase for phase in phases)
        assert all("start_version" in phase for phase in phases)
        assert all("end_version" in phase for phase in phases)
        assert all("backward_compatible" in phase for phase in phases)
        assert all("migration_strategy" in phase for phase in phases)

    # ==========================================================================
    # Version comparison tests
    # ==========================================================================

    def test_version_comparison_equal(
        self, service: PhasedMigrationCoordinator
    ) -> None:
        """Test version comparison for equal versions."""
        result = service._version_compare("1.2.3", "1.2.3")
        assert result == 0

    def test_version_comparison_greater(
        self, service: PhasedMigrationCoordinator
    ) -> None:
        """Test version comparison for greater version."""
        result = service._version_compare("1.2.4", "1.2.3")
        assert result == 1

    def test_version_comparison_less(self, service: PhasedMigrationCoordinator) -> None:
        """Test version comparison for lesser version."""
        result = service._version_compare("1.2.2", "1.2.3")
        assert result == -1

    def test_version_comparison_major_difference(
        self, service: PhasedMigrationCoordinator
    ) -> None:
        """Test version comparison for major version difference."""
        result = service._version_compare("2.0.0", "1.2.3")
        assert result == 1

    def test_version_comparison_minor_difference(
        self, service: PhasedMigrationCoordinator
    ) -> None:
        """Test version comparison for minor version difference."""
        result = service._version_compare("1.3.0", "1.2.3")
        assert result == 1

    def test_version_comparison_patch_difference(
        self, service: PhasedMigrationCoordinator
    ) -> None:
        """Test version comparison for patch version difference."""
        result = service._version_compare("1.2.4", "1.2.3")
        assert result == 1

    def test_version_comparison_different_lengths(
        self, service: PhasedMigrationCoordinator
    ) -> None:
        """Test version comparison for versions with different lengths."""
        result = service._version_compare("1.2", "1.2.3")
        assert result == -1  # 1.2 (1.2.0) is less than 1.2.3

    # ==========================================================================
    # Factory function test
    # ==========================================================================

    def test_factory_function(self) -> None:
        """Test the factory function."""
        service = create_phased_migration_support_service()
        assert isinstance(service, PhasedMigrationCoordinator)


# Helper function for easier testing


def create_phased_migration_support_service() -> PhasedMigrationCoordinator:
    """Factory function for PhasedMigrationCoordinator."""
    return PhasedMigrationCoordinator()
