# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Additional contract registry coverage for deterministic control-plane semantics."""

from __future__ import annotations

import pytest

from bioetl.domain.control_plane.contract_registry_service import ContractRegistry
from bioetl.domain.control_plane.contract_registry_types import (
    ContractRegistryEntry,
    RegistryValidationIssue,
    RegistryValidationSeverity,
)
from bioetl.domain.types.contract_identity import (
    CompatibilityLevel,
    ContractIdentity,
    LifecycleStatus,
)


pytestmark = pytest.mark.unit


@pytest.fixture
def sample_identity() -> ContractIdentity:
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
def sample_entry(sample_identity: ContractIdentity) -> ContractRegistryEntry:
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
def sample_registry_data() -> dict[str, object]:
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


def test_registry_from_dict_round_trips_single_entry(
    sample_registry_data: dict[str, object],
) -> None:
    registry = ContractRegistry.from_dict(sample_registry_data)

    payload = registry.to_dict()

    assert payload["version"] == "1.0"
    assert payload["entries"]["test.contract.v1"]["status"] == "active"
    assert registry.get_entry("test.contract.v1") is not None


def test_registry_from_dict_rejects_non_mapping_entries_payload() -> None:
    with pytest.raises(ValueError, match="missing 'entries' mapping"):
        ContractRegistry.from_dict({"version": "1.0", "entries": []})


def test_validate_all_rebinds_missing_contract_refs_to_registry_key(
    sample_entry,
) -> None:
    class _EntryWithDetachedIssues:
        def __init__(self, entry) -> None:
            self.identity = entry.identity
            self.status = entry.status
            self.source_path = entry.source_path
            self.supported_versions = entry.supported_versions
            self.last_updated = entry.last_updated
            self.owners = entry.owners
            self.normalization_profile_ref = entry.normalization_profile_ref
            self.normalization_profile_version = entry.normalization_profile_version
            self.normalization_profile_hash = entry.normalization_profile_hash

        def validate(self) -> list[RegistryValidationIssue]:
            return [
                RegistryValidationIssue(
                    message="missing source path",
                    severity=RegistryValidationSeverity.WARNING,
                    contract_ref=None,
                    field="source_path",
                )
            ]

    registry = ContractRegistry(
        entries={"test.contract.v1": _EntryWithDetachedIssues(sample_entry)}
    )

    result = registry.validate_all()

    assert result.valid is False
    assert result.issues == [
        RegistryValidationIssue(
            message="missing source path",
            severity=RegistryValidationSeverity.WARNING,
            contract_ref="test.contract.v1",
            field="source_path",
        )
    ]
