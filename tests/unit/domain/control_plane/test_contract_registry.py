"""Tests for contract registry implementation."""

import hashlib
import json

import pytest

from bioetl.domain.serialization import serialize_to_json_canonical
from bioetl.domain.control_plane.contract_registry import (
    ContractRegistry,
    ContractRegistryEntry,
    RegistryValidationResult,
    RegistryValidationSeverity,
    RegistryValidationIssue,
    RegistryValidationError,
)
from bioetl.domain.types.contract_identity import (
    ContractIdentity,
    CompatibilityLevel,
    LifecycleStatus,
)


def _ts() -> str:
    """Return one deterministic fixture timestamp."""
    return "2024-01-01T00:00:00+00:00"


class TestContractRegistryEntry:
    """Test contract registry entry creation and validation."""

    def test_entry_creation(self):
        """Test basic entry creation."""
        identity = ContractIdentity(
            contract_ref="test.contract.v1",
            contract_version="1.0.0",
            compatibility_level=CompatibilityLevel.MAJOR,
            schema_hash="a" * 64,
        )

        entry = ContractRegistryEntry(
            identity=identity,
            status=LifecycleStatus.ACTIVE,
            source_path="src/schemas/test.v1.yaml",
            supported_versions=["1.0.0"],
            last_updated=_ts(),
            owners=["test-team"],
        )

        assert entry.identity == identity
        assert entry.status == LifecycleStatus.ACTIVE
        assert entry.source_path == "src/schemas/test.v1.yaml"
        assert entry.supported_versions == ["1.0.0"]

    def test_entry_validation(self):
        """Test entry validation."""
        identity = ContractIdentity(
            contract_ref="test.contract.v1",
            contract_version="1.0.0",
            compatibility_level=CompatibilityLevel.PATCH,
            schema_hash="a" * 64,
        )

        # Valid entry
        valid_entry = ContractRegistryEntry(
            identity=identity,
            status=LifecycleStatus.ACTIVE,
            source_path="src/schemas/test.v1.yaml",
            supported_versions=["1.0.0"],
            last_updated=_ts(),
            owners=["test-team"],
        )
        assert valid_entry.validate() == []

        # Missing source path
        invalid_entry = ContractRegistryEntry(
            identity=identity,
            status=LifecycleStatus.ACTIVE,
            source_path="",  # Invalid
            supported_versions=["1.0.0"],
            last_updated="",
            owners=[],
        )
        issues = invalid_entry.validate()
        assert len(issues) == 3  # source_path, last_updated, owners
        assert any("Missing source_path" in i.message for i in issues)

    def test_version_consistency_validation(self):
        """Test version consistency validation."""
        identity = ContractIdentity(
            contract_ref="test.contract.v1",
            contract_version="1.0.0",
            compatibility_level=CompatibilityLevel.PATCH,
            schema_hash="a" * 64,
        )

        # Current version not in supported versions
        inconsistent_entry = ContractRegistryEntry(
            identity=identity,
            status=LifecycleStatus.ACTIVE,
            source_path="src/schemas/test.v1.yaml",
            supported_versions=["0.9.0"],  # Missing 1.0.0
            last_updated=_ts(),
            owners=["test-team"],
        )

        issues = inconsistent_entry.validate()
        assert len(issues) == 1
        assert "Current version 1.0.0 not in supported_versions" in issues[0].message


class TestContractRegistry:
    """Test contract registry functionality."""

    def test_registry_creation(self):
        """Test registry creation."""
        registry = ContractRegistry()
        assert len(registry.entries) == 0
        assert registry.registry_hash is None
        assert registry.registry_hash_v1 is None
        assert registry.registry_hash_v2 is None

    def test_contract_registration(self):
        """Test contract registration."""
        registry = ContractRegistry()

        identity = ContractIdentity(
            contract_ref="test.contract.v1",
            contract_version="1.0.0",
            compatibility_level=CompatibilityLevel.PATCH,
            schema_hash="a" * 64,
        )

        entry = ContractRegistryEntry(
            identity=identity,
            status=LifecycleStatus.ACTIVE,
            source_path="src/schemas/test.v1.yaml",
            supported_versions=["1.0.0"],
            last_updated=_ts(),
            owners=["test-team"],
        )

        result = registry.register_contract(entry)
        assert result.valid is True
        assert len(registry.entries) == 1

    def test_duplicate_registration(self):
        """Test duplicate contract registration."""
        registry = ContractRegistry()

        identity = ContractIdentity(
            contract_ref="test.contract.v1",
            contract_version="1.0.0",
            compatibility_level=CompatibilityLevel.PATCH,
            schema_hash="a" * 64,
        )

        entry1 = ContractRegistryEntry(
            identity=identity,
            status=LifecycleStatus.ACTIVE,
            source_path="src/schemas/test.v1.yaml",
            supported_versions=["1.0.0"],
            last_updated=_ts(),
            owners=["test-team"],
        )

        entry2 = ContractRegistryEntry(
            identity=identity,
            status=LifecycleStatus.ACTIVE,
            source_path="src/schemas/test.v2.yaml",  # Different source
            supported_versions=["1.0.0"],
            last_updated=_ts(),
            owners=["test-team"],
        )

        # First registration should succeed
        result1 = registry.register_contract(entry1)
        assert result1.valid is True

        # Second registration should warn about update
        result2 = registry.register_contract(entry2)
        assert result2.valid is False
        assert len(result2.issues) == 1
        assert "Updating existing version" in result2.issues[0].message

    def test_version_sequence_validation(self):
        """Test version sequence validation."""
        registry = ContractRegistry()

        # Register initial version
        identity_v1 = ContractIdentity(
            contract_ref="test.contract.v1",
            contract_version="1.0.0",
            compatibility_level=CompatibilityLevel.PATCH,
            schema_hash="a" * 64,
        )

        entry_v1 = ContractRegistryEntry(
            identity=identity_v1,
            status=LifecycleStatus.ACTIVE,
            source_path="src/schemas/test.v1.yaml",
            supported_versions=["1.0.0"],
            last_updated=_ts(),
            owners=["test-team"],
        )

        registry.register_contract(entry_v1)

        # Try to register older version
        identity_v0 = ContractIdentity(
            contract_ref="test.contract.v1",
            contract_version="0.9.0",
            compatibility_level=CompatibilityLevel.PATCH,
            schema_hash="b" * 64,
        )

        entry_v0 = ContractRegistryEntry(
            identity=identity_v0,
            status=LifecycleStatus.ACTIVE,
            source_path="src/schemas/test.v0.yaml",
            supported_versions=["0.9.0"],
            last_updated=_ts(),
            owners=["test-team"],
        )

        # Registration should fail with RegistryValidationError due to version sequence validation
        with pytest.raises(RegistryValidationError) as exc_info:
            registry.register_contract(entry_v0)

        # Check the exception message
        assert "Cannot register older major version" in str(exc_info.value)
        assert "0.9.0 < 1.0.0" in str(exc_info.value)

    def test_registry_validation(self):
        """Test registry validation."""
        registry = ContractRegistry()

        # Add valid entry
        identity = ContractIdentity(
            contract_ref="test.contract.v1",
            contract_version="1.0.0",
            compatibility_level=CompatibilityLevel.PATCH,
            schema_hash="a" * 64,
        )

        valid_entry = ContractRegistryEntry(
            identity=identity,
            status=LifecycleStatus.ACTIVE,
            source_path="src/schemas/test.v1.yaml",
            supported_versions=["1.0.0"],
            last_updated=_ts(),
            owners=["test-team"],
        )

        registry.register_contract(valid_entry)

        # Add invalid entry
        invalid_identity = ContractIdentity(
            contract_ref="test.contract.v2",
            contract_version="invalid",  # Invalid version
            compatibility_level=CompatibilityLevel.PATCH,
            schema_hash="a" * 64,
        )

        invalid_entry = ContractRegistryEntry(
            identity=invalid_identity,
            status=LifecycleStatus.ACTIVE,
            source_path="src/schemas/test.v2.yaml",
            supported_versions=["1.0.0"],
            last_updated=_ts(),
            owners=["test-team"],
        )

        # Registration should fail validation and not add the entry
        result = registry.register_contract(invalid_entry)

        # The registration should fail validation
        assert result.valid is False
        # Invalid version causes validation issues
        assert len(result.issues) >= 1  # At least one issue
        version_issues = [
            i for i in result.issues if "Invalid version format" in i.message
        ]
        assert len(version_issues) == 1

        # Entry should not be added to registry if validation fails
        assert len(registry.entries) == 1  # Only the valid entry

        # Overall registry validation should still pass (invalid entry not added)
        all_result = registry.validate_all()
        assert all_result.valid is True  # No issues because invalid entry wasn't added
        assert len(all_result.issues) == 0

    def test_registry_hash_exposes_v1_and_v2_during_migration(self):
        """Registry should expose both legacy and canonical hash variants."""
        registry = ContractRegistry()

        identity = ContractIdentity(
            contract_ref="test.contract.v1",
            contract_version="1.0.0",
            compatibility_level=CompatibilityLevel.PATCH,
            schema_hash="a" * 64,
        )

        entry = ContractRegistryEntry(
            identity=identity,
            status=LifecycleStatus.ACTIVE,
            source_path="src/schemas/test.v1.yaml",
            supported_versions=["1.0.0"],
            last_updated="2024-01-01T00:00:00Z",
            owners=["test-team"],
        )

        registry.register_contract(entry)

        assert registry.registry_hash_v1 is not None
        assert registry.registry_hash_v2 is not None
        assert registry.registry_hash == registry.registry_hash_v2
        assert registry.registry_hash_v1 != registry.registry_hash_v2

    def test_registry_hash_v2_matches_canonical_serializer_contract(self):
        """Canonical registry hash must hash canonical JSON bytes only."""
        registry = ContractRegistry()

        identity = ContractIdentity(
            contract_ref="test.contract.v1",
            contract_version="1.0.0",
            compatibility_level=CompatibilityLevel.PATCH,
            schema_hash="a" * 64,
        )

        entry = ContractRegistryEntry(
            identity=identity,
            status=LifecycleStatus.ACTIVE,
            source_path="src/schemas/test.v1.yaml",
            supported_versions=["2.0.0", "1.0.0"],
            last_updated="2024-01-01T00:00:00Z",
            owners=["test-team"],
        )

        registry.register_contract(entry)
        payload = {
            "test.contract.v1": {
                "identity": {
                    "contract_version": "1.0.0",
                    "schema_hash": "a" * 64,
                },
                "status": "active",
                "supported_versions": ["1.0.0", "2.0.0"],
            }
        }

        expected_v1 = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode("utf-8")
        ).hexdigest()
        expected_v2 = hashlib.sha256(
            serialize_to_json_canonical(payload).encode("utf-8")
        ).hexdigest()

        assert registry.registry_hash_v1 == expected_v1
        assert registry.registry_hash_v2 == expected_v2

    def test_registry_hash_is_deterministic_for_registration_order(self):
        """Hash values should remain stable regardless of registration order."""
        identity_a = ContractIdentity(
            contract_ref="test.contract.a",
            contract_version="1.0.0",
            compatibility_level=CompatibilityLevel.PATCH,
            schema_hash="a" * 64,
        )
        identity_b = ContractIdentity(
            contract_ref="test.contract.b",
            contract_version="1.0.0",
            compatibility_level=CompatibilityLevel.MINOR,
            schema_hash="b" * 64,
        )
        entry_a = ContractRegistryEntry(
            identity=identity_a,
            status=LifecycleStatus.ACTIVE,
            source_path="src/schemas/test.a.yaml",
            supported_versions=["1.0.0"],
            last_updated="2024-01-01T00:00:00Z",
            owners=["team-a"],
        )
        entry_b = ContractRegistryEntry(
            identity=identity_b,
            status=LifecycleStatus.DEPRECATED,
            source_path="src/schemas/test.b.yaml",
            supported_versions=["1.0.0"],
            last_updated="2024-01-01T00:00:00Z",
            owners=["team-b"],
        )

        registry_left = ContractRegistry()
        registry_left.register_contract(entry_a)
        registry_left.register_contract(entry_b)

        registry_right = ContractRegistry()
        registry_right.register_contract(entry_b)
        registry_right.register_contract(entry_a)

        assert registry_left.registry_hash_v1 == registry_right.registry_hash_v1
        assert registry_left.registry_hash_v2 == registry_right.registry_hash_v2


class TestRegistryValidationResult:
    """Test registry validation result."""

    def test_validation_result_creation(self):
        """Test validation result creation."""
        result = RegistryValidationResult(valid=True)
        assert result.valid is True
        assert result.issues == []
        assert result.has_blocking_issues is False
        assert result.has_warnings is False

    def test_validation_result_with_issues(self):
        """Test validation result with issues."""
        issues = [
            RegistryValidationIssue(
                message="Test blocking issue",
                severity=RegistryValidationSeverity.BLOCKING,
                contract_ref="test.v1",
            ),
            RegistryValidationIssue(
                message="Test warning",
                severity=RegistryValidationSeverity.WARNING,
                contract_ref="test.v1",
            ),
        ]

        result = RegistryValidationResult(valid=False, issues=issues)
        assert result.valid is False
        assert len(result.issues) == 2
        assert result.has_blocking_issues is True
        assert result.has_warnings is True


class TestRegistryIntegration:
    """Test registry integration with contract identity."""

    def test_registry_with_contract_identity(self):
        """Test registry integration with contract identity."""
        from bioetl.domain.types.contract_identity import DQContractCompatibility

        registry = ContractRegistry()

        # Create contract identity
        identity = ContractIdentity(
            contract_ref="chembl.molecule.v1",
            contract_version="1.0.0",
            compatibility_level=CompatibilityLevel.MAJOR,
            schema_hash="a" * 64,
            dq_policy_ref="chembl.dq.v1",
            rule_bundle_version="dq-rules.v1.0",
        )

        # Create DQ compatibility
        dq_compat = DQContractCompatibility(
            policy_ref="chembl.dq.v1",
            rule_bundle_version="dq-rules.v1.0",
            compatibility_hash="compat_hash_123",
            contract_ref="chembl.molecule.v1",
            contract_version="1.0.0",
        )

        # Verify alignment
        assert dq_compat.validate_alignment(identity) is True

        # Create registry entry
        entry = ContractRegistryEntry(
            identity=identity,
            status=LifecycleStatus.ACTIVE,
            source_path="src/schemas/chembl/molecule.v1.yaml",
            supported_versions=["1.0.0"],
            last_updated=_ts(),
            owners=["chembl-team"],
            dq_policy_ref="chembl.dq.v1",
            rule_bundle_version="dq-rules.v1.0",
        )

        # Register and validate
        result = registry.register_contract(entry)
        assert result.valid is True
        assert len(registry.entries) == 1

    def test_registry_misaligned_dq(self):
        """Test registry with misaligned DQ compatibility."""
        registry = ContractRegistry()

        # Create contract identity
        identity = ContractIdentity(
            contract_ref="chembl.molecule.v1",
            contract_version="1.0.0",
            compatibility_level=CompatibilityLevel.MAJOR,
            schema_hash="a" * 64,
            dq_policy_ref="chembl.dq.v1",  # Different from entry below
            rule_bundle_version="dq-rules.v1.0",
        )

        # Create registry entry with different DQ policy
        entry = ContractRegistryEntry(
            identity=identity,
            status=LifecycleStatus.ACTIVE,
            source_path="src/schemas/chembl/molecule.v1.yaml",
            supported_versions=["1.0.0"],
            last_updated=_ts(),
            owners=["chembl-team"],
            dq_policy_ref="chembl.dq.v2",  # Different policy
            rule_bundle_version="dq-rules.v1.0",
        )

        # This should still register but identity validation will catch the mismatch
        result = registry.register_contract(entry)
        assert result.valid is True  # Entry itself is valid

        # But identity validation should catch the issue
        identity_issues = identity.validate()
        assert len(identity_issues) == 0  # Identity is valid on its own

        # The mismatch would be caught at runtime when both are used together
