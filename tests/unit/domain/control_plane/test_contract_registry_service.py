"""Tests for contract registry service internal modules.

This test file provides focused coverage for contract registry internal modules:
- contract_registry_service.py: ContractRegistry class and registration logic
- contract_registry_helpers.py: Parsing, validation, and helper functions
- contract_registry_types.py: Domain types and validation logic

These tests complement the existing test_contract_registry.py by testing internal
helper functions, parsing logic, and validation scenarios directly.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.domain.control_plane.contract_registry_helpers import (
    _is_string_mapping,
    as_string_dict,
    as_string_list,
    build_existing_version_issue,
    build_version_regression_message,
    entry_payload,
    parse_entry_payload,
    parse_semver,
    resolve_path,
)
from bioetl.domain.control_plane.contract_registry_service import ContractRegistry
from bioetl.domain.control_plane.contract_registry_types import (
    ContractRegistryEntry,
    RegistryValidationIssue,
    RegistryValidationResult,
    RegistryValidationSeverity,
)
from bioetl.domain.types.contract_identity import (
    CompatibilityLevel,
    ContractIdentity,
    LifecycleStatus,
)

pytestmark = pytest.mark.unit


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def sample_identity():
    """Create a sample ContractIdentity for testing."""
    return ContractIdentity(
        contract_ref="test.contract.v1",
        contract_version="1.0.0",
        compatibility_level=CompatibilityLevel.PATCH,
        schema_hash="a" * 64,
        normalization_profile_ref="test.entity",
        normalization_profile_version="1.0.0",
        normalization_profile_hash="b" * 64,
    )


@pytest.fixture
def sample_entry(sample_identity):
    """Create a sample ContractRegistryEntry for testing."""
    return ContractRegistryEntry(
        identity=sample_identity,
        status=LifecycleStatus.ACTIVE,
        source_path="src/schemas/test.v1.yaml",
        supported_versions=["1.0.0"],
        last_updated="2024-01-01T00:00:00+00:00",
        owners=["test-team"],
        normalization_profile_ref="test.entity",
        normalization_profile_version="1.0.0",
        normalization_profile_hash="b" * 64,
    )


@pytest.fixture
def alternate_entry():
    """Create a second valid ContractRegistryEntry for ordering tests."""
    identity = ContractIdentity(
        contract_ref="test.alternate.v1",
        contract_version="1.1.0",
        compatibility_level=CompatibilityLevel.MINOR,
        schema_hash="c" * 64,
        normalization_profile_ref="test.alternate",
        normalization_profile_version="1.0.0",
        normalization_profile_hash="d" * 64,
    )
    return ContractRegistryEntry(
        identity=identity,
        status=LifecycleStatus.ACTIVE,
        source_path="src/schemas/alternate.v1.yaml",
        supported_versions=["1.0.0", "1.1.0"],
        last_updated="2024-01-02T00:00:00+00:00",
        owners=["test-team"],
        normalization_profile_ref="test.alternate",
        normalization_profile_version="1.0.0",
        normalization_profile_hash="d" * 64,
    )


@pytest.fixture
def sample_registry_data():
    """Create sample registry data for testing."""
    return {
        "version": "1.0",
        "entries": {
            "test.contract.v1": {
                "identity": {
                    "contract_version": "1.0.0",
                    "compatibility_level": "patch",
                    "schema_hash": "a" * 64,
                    "normalization_profile_ref": "test.entity",
                    "normalization_profile_version": "1.0.0",
                    "normalization_profile_hash": "b" * 64,
                },
                "status": "active",
                "source_path": "src/schemas/test.v1.yaml",
                "supported_versions": ["1.0.0"],
                "last_updated": "2024-01-01T00:00:00+00:00",
                "owners": ["test-team"],
            }
        },
    }


# ──────────────────────────────────────────────────────────────────────────────
# contract_registry_helpers.py Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestParseSemver:
    """Tests for parse_semver function."""

    def test_parse_semver_valid_format(self):
        """parse_semver should parse valid semantic versions."""
        assert parse_semver("1.0.0") == (1, 0, 0)
        assert parse_semver("2.5.3") == (2, 5, 3)
        assert parse_semver("10.20.30") == (10, 20, 30)

    def test_parse_semver_invalid_format(self):
        """parse_semver should raise ValueError for invalid formats."""
        with pytest.raises(ValueError, match="Invalid version format"):
            parse_semver("1.0")  # Missing patch

        with pytest.raises(ValueError, match="Invalid version format"):
            parse_semver("1.0.0.0")  # Too many parts

        with pytest.raises(ValueError, match="Invalid version format"):
            parse_semver("a.b.c")  # Non-numeric


def test_registry_hash_is_stable_across_insertion_order(
    sample_entry: ContractRegistryEntry,
    alternate_entry: ContractRegistryEntry,
) -> None:
    """Registry hash must not depend on Python dict insertion order."""
    first = ContractRegistry()
    second = ContractRegistry()

    assert first.register_contract(sample_entry).valid is True
    assert first.register_contract(alternate_entry).valid is True
    assert second.register_contract(alternate_entry).valid is True
    assert second.register_contract(sample_entry).valid is True

    assert first.registry_hash_v2 == second.registry_hash_v2
    assert first.registry_hash_v1 == second.registry_hash_v1


def test_registry_validation_blocks_dq_identity_drift(
    sample_identity: ContractIdentity,
) -> None:
    """DQ metadata must match identity and entry payloads exactly."""
    entry = ContractRegistryEntry(
        identity=sample_identity,
        status=LifecycleStatus.ACTIVE,
        source_path="src/schemas/test.v1.yaml",
        supported_versions=["1.0.0"],
        last_updated="2024-01-01T00:00:00+00:00",
        owners=["test-team"],
        normalization_profile_ref="different.profile",
        normalization_profile_version="1.0.0",
        normalization_profile_hash="b" * 64,
    )

    result = ContractRegistry().register_contract(entry)

    assert result.valid is False
    assert result.has_blocking_issues is True
    assert [
        (issue.field, issue.severity, issue.contract_ref) for issue in result.issues
    ] == [
        (
            "normalization_profile_ref",
            RegistryValidationSeverity.BLOCKING,
            "test.contract.v1",
        )
    ]


class TestStringMappingValidation:
    """Tests for string mapping validation functions."""

    def test_is_string_mapping_returns_true_for_valid(self):
        """_is_string_mapping should return True for valid string mappings."""
        assert _is_string_mapping({"key1": "value1", "key2": "value2"})

    def test_is_string_mapping_returns_false_for_non_string_keys(self):
        """_is_string_mapping should return False for non-string keys."""
        assert not _is_string_mapping({1: "value"})

    def test_is_string_mapping_returns_false_for_non_string_values(self):
        """_is_string_mapping should return False for non-string values."""
        assert not _is_string_mapping({"key": 123})


class TestAsStringList:
    """Tests for as_string_list function."""

    def test_as_string_list_accepts_none(self):
        """as_string_list should return empty list for None."""
        assert as_string_list(None, "test_field") == []

    def test_as_string_list_accepts_valid_list(self):
        """as_string_list should return list for valid input."""
        assert as_string_list(["a", "b", "c"], "test_field") == ["a", "b", "c"]

    def test_as_string_list_rejects_non_list(self):
        """as_string_list should raise ValueError for non-list input."""
        with pytest.raises(ValueError, match="must be a list"):
            as_string_list("not_a_list", "test_field")

    def test_as_string_list_rejects_non_string_elements(self):
        """as_string_list should raise ValueError for non-string elements."""
        with pytest.raises(ValueError, match="must contain only strings"):
            as_string_list(["a", 123, "c"], "test_field")


class TestAsStringDict:
    """Tests for as_string_dict function."""

    def test_as_string_dict_accepts_none(self):
        """as_string_dict should return empty dict for None."""
        assert as_string_dict(None, "test_field") == {}

    def test_as_string_dict_accepts_valid_dict(self):
        """as_string_dict should return dict for valid input."""
        assert as_string_dict({"key1": "value1", "key2": "value2"}, "test_field") == {
            "key1": "value1",
            "key2": "value2",
        }

    def test_as_string_dict_rejects_non_dict(self):
        """as_string_dict should raise ValueError for non-dict input."""
        with pytest.raises(ValueError, match="must be a mapping"):
            as_string_dict("not_a_dict", "test_field")

    def test_as_string_dict_rejects_non_string_mapping(self):
        """as_string_dict should raise ValueError for non-string mapping."""
        with pytest.raises(ValueError, match="must be a mapping of strings"):
            as_string_dict({"key": 123}, "test_field")


class TestParseEntryPayload:
    """Tests for parse_entry_payload function."""

    def test_parse_entry_payload_valid_data(self):
        """parse_entry_payload should parse valid entry data."""
        data = {
            "identity": {
                "contract_version": "1.0.0",
                "compatibility_level": "patch",
                "schema_hash": "a" * 64,
            },
            "status": "active",
            "source_path": "src/schemas/test.yaml",
            "supported_versions": ["1.0.0"],
            "last_updated": "2024-01-01T00:00:00+00:00",
            "owners": ["test-team"],
        }

        entry = parse_entry_payload("test.contract.v1", data)

        assert entry.identity.contract_ref == "test.contract.v1"
        assert entry.identity.contract_version == "1.0.0"
        assert entry.status == LifecycleStatus.ACTIVE
        assert entry.source_path == "src/schemas/test.yaml"

    def test_parse_entry_payload_missing_identity(self):
        """parse_entry_payload should handle missing identity."""
        data = {
            "status": "active",
            "source_path": "src/schemas/test.yaml",
        }

        entry = parse_entry_payload("test.contract.v1", data)

        assert entry.identity.contract_ref == "test.contract.v1"
        assert entry.identity.contract_version == "1.0.0"  # Default

    def test_parse_entry_payload_invalid_identity_type(self):
        """parse_entry_payload should raise ValueError for invalid identity type."""
        data = {
            "identity": "not_a_dict",  # Invalid
            "status": "active",
        }

        with pytest.raises(ValueError, match="Invalid identity payload"):
            parse_entry_payload("test.contract.v1", data)

    def test_parse_entry_payload_invalid_compatibility_level(self):
        """parse_entry_payload should raise ValueError for invalid compatibility_level."""
        data = {
            "identity": {
                "compatibility_level": "invalid_level",  # Invalid
            },
            "status": "active",
        }

        with pytest.raises(ValueError, match="Invalid compatibility_level"):
            parse_entry_payload("test.contract.v1", data)

    def test_parse_entry_payload_invalid_status(self):
        """parse_entry_payload should raise ValueError for invalid status."""
        data = {
            "identity": {
                "contract_version": "1.0.0",
                "schema_hash": "a" * 64,
            },
            "status": "invalid_status",  # Invalid
        }

        with pytest.raises(ValueError, match="Invalid status"):
            parse_entry_payload("test.contract.v1", data)


class TestEntryPayload:
    """Tests for entry_payload function."""

    def test_entry_payload_serializes_entry(self, sample_entry):
        """entry_payload should serialize entry to dictionary."""
        payload = entry_payload(sample_entry)

        assert "identity" in payload
        assert "status" in payload
        assert payload["status"] == "active"
        assert payload["source_path"] == "src/schemas/test.v1.yaml"


class TestBuildExistingVersionIssue:
    """Tests for build_existing_version_issue function."""

    def test_build_existing_version_issue_different_versions(self, sample_entry):
        """build_existing_version_issue should return None for different versions."""
        different_version = ContractRegistryEntry(
            identity=ContractIdentity(
                contract_ref=sample_entry.identity.contract_ref,
                contract_version="2.0.0",
                compatibility_level=sample_entry.identity.compatibility_level,
                schema_hash=sample_entry.identity.schema_hash,
                normalization_profile_ref=sample_entry.identity.normalization_profile_ref,
                normalization_profile_version=sample_entry.identity.normalization_profile_version,
                normalization_profile_hash=sample_entry.identity.normalization_profile_hash,
            ),
            status=sample_entry.status,
            source_path=sample_entry.source_path,
            supported_versions=sample_entry.supported_versions,
            last_updated=sample_entry.last_updated,
            owners=sample_entry.owners,
            normalization_profile_ref=sample_entry.identity.normalization_profile_ref,
            normalization_profile_version=sample_entry.identity.normalization_profile_version,
            normalization_profile_hash=sample_entry.identity.normalization_profile_hash,
        )

        issue = build_existing_version_issue(sample_entry, different_version)
        assert issue is None

    def test_build_existing_version_issue_identical_entries(self, sample_entry):
        """build_existing_version_issue should return None for identical entries."""
        issue = build_existing_version_issue(sample_entry, sample_entry)
        assert issue is None

    def test_build_existing_version_issue_same_version_different_content(
        self, sample_entry
    ):
        """build_existing_version_issue should return warning for same version with different content."""
        different_content = ContractRegistryEntry(
            identity=sample_entry.identity,
            status=sample_entry.status,
            source_path="different/path.yaml",  # Different
            supported_versions=sample_entry.supported_versions,
            last_updated=sample_entry.last_updated,
            owners=sample_entry.owners,
        )

        issue = build_existing_version_issue(sample_entry, different_content)

        assert issue is not None
        assert issue.severity == RegistryValidationSeverity.WARNING
        assert "Updating existing version" in issue.message


class TestResolvePath:
    """Tests for resolve_path function."""

    def test_resolve_path_absolute_path(self):
        """resolve_path should return absolute paths unchanged."""
        absolute = Path("/absolute/path/to/file.yaml")
        base = Path("/base/directory")

        result = resolve_path(str(absolute), base)
        assert result == absolute

    def test_resolve_path_relative_path_with_base(self):
        """resolve_path should resolve relative paths against base."""
        relative = Path("relative/path.yaml")
        base = Path("/base/directory")

        result = resolve_path(str(relative), base)
        assert result == base / relative

    def test_resolve_path_relative_path_without_base(self):
        """resolve_path should return relative paths unchanged when no base."""
        relative = Path("relative/path.yaml")

        result = resolve_path(str(relative), None)
        assert result == relative


class TestBuildVersionRegressionMessage:
    """Tests for build_version_regression_message function."""

    def test_build_version_regression_message_newer_version(self):
        """build_version_regression_message should return None for newer versions."""
        message = build_version_regression_message("1.0.0", "2.0.0")
        assert message is None

    def test_build_version_regression_message_same_version(self):
        """build_version_regression_message should return None for same version."""
        message = build_version_regression_message("1.0.0", "1.0.0")
        assert message is None

    def test_build_version_regression_message_major_regression(self):
        """build_version_regression_message should detect major regression."""
        message = build_version_regression_message("2.0.0", "1.0.0")

        assert message is not None
        assert "major" in message
        assert "1.0.0 < 2.0.0" in message

    def test_build_version_regression_message_minor_regression(self):
        """build_version_regression_message should detect minor regression."""
        message = build_version_regression_message("1.5.0", "1.3.0")

        assert message is not None
        assert "minor" in message

    def test_build_version_regression_message_patch_regression(self):
        """build_version_regression_message should detect patch regression."""
        message = build_version_regression_message("1.0.5", "1.0.3")

        assert message is not None
        assert "patch" in message


# ──────────────────────────────────────────────────────────────────────────────
# contract_registry_service.py Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestContractRegistry:
    """Tests for ContractRegistry class."""

    def test_registry_initialization_empty(self):
        """ContractRegistry should initialize with empty entries."""
        registry = ContractRegistry()
        assert registry.entries == {}
        assert registry.registry_hash is None

    def test_registry_initialization_with_entries(self, sample_entry):
        """ContractRegistry should initialize with pre-parsed entries."""
        entries = {sample_entry.identity.contract_ref: sample_entry}
        registry = ContractRegistry(entries=entries)

        assert len(registry.entries) == 1
        assert registry.registry_hash is not None

    def test_from_dict_builds_registry(self, sample_registry_data):
        """from_dict should build registry from dictionary payload."""
        registry = ContractRegistry.from_dict(sample_registry_data)

        assert len(registry.entries) == 1
        assert "test.contract.v1" in registry.entries

    def test_from_dict_invalid_format_missing_entries(self):
        """from_dict should raise ValueError for missing entries."""
        data = {"version": "1.0"}  # Missing entries

        with pytest.raises(ValueError, match="missing 'entries' mapping"):
            ContractRegistry.from_dict(data)

    def test_from_dict_invalid_entries_type(self):
        """from_dict should raise ValueError for invalid entries type."""
        data = {"entries": "not_a_dict"}  # Invalid type

        with pytest.raises(ValueError, match="missing 'entries' mapping"):
            ContractRegistry.from_dict(data)

    def test_from_dict_invalid_entry_payload(self):
        """from_dict should raise ValueError for invalid entry payload."""
        data = {
            "entries": {
                "test.contract.v1": "not_a_dict"  # Invalid payload
            }
        }

        with pytest.raises(ValueError, match="Invalid entry payload"):
            ContractRegistry.from_dict(data)

    def test_register_contract_valid_entry(self, sample_entry):
        """register_contract should register valid entry."""
        registry = ContractRegistry()
        result = registry.register_contract(sample_entry)

        assert result.valid
        assert len(result.issues) == 0
        assert sample_entry.identity.contract_ref in registry.entries

    def test_register_contract_invalid_entry(self, sample_identity):
        """register_contract should reject invalid entry."""
        invalid_entry = ContractRegistryEntry(
            identity=sample_identity,
            status=LifecycleStatus.ACTIVE,
            source_path="",  # Invalid: empty source_path
            supported_versions=[],
            last_updated="",
            owners=[],
        )

        registry = ContractRegistry()
        result = registry.register_contract(invalid_entry)

        assert not result.valid
        assert len(result.issues) > 0
        assert any("Missing source_path" in i.message for i in result.issues)

    def test_register_contract_version_regression(self, sample_entry):
        """register_contract should reject version regression."""
        registry = ContractRegistry()
        registry.register_contract(sample_entry)

        # Try to register older version
        older_entry = ContractRegistryEntry(
            identity=ContractIdentity(
                contract_ref=sample_entry.identity.contract_ref,
                contract_version="0.5.0",
                compatibility_level=sample_entry.identity.compatibility_level,
                schema_hash=sample_entry.identity.schema_hash,
                normalization_profile_ref=sample_entry.identity.normalization_profile_ref,
                normalization_profile_version=sample_entry.identity.normalization_profile_version,
                normalization_profile_hash=sample_entry.identity.normalization_profile_hash,
            ),
            status=sample_entry.status,
            source_path=sample_entry.source_path,
            supported_versions=["0.5.0"],
            last_updated=sample_entry.last_updated,
            owners=sample_entry.owners,
            normalization_profile_ref=sample_entry.identity.normalization_profile_ref,
            normalization_profile_version=sample_entry.identity.normalization_profile_version,
            normalization_profile_hash=sample_entry.identity.normalization_profile_hash,
        )

        from bioetl.domain.control_plane.contract_registry_types import (
            RegistryValidationError,
        )

        with pytest.raises(RegistryValidationError, match="Cannot register older"):
            registry.register_contract(older_entry)

    def test_register_contract_same_version_warning(self, sample_entry):
        """register_contract should warn when updating same version with different content."""
        registry = ContractRegistry()
        registry.register_contract(sample_entry)

        # Same version, different content
        modified_entry = ContractRegistryEntry(
            identity=sample_entry.identity,
            status=sample_entry.status,
            source_path="different/path.yaml",  # Different
            supported_versions=sample_entry.supported_versions,
            last_updated=sample_entry.last_updated,
            owners=sample_entry.owners,
            normalization_profile_ref=sample_entry.identity.normalization_profile_ref,
            normalization_profile_version=sample_entry.identity.normalization_profile_version,
            normalization_profile_hash=sample_entry.identity.normalization_profile_hash,
        )

        result = registry.register_contract(modified_entry)

        # Warning makes result not valid
        assert not result.valid
        assert len(result.issues) == 1
        assert result.issues[0].severity == RegistryValidationSeverity.WARNING

    def test_get_entry_returns_entry(self, sample_entry):
        """get_entry should return registered entry."""
        registry = ContractRegistry()
        registry.register_contract(sample_entry)

        retrieved = registry.get_entry(sample_entry.identity.contract_ref)

        assert retrieved is not None
        assert retrieved.identity.contract_ref == sample_entry.identity.contract_ref

    def test_get_entry_returns_none_for_missing(self):
        """get_entry should return None for missing contract."""
        registry = ContractRegistry()

        retrieved = registry.get_entry("missing.contract")

        assert retrieved is None

    def test_validate_all_validates_all_entries(self):
        """validate_all should validate all registered entries."""
        # Create a valid entry first, then manually add invalid one to registry
        simple_identity = ContractIdentity(
            contract_ref="test.contract.v2",
            contract_version="1.0.0",
            compatibility_level=CompatibilityLevel.PATCH,
            schema_hash="c" * 64,
        )
        valid_entry = ContractRegistryEntry(
            identity=simple_identity,
            status=LifecycleStatus.ACTIVE,
            source_path="src/schemas/test.yaml",
            supported_versions=["1.0.0"],
            last_updated="2024-01-01T00:00:00+00:00",
            owners=["test-team"],
        )

        registry = ContractRegistry()
        registry.register_contract(valid_entry)

        # Manually add invalid entry to bypass register_contract validation
        invalid_entry = ContractRegistryEntry(
            identity=simple_identity,
            status=LifecycleStatus.ACTIVE,
            source_path="",  # Invalid
            supported_versions=["1.0.0"],
            last_updated="",  # Invalid
            owners=[],  # Invalid
        )
        registry.entries["test.contract.v2"] = invalid_entry

        result = registry.validate_all()

        assert not result.valid
        assert len(result.issues) > 0

    def test_to_dict_serializes_registry(self, sample_entry):
        """to_dict should serialize registry to dictionary."""
        registry = ContractRegistry()
        registry.register_contract(sample_entry)

        data = registry.to_dict()

        assert "version" in data
        assert "entries" in data
        assert sample_entry.identity.contract_ref in data["entries"]

    def test_registry_hash_calculation(self, sample_entry):
        """Registry should calculate hash after registration."""
        registry = ContractRegistry()
        assert registry.registry_hash is None

        registry.register_contract(sample_entry)

        assert registry.registry_hash is not None
        assert len(registry.registry_hash) == 64  # SHA256 hex length

    def test_registry_hash_v1_legacy(self, sample_entry):
        """Registry should calculate legacy v1 hash."""
        registry = ContractRegistry()
        registry.register_contract(sample_entry)

        assert registry.registry_hash_v1 is not None
        assert len(registry.registry_hash_v1) == 64

    def test_registry_hash_v2_canonical(self, sample_entry):
        """Registry should calculate canonical v2 hash."""
        registry = ContractRegistry()
        registry.register_contract(sample_entry)

        assert registry.registry_hash_v2 is not None
        assert len(registry.registry_hash_v2) == 64

    def test_registry_hash_updates_on_registration(self, sample_entry):
        """Registry hash should update when new entry is registered."""
        registry = ContractRegistry()
        registry.register_contract(sample_entry)

        hash_before = registry.registry_hash

        # Register another entry
        another_entry = ContractRegistryEntry(
            identity=ContractIdentity(
                contract_ref="test.contract.v2",
                contract_version="1.0.0",
                compatibility_level=CompatibilityLevel.PATCH,
                schema_hash="c" * 64,
            ),
            status=LifecycleStatus.ACTIVE,
            source_path="src/schemas/test.v2.yaml",
            supported_versions=["1.0.0"],
            last_updated="2024-01-01T00:00:00+00:00",
            owners=["test-team"],
        )
        registry.register_contract(another_entry)

        hash_after = registry.registry_hash

        assert hash_before != hash_after


# ──────────────────────────────────────────────────────────────────────────────
# contract_registry_types.py Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestRegistryValidationResult:
    """Tests for RegistryValidationResult."""

    def test_has_blocking_issues_true(self):
        """has_blocking_issues should return True when blocking issues exist."""
        result = RegistryValidationResult(
            valid=False,
            issues=[
                RegistryValidationIssue(
                    message="Blocking error",
                    severity=RegistryValidationSeverity.BLOCKING,
                )
            ],
        )

        assert result.has_blocking_issues

    def test_has_blocking_issues_false(self):
        """has_blocking_issues should return False when no blocking issues."""
        result = RegistryValidationResult(
            valid=True,
            issues=[
                RegistryValidationIssue(
                    message="Warning",
                    severity=RegistryValidationSeverity.WARNING,
                )
            ],
        )

        assert not result.has_blocking_issues

    def test_has_warnings_true(self):
        """has_warnings should return True when warnings exist."""
        result = RegistryValidationResult(
            valid=False,
            issues=[
                RegistryValidationIssue(
                    message="Warning",
                    severity=RegistryValidationSeverity.WARNING,
                )
            ],
        )

        assert result.has_warnings

    def test_has_warnings_false(self):
        """has_warnings should return False when no warnings."""
        result = RegistryValidationResult(
            valid=True,
            issues=[],
        )

        assert not result.has_warnings


class TestContractRegistryEntryValidation:
    """Tests for ContractRegistryEntry validation methods."""

    def test_validate_required_fields(self, sample_identity):
        """validate should check required fields."""
        # Create a simple identity without DQ fields to avoid DQ alignment issues
        simple_identity = ContractIdentity(
            contract_ref=sample_identity.contract_ref,
            contract_version=sample_identity.contract_version,
            compatibility_level=sample_identity.compatibility_level,
            schema_hash=sample_identity.schema_hash,
        )
        invalid_entry = ContractRegistryEntry(
            identity=simple_identity,
            status=LifecycleStatus.ACTIVE,
            source_path="",  # Missing
            supported_versions=["1.0.0"],  # Include current version
            last_updated="",  # Missing
            owners=[],  # Missing
        )

        issues = invalid_entry.validate()

        assert len(issues) == 3
        assert any("Missing source_path" in i.message for i in issues)
        assert any("Missing last_updated" in i.message for i in issues)
        assert any("No owners specified" in i.message for i in issues)

    def test_validate_supported_versions_includes_current(self, sample_entry):
        """validate should check that current version is in supported_versions."""
        invalid_entry = ContractRegistryEntry(
            identity=sample_entry.identity,
            status=sample_entry.status,
            source_path=sample_entry.source_path,
            supported_versions=["2.0.0"],  # Missing current 1.0.0
            last_updated=sample_entry.last_updated,
            owners=sample_entry.owners,
        )

        issues = invalid_entry.validate()

        assert any("not in supported_versions" in i.message for i in issues)

    def test_validate_dq_identity_alignment(self, sample_identity):
        """validate should check DQ metadata alignment between identity and entry."""
        misaligned_entry = ContractRegistryEntry(
            identity=sample_identity,
            status=LifecycleStatus.ACTIVE,
            source_path="src/schemas/test.yaml",
            supported_versions=["1.0.0"],
            last_updated="2024-01-01T00:00:00+00:00",
            owners=["test-team"],
            dq_policy_ref="different_policy",  # Misaligned
            normalization_profile_ref="test.entity",
            normalization_profile_version="1.0.0",
            normalization_profile_hash="b" * 64,
        )

        issues = misaligned_entry.validate()

        # Since identity has dq_policy_ref=None, entry with "different_policy" will be misaligned
        assert len(issues) > 0
