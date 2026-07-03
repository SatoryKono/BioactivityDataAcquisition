"""Tests for contract identity model."""

import pytest

from bioetl.domain.types.contract_identity import (
    CompatibilityLevel,
    ContractIdentity,
    ContractProvenance,
    DQContractCompatibility,
    LifecycleStatus,
)
from tests.helpers.clock import FIXED_TEST_TIME


pytestmark = pytest.mark.unit


def _utcnow_iso() -> str:
    """Return an aware UTC timestamp string for test fixtures."""
    return FIXED_TEST_TIME.isoformat()


class TestContractIdentity:
    """Test contract identity creation and validation."""

    def test_contract_identity_creation(self):
        """Test basic contract identity creation."""
        identity = ContractIdentity(
            contract_ref="chembl.molecule.v1",
            contract_version="1.0.0",
            compatibility_level=CompatibilityLevel.MAJOR,
            schema_hash="a" * 64,  # Valid SHA256 hash
            dq_policy_ref="chembl.dq.v1",
            rule_bundle_version="dq-rules.v1",
        )

        assert identity.contract_ref == "chembl.molecule.v1"
        assert identity.contract_version == "1.0.0"
        assert identity.compatibility_level == CompatibilityLevel.MAJOR
        assert identity.dq_policy_ref == "chembl.dq.v1"
        assert identity.rule_bundle_version == "dq-rules.v1"

    def test_contract_identity_validation(self):
        """Test contract identity validation."""
        # Valid identity
        valid_identity = ContractIdentity(
            contract_ref="chembl.molecule.v1",
            contract_version="1.0.0",
            compatibility_level=CompatibilityLevel.PATCH,
            schema_hash="a" * 64,
        )
        assert valid_identity.validate() == []

        # Invalid contract ref
        invalid_ref = ContractIdentity(
            contract_ref="invalid_ref",
            contract_version="1.0.0",
            compatibility_level=CompatibilityLevel.PATCH,
            schema_hash="a" * 64,
        )
        assert "Invalid contract_ref format" in invalid_ref.validate()[0]

        # Invalid version
        invalid_version = ContractIdentity(
            contract_ref="chembl.molecule.v1",
            contract_version="1.0",  # Missing patch version
            compatibility_level=CompatibilityLevel.PATCH,
            schema_hash="a" * 64,
        )
        assert "Invalid version format" in invalid_version.validate()[0]

        # Invalid schema hash
        invalid_hash = ContractIdentity(
            contract_ref="chembl.molecule.v1",
            contract_version="1.0.0",
            compatibility_level=CompatibilityLevel.PATCH,
            schema_hash="invalid",  # Too short
        )
        assert "Invalid schema_hash format" in invalid_hash.validate()[0]

    def test_legacy_migration(self):
        """Test migration from legacy contract references."""
        legacy_identity = ContractIdentity.from_legacy("chembl_molecule", "1.0")

        assert legacy_identity.contract_ref == "chembl_molecule.v1.0.0"
        assert legacy_identity.contract_version == "1.0.0"
        assert legacy_identity.compatibility_level == CompatibilityLevel.PATCH
        assert len(legacy_identity.schema_hash) == 64  # Valid SHA256 length

    def test_runtime_metadata_conversion(self):
        """Test conversion to runtime metadata format."""
        identity = ContractIdentity(
            contract_ref="chembl.molecule.v1",
            contract_version="1.0.0",
            compatibility_level=CompatibilityLevel.MINOR,
            schema_hash="a" * 64,
            dq_policy_ref="chembl.dq.v1",
            rule_bundle_version="dq-rules.v1",
        )

        metadata = identity.to_runtime_metadata()

        assert metadata["contract_ref"] == "chembl.molecule.v1"
        assert metadata["contract_version"] == "1.0.0"
        assert metadata["compatibility_level"] == "minor"
        assert metadata["dq_policy_ref"] == "chembl.dq.v1"
        assert metadata["rule_bundle_version"] == "dq-rules.v1"


class TestContractProvenance:
    """Test contract provenance tracking."""

    def test_provenance_creation(self):
        """Test provenance creation."""
        provenance = ContractProvenance(
            source_file="src/schemas/chembl/molecule.v1.yaml",
            generated_by="schema-generator.v1",
            generation_time=_utcnow_iso(),
            source_commit="abc123def",
        )

        assert provenance.source_file == "src/schemas/chembl/molecule.v1.yaml"
        assert provenance.generated_by == "schema-generator.v1"
        assert provenance.source_commit == "abc123def"


class TestDQContractCompatibility:
    """Test DQ contract compatibility."""

    def test_dq_compatibility_creation(self):
        """Test DQ compatibility creation."""
        dq_compat = DQContractCompatibility(
            policy_ref="chembl.dq.v1",
            rule_bundle_version="dq-rules.v1",
            compatibility_hash="compat_hash_123",
            contract_ref="chembl.molecule.v1",
            contract_version="1.0.0",
        )

        assert dq_compat.policy_ref == "chembl.dq.v1"
        assert dq_compat.contract_ref == "chembl.molecule.v1"

    def test_alignment_validation(self):
        """Test alignment validation with contract identity."""
        identity = ContractIdentity(
            contract_ref="chembl.molecule.v1",
            contract_version="1.0.0",
            compatibility_level=CompatibilityLevel.PATCH,
            schema_hash="a" * 64,
            dq_policy_ref="chembl.dq.v1",
            rule_bundle_version="dq-rules.v1",
        )

        # Aligned DQ compatibility
        aligned_dq = DQContractCompatibility(
            policy_ref="chembl.dq.v1",
            rule_bundle_version="dq-rules.v1",
            compatibility_hash="hash123",
            contract_ref="chembl.molecule.v1",
            contract_version="1.0.0",
        )
        assert aligned_dq.validate_alignment(identity) is True

        # Misaligned DQ compatibility
        misaligned_dq = DQContractCompatibility(
            policy_ref="chembl.dq.v2",  # Different policy
            rule_bundle_version="dq-rules.v1",
            compatibility_hash="hash123",
            contract_ref="chembl.molecule.v1",
            contract_version="1.0.0",
        )
        assert misaligned_dq.validate_alignment(identity) is False


class TestLifecycleStatus:
    """Test lifecycle status enum."""

    def test_lifecycle_status_values(self):
        """Test lifecycle status values."""
        assert LifecycleStatus.ACTIVE.value == "active"
        assert LifecycleStatus.DEPRECATED.value == "deprecated"
        assert LifecycleStatus.EXPERIMENTAL.value == "experimental"
        assert LifecycleStatus.SUNSET.value == "sunset"


class TestCompatibilityLevel:
    """Test compatibility level enum."""

    def test_compatibility_level_values(self):
        """Test compatibility level values."""
        assert CompatibilityLevel.MAJOR.value == "major"
        assert CompatibilityLevel.MINOR.value == "minor"
        assert CompatibilityLevel.PATCH.value == "patch"
        assert CompatibilityLevel.MANUAL_REVIEW.value == "manual_review"


class TestPipelineRunContextIntegration:
    """Test contract identity integration with PipelineRunContext."""

    def test_context_with_contract_identity(self):
        """Test PipelineRunContext with contract identity."""
        from bioetl.domain.context import PipelineRunContext
        from bioetl.domain.types import RunID

        identity = ContractIdentity(
            contract_ref="chembl.molecule.v1",
            contract_version="1.0.0",
            compatibility_level=CompatibilityLevel.PATCH,
            schema_hash="a" * 64,
            dq_policy_ref="chembl.dq.v1",
            rule_bundle_version="dq-rules.v1",
        )

        dq_compat = DQContractCompatibility(
            policy_ref="chembl.dq.v1",
            rule_bundle_version="dq-rules.v1",
            compatibility_hash="hash123",
            contract_ref="chembl.molecule.v1",
            contract_version="1.0.0",
        )

        context = PipelineRunContext(
            pipeline_name="chembl_molecule",
            run_id=RunID("test-run-123"),
            run_type="incremental",
            contract_identity=identity,
            dq_contract_compatibility=dq_compat,
        )

        # Test contract consistency validation
        consistency_issues = context.validate_contract_consistency()
        assert consistency_issues == []

    def test_context_with_misaligned_dq(self):
        """Test context with misaligned DQ compatibility."""
        from bioetl.domain.context import PipelineRunContext
        from bioetl.domain.types import RunID

        identity = ContractIdentity(
            contract_ref="chembl.molecule.v1",
            contract_version="1.0.0",
            compatibility_level=CompatibilityLevel.PATCH,
            schema_hash="a" * 64,
            dq_policy_ref="chembl.dq.v1",  # Different from DQ compat below
            rule_bundle_version="dq-rules.v1",
        )

        dq_compat = DQContractCompatibility(
            policy_ref="chembl.dq.v2",  # Different policy ref
            rule_bundle_version="dq-rules.v1",
            compatibility_hash="hash123",
            contract_ref="chembl.molecule.v1",
            contract_version="1.0.0",
        )

        context = PipelineRunContext(
            pipeline_name="chembl_molecule",
            run_id=RunID("test-run-123"),
            run_type="incremental",
            contract_identity=identity,
            dq_contract_compatibility=dq_compat,
        )

        # Should detect DQ policy mismatch
        consistency_issues = context.validate_contract_consistency()
        assert "DQ policy ref mismatch" in consistency_issues[0]
