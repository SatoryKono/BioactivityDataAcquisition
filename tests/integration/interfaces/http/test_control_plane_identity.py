"""Integration tests for HTTP control-plane identity specs.

Tests control-plane identity anchor specifications and HTTP contract compliance.
"""

from __future__ import annotations


import pytest


@pytest.mark.integration
class TestControlPlaneIdentitySpecs:
    """Integration tests for control-plane identity specifications.

    Tests P0/P1/P2 anchor specs and HTTP contract compliance.
    """

    def test_p0_anchor_specs_defined(self) -> None:
        """Test P0 anchor specifications are defined."""
        from bioetl.interfaces.http.control_plane_identity.p0_specs import (
            P0_ANCHOR_SPECS,
        )

        # Verify P0 specs exist
        assert P0_ANCHOR_SPECS is not None
        assert len(P0_ANCHOR_SPECS) > 0

        # Verify each spec has required fields
        for spec in P0_ANCHOR_SPECS:
            assert spec.priority == "P0"
            assert spec.anchor_name is not None
            assert spec.display_name is not None
            assert spec.source_location is not None
            assert spec.data_type is not None
            assert spec.description is not None
            assert spec.display_mode is not None
            assert spec.is_identifier is not None
            assert spec.usage_locations is not None
            assert spec.implementation_status is not None

    def test_p1_anchor_specs_defined(self) -> None:
        """Test P1 anchor specifications are defined."""
        from bioetl.interfaces.http.control_plane_identity.p1_specs import (
            P1_ANCHOR_SPECS,
        )

        # Verify P1 specs exist
        assert P1_ANCHOR_SPECS is not None
        assert len(P1_ANCHOR_SPECS) > 0

        # Verify each spec has required fields
        for spec in P1_ANCHOR_SPECS:
            assert spec.priority == "P1"
            assert spec.anchor_name is not None
            assert spec.display_name is not None

    def test_p2_anchor_specs_defined(self) -> None:
        """Test P2 anchor specifications are defined."""
        from bioetl.interfaces.http.control_plane_identity.p2_specs import (
            P2_ANCHOR_SPECS,
        )

        # Verify P2 specs exist
        assert P2_ANCHOR_SPECS is not None
        assert len(P2_ANCHOR_SPECS) > 0

        # Verify each spec has required fields
        for spec in P2_ANCHOR_SPECS:
            assert spec.priority == "P2"
            assert spec.anchor_name is not None
            assert spec.display_name is not None

    def test_anchor_spec_constants(self) -> None:
        """Test anchor spec constants are defined."""
        from bioetl.interfaces.http.control_plane_identity.spec_constants import (
            ANCHOR_SPEC_VERSION,
            SPEC_VALIDATION_RULES,
        )

        # Verify spec version
        assert ANCHOR_SPEC_VERSION is not None
        assert isinstance(ANCHOR_SPEC_VERSION, str)

        # Verify validation rules exist
        assert SPEC_VALIDATION_RULES is not None
        assert len(SPEC_VALIDATION_RULES) > 0

    def test_anchor_values_extractor(self) -> None:
        """Test anchor values extraction from control-plane artifacts."""
        from bioetl.interfaces.http.control_plane_identity.anchor_values import (
            AnchorValues,
        )
        from bioetl.interfaces.http.control_plane_identity.types import (
            AnchorSpec,
        )

        # Create sample anchor spec
        spec = AnchorSpec(
            priority="P0",
            anchor_name="run_id",
            display_name="Run ID",
            source_location="RunManifest.run_id",
            data_type="UUID v4",
            description="Primary correlation anchor",
            display_mode="overview: short; details: full",
            is_identifier=True,
            usage_locations="Manifest JSON; ledger",
            implementation_status="SHIPPED",
        )

        # Create anchor values
        values = AnchorValues(
            spec=spec,
            value="test-run-123",
            source="manifest",
        )

        assert values.spec.anchor_name == "run_id"
        assert values.value == "test-run-123"
        assert values.source == "manifest"

    def test_manifest_extractor(self) -> None:
        """Test manifest anchor extraction."""
        from bioetl.interfaces.http.control_plane_identity.manifest_extractors import (
            extract_manifest_anchors,
        )

        # Create sample manifest data
        manifest_data = {
            "run_id": "test-run-123",
            "manifest_id": "manifest-456",
            "pipeline_name": "test_pipeline",
            "provider": "test_provider",
            "entity": "test_entity",
        }

        # Extract anchors
        anchors = extract_manifest_anchors(manifest_data)

        # Verify anchor extraction
        assert anchors is not None
        assert len(anchors) > 0

        # Verify required anchors are present
        anchor_names = [anchor.spec.anchor_name for anchor in anchors]
        assert "run_id" in anchor_names
        assert "manifest_id" in anchor_names

    def test_ledger_extractor(self) -> None:
        """Test ledger anchor extraction."""
        from bioetl.interfaces.http.control_plane_identity.ledger_extractors import (
            extract_ledger_anchors,
        )

        # Create sample ledger event
        ledger_event = {
            "event_type": "test_event",
            "run_id": "test-run-123",
            "timestamp": "2024-01-01T00:00:00Z",
            "data": {},
        }

        # Extract anchors
        anchors = extract_ledger_anchors(ledger_event)

        # Verify anchor extraction
        assert anchors is not None
        assert len(anchors) > 0

        # Verify run_id anchor is present
        anchor_names = [anchor.spec.anchor_name for anchor in anchors]
        assert "run_id" in anchor_names

    def test_checkpoint_extractor(self) -> None:
        """Test checkpoint anchor extraction."""
        from bioetl.interfaces.http.control_plane_identity.checkpoint_extractors import (
            extract_checkpoint_anchors,
        )

        # Create sample checkpoint data
        checkpoint_data = {
            "checkpoint_id": "checkpoint-789",
            "run_id": "test-run-123",
            "timestamp": "2024-01-01T00:00:00Z",
            "state": {},
        }

        # Extract anchors
        anchors = extract_checkpoint_anchors(checkpoint_data)

        # Verify anchor extraction
        assert anchors is not None
        assert len(anchors) > 0

    def test_payload_validation(self) -> None:
        """Test payload validation for HTTP identity specs."""
        from bioetl.interfaces.http.control_plane_identity.payload import (
            validate_identity_payload,
        )

        # Create valid payload
        valid_payload = {
            "run_id": "test-run-123",
            "manifest_id": "manifest-456",
            "pipeline_name": "test_pipeline",
        }

        # Validate payload
        is_valid, errors = validate_identity_payload(valid_payload)

        # Verify validation
        assert is_valid is True
        assert len(errors) == 0

    def test_source_model_compatibility(self) -> None:
        """Test source model compatibility with HTTP identity specs."""
        from bioetl.interfaces.http.control_plane_identity.source_model import (
            ControlPlaneSourceModel,
        )

        # Create source model
        model = ControlPlaneSourceModel(
            run_id="test-run-123",
            manifest_id="manifest-456",
            pipeline_name="test_pipeline",
            provider="test_provider",
            entity="test_entity",
        )

        # Verify model fields
        assert model.run_id == "test-run-123"
        assert model.manifest_id == "manifest-456"
        assert model.pipeline_name == "test_pipeline"

    def test_identity_spec_versioning(self) -> None:
        """Test identity spec versioning and compatibility."""
        from bioetl.interfaces.http.control_plane_identity.specs import (
            get_current_spec_version,
            is_spec_version_compatible,
        )

        # Get current spec version
        current_version = get_current_spec_version()

        # Verify version format
        assert current_version is not None
        assert isinstance(current_version, str)

        # Test compatibility check
        is_compatible = is_spec_version_compatible(current_version)
        assert is_compatible is True


@pytest.mark.unit
class TestIdentityContractTests:
    """Contract tests for HTTP control-plane identity specifications."""

    def test_run_id_format_validation(self) -> None:
        """Test run_id format validation."""
        from bioetl.interfaces.http.control_plane_identity.formatting import (
            validate_run_id_format,
        )

        # Valid run_id (UUID-like)
        valid_run_id = "550e8400-e29b-41d4-a716-446655440000"
        is_valid = validate_run_id_format(valid_run_id)
        assert is_valid is True

        # Invalid run_id
        invalid_run_id = "not-a-uuid"
        is_valid = validate_run_id_format(invalid_run_id)
        assert is_valid is False

    def test_manifest_id_format_validation(self) -> None:
        """Test manifest_id format validation."""
        from bioetl.interfaces.http.control_plane_identity.formatting import (
            validate_manifest_id_format,
        )

        # Valid manifest_id
        valid_manifest_id = "manifest-1234567890"
        is_valid = validate_manifest_id_format(valid_manifest_id)
        assert is_valid is True

    def test_provider_entity_format_validation(self) -> None:
        """Test provider.entity format validation."""
        from bioetl.interfaces.http.control_plane_identity.formatting import (
            validate_provider_entity_format,
        )

        # Valid provider.entity
        valid_provider_entity = "chembl.activity"
        is_valid = validate_provider_entity_format(valid_provider_entity)
        assert is_valid is True

        # Invalid provider.entity
        invalid_provider_entity = "invalid-format"
        is_valid = validate_provider_entity_format(invalid_provider_entity)
        assert is_valid is False

    def test_anchor_spec_completeness(self) -> None:
        """Test anchor specs cover all required control-plane artifacts."""
        from bioetl.interfaces.http.control_plane_identity.p0_specs import (
            P0_ANCHOR_SPECS,
        )

        # Verify required anchors are present
        required_anchors = [
            "run_id",
            "manifest_id",
            "pipeline_name",
            "provider_entity",
        ]

        anchor_names = [spec.anchor_name for spec in P0_ANCHOR_SPECS]
        for required_anchor in required_anchors:
            assert required_anchor in anchor_names, (
                f"Missing required anchor: {required_anchor}"
            )

    def test_implementation_status_tracking(self) -> None:
        """Test implementation status tracking for anchor specs."""
        from bioetl.interfaces.http.control_plane_identity.p0_specs import (
            P0_ANCHOR_SPECS,
        )

        # Verify implementation status values are valid
        valid_statuses = ["SHIPPED", "DEGRADED", "FAILING", "PLANNED"]

        for spec in P0_ANCHOR_SPECS:
            assert spec.implementation_status in valid_statuses, (
                f"Invalid implementation status for {spec.anchor_name}: {spec.implementation_status}"
            )

    def test_anchor_spec_mutability(self) -> None:
        """Test anchor specs are immutable (frozen)."""
        from bioetl.interfaces.http.control_plane_identity.types import (
            AnchorSpec,
        )

        # Create a spec
        spec = AnchorSpec(
            priority="P0",
            anchor_name="test_anchor",
            display_name="Test Anchor",
            source_location="Test Location",
            data_type="string",
            description="Test description",
            display_mode="full",
            is_identifier=True,
            usage_locations="Test usage",
            implementation_status="SHIPPED",
        )

        # Verify spec is frozen (immutable)
        try:
            spec.anchor_name = "modified_anchor"
            assert False, "AnchorSpec should be immutable"
        except (AttributeError, TypeError):
            # Expected behavior - spec is immutable
            pass
