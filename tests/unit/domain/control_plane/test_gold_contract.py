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
"""Unit tests for Gold contract compatibility and registry helpers."""

from __future__ import annotations

import pytest

from bioetl.domain.control_plane.gold_contract import (
    CompatibilityCheckResult,
    CompatibilityVerdict,
    GoldContract,
    GoldContractRegistry,
    _minor_version_compatible,
    _parse_semver,
    create_gold_contract_registry,
)
from bioetl.domain.types.contract_identity import (
    CompatibilityLevel,
    ContractIdentity,
    ContractProvenance,
    LifecycleStatus,
)


pytestmark = pytest.mark.unit


def _make_identity(
    version: str = "1.2.3",
    *,
    contract_ref: str = "gold.compound",
    schema_hash: str = "a" * 64,
) -> ContractIdentity:
    return ContractIdentity(
        contract_ref=contract_ref,
        contract_version=version,
        compatibility_level=CompatibilityLevel.MINOR,
        schema_hash=schema_hash,
        dq_policy_ref="dq.policy",
        rule_bundle_version="2026.03",
    )


def _make_contract(
    version: str = "1.2.3",
    *,
    contract_ref: str = "gold.compound",
    schema: dict[str, object] | None = None,
    source_file: str = "contracts/gold_compound.yaml",
    compatibility_rules: dict[str, object] | None = None,
) -> GoldContract:
    return GoldContract(
        identity=_make_identity(version=version, contract_ref=contract_ref),
        schema=schema or {"fields": ["id", "name"]},
        provenance=ContractProvenance(
            source_file=source_file,
            generated_by="unit-test",
            generation_time="2026-03-28T10:00:00Z",
            source_commit="abc123",
        ),
        lifecycle_status=LifecycleStatus.ACTIVE,
        owners=["team-bioetl"],
        downstream_dependencies=["gold.analytics"],
        migration_notes="Safe to roll forward",
        compatibility_rules=compatibility_rules,
    )


def test_compatibility_check_result_helpers_build_expected_payloads() -> None:
    compatible = CompatibilityCheckResult.compatible()
    incompatible = CompatibilityCheckResult.incompatible(
        CompatibilityVerdict.MAJOR_INCOMPATIBLE,
        "major drift",
        {"expected": "1.x"},
    )

    assert compatible.verdict is CompatibilityVerdict.COMPATIBLE
    assert compatible.message == "Contracts are compatible"
    assert compatible.details == {}
    assert incompatible.verdict is CompatibilityVerdict.MAJOR_INCOMPATIBLE
    assert incompatible.details == {"expected": "1.x"}


def test_parse_semver_returns_integer_triplet() -> None:
    assert _parse_semver("12.34.56") == (12, 34, 56)


@pytest.mark.parametrize(
    ("compatibility_rules", "expected"),
    [
        (None, True),
        ({}, True),
        ({"minor_version_compatibility": True}, True),
        ({"minor_version_compatibility": False}, False),
    ],
)
def test_minor_version_compatible_honors_explicit_flag(
    compatibility_rules: dict[str, object] | None, expected: bool
) -> None:
    assert _minor_version_compatible(compatibility_rules) is expected


def test_validate_compatibility_returns_unknown_for_different_contract_refs() -> None:
    source = _make_contract(contract_ref="gold.compound")
    target = _make_contract(contract_ref="gold.target")

    result = source.validate_compatibility(target)

    assert result.verdict is CompatibilityVerdict.UNKNOWN
    assert "Different contract references" in result.message


def test_validate_compatibility_detects_major_version_change() -> None:
    source = _make_contract("1.2.3")
    target = _make_contract("2.0.0")

    result = source.validate_compatibility(target)

    assert result.verdict is CompatibilityVerdict.MAJOR_INCOMPATIBLE
    assert result.message == "Major version change: 1.2.3 -> 2.0.0"


def test_validate_compatibility_allows_minor_version_when_rule_enables_it() -> None:
    source = _make_contract(
        "1.2.3", compatibility_rules={"minor_version_compatibility": True}
    )
    target = _make_contract("1.3.0")

    result = source.validate_compatibility(target)

    assert result.verdict is CompatibilityVerdict.COMPATIBLE


def test_validate_compatibility_blocks_minor_version_when_rule_disables_it() -> None:
    source = _make_contract(
        "1.2.3",
        compatibility_rules={"minor_version_compatibility": False},
    )
    target = _make_contract("1.3.0")

    result = source.validate_compatibility(target)

    assert result.verdict is CompatibilityVerdict.MINOR_INCOMPATIBLE
    assert result.message == "Minor version change: 1.2.3 -> 1.3.0"


@pytest.mark.parametrize("target_version", ["1.2.4", "1.2.3"])
def test_validate_compatibility_treats_patch_and_same_version_as_compatible(
    target_version: str,
) -> None:
    source = _make_contract("1.2.3")
    target = _make_contract(target_version)

    result = source.validate_compatibility(target)

    assert result.verdict is CompatibilityVerdict.COMPATIBLE


def test_get_identity_metadata_returns_runtime_payload() -> None:
    contract = _make_contract()

    metadata = contract.get_identity_metadata()

    assert metadata["contract_ref"] == "gold.compound"
    assert metadata["contract_version"] == "1.2.3"
    assert metadata["compatibility_level"] == "minor"
    assert metadata["dq_policy_ref"] == "dq.policy"
    assert metadata["rule_bundle_version"] == "2026.03"
    assert metadata["lifecycle_status"] == LifecycleStatus.ACTIVE.value
    assert metadata["owners"] == ["team-bioetl"]
    assert metadata["provenance"] == {
        "source_file": "contracts/gold_compound.yaml",
        "generated_by": "unit-test",
        "generation_time": "2026-03-28T10:00:00Z",
        "source_commit": "abc123",
    }


def test_validate_reports_identity_schema_and_provenance_errors() -> None:
    invalid_identity = ContractIdentity(
        contract_ref="gold",
        contract_version="1.2",
        compatibility_level=CompatibilityLevel.PATCH,
        schema_hash="bad-hash",
    )
    contract = GoldContract(
        identity=invalid_identity,
        schema={},
        provenance=ContractProvenance(
            source_file="",
            generated_by="unit-test",
            generation_time="2026-03-28T10:00:00Z",
        ),
        lifecycle_status=LifecycleStatus.DEPRECATED,
        owners=[],
        downstream_dependencies=[],
    )

    errors = contract.validate()

    assert "Identity: Invalid contract_ref format: gold" in errors
    assert "Identity: Invalid version format: 1.2 (expected X.Y.Z)" in errors
    assert "Identity: Invalid schema_hash format: bad-hash" in errors
    assert "Invalid or missing schema definition" in errors
    assert "Missing source file in provenance" in errors


def test_registry_register_get_and_validate_all_handle_conflicts_and_invalid_contracts() -> (
    None
):
    registry = GoldContractRegistry()
    valid_contract = _make_contract("1.2.3")
    invalid_contract = GoldContract(
        identity=_make_identity(version="1.2.3", contract_ref="gold.invalid"),
        schema=[],
        provenance=ContractProvenance(
            source_file="",
            generated_by="unit-test",
            generation_time="2026-03-28T10:00:00Z",
        ),
        lifecycle_status=LifecycleStatus.ACTIVE,
        owners=[],
        downstream_dependencies=[],
    )

    registry.register(valid_contract)
    registry.register(invalid_contract)

    assert registry.get("gold.compound") is valid_contract
    assert registry.get("missing") is None
    assert registry.validate_all() == {
        "gold.invalid": [
            "Invalid or missing schema definition",
            "Missing source file in provenance",
        ]
    }

    with pytest.raises(
        ValueError,
        match=r"Version conflict for gold\.compound: 1\.2\.3 vs 2\.0\.0",
    ):
        registry.register(_make_contract("2.0.0"))


def test_create_gold_contract_registry_returns_empty_registry() -> None:
    registry = create_gold_contract_registry()

    assert isinstance(registry, GoldContractRegistry)
    assert registry.contracts == {}
