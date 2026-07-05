"""Domain-only invariant tests for contract registry validation semantics."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from bioetl.domain.control_plane.contract_registry_service import ContractRegistry
from bioetl.domain.control_plane.contract_registry_types import (
    ContractRegistryEntry,
    RegistryValidationIssue,
    RegistryValidationSeverity,
)
from bioetl.domain.control_plane.gold_contract import GoldContract
from bioetl.domain.types.contract_identity import (
    CompatibilityLevel,
    ContractIdentity,
    ContractProvenance,
    LifecycleStatus,
)

pytestmark = pytest.mark.unit

FIXTURE_DIR = Path("tests/fixtures/golden/control_plane")
UPDATE_SNAPSHOTS = os.environ.get("UPDATE_SNAPSHOTS", "0") == "1"


def _issue_key(
    issue: RegistryValidationIssue,
) -> tuple[str, str, str | None, str | None]:
    return (
        issue.contract_ref or "",
        issue.field or "",
        issue.severity.value,
        issue.message,
    )


def _make_identity(
    *,
    contract_ref: str,
    contract_version: str = "1.0.0",
    schema_hash: str = "a" * 64,
) -> ContractIdentity:
    return ContractIdentity(
        contract_ref=contract_ref,
        contract_version=contract_version,
        compatibility_level=CompatibilityLevel.PATCH,
        schema_hash=schema_hash,
        normalization_profile_ref="test.entity",
        normalization_profile_version="1.0.0",
        normalization_profile_hash="b" * 64,
    )


def _make_entry(
    *,
    contract_ref: str,
    source_path: str = "",
    owners: list[str] | None = None,
    supported_versions: list[str] | None = None,
) -> ContractRegistryEntry:
    identity = _make_identity(contract_ref=contract_ref)
    return ContractRegistryEntry(
        identity=identity,
        status=LifecycleStatus.ACTIVE,
        source_path=source_path,
        supported_versions=supported_versions or [identity.contract_version],
        last_updated="2024-01-01T00:00:00+00:00",
        owners=["test-team"] if owners is None else owners,
        normalization_profile_ref="test.entity",
        normalization_profile_version="1.0.0",
        normalization_profile_hash="b" * 64,
    )


def _make_gold_contract() -> GoldContract:
    identity = ContractIdentity(
        contract_ref="gold.compound",
        contract_version="1.2.3",
        compatibility_level=CompatibilityLevel.MINOR,
        schema_hash="a" * 64,
        dq_policy_ref="dq.policy",
        rule_bundle_version="2026.03",
    )
    return GoldContract(
        identity=identity,
        schema={"fields": ["id", "name"]},
        provenance=ContractProvenance(
            source_file="contracts/gold_compound.yaml",
            generated_by="unit-test",
            generation_time="2026-03-28T10:00:00Z",
            source_commit="abc123",
        ),
        lifecycle_status=LifecycleStatus.ACTIVE,
        owners=["team-bioetl"],
        downstream_dependencies=["gold.analytics"],
    )


def test_validate_all_issue_ordering_is_deterministic() -> None:
    registry = ContractRegistry(
        entries={
            "alpha.contract": _make_entry(
                contract_ref="alpha.contract",
                source_path="",
                owners=[],
            ),
            "beta.contract": _make_entry(
                contract_ref="beta.contract",
                source_path="",
                owners=[],
                supported_versions=["9.9.9"],
            ),
        }
    )

    first = [_issue_key(issue) for issue in registry.validate_all().issues]
    second = [_issue_key(issue) for issue in registry.validate_all().issues]

    assert first == second
    contract_refs = [issue.contract_ref for issue in registry.validate_all().issues]
    assert contract_refs == [
        "alpha.contract",
        "alpha.contract",
        "beta.contract",
        "beta.contract",
        "beta.contract",
    ]


def test_validate_all_rebinds_missing_contract_refs_in_stable_order() -> None:
    class _EntryWithDetachedIssues:
        def __init__(self, entry: ContractRegistryEntry) -> None:
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

    first_entry = _make_entry(contract_ref="first.contract")
    second_entry = _make_entry(contract_ref="second.contract")
    registry = ContractRegistry(
        entries={
            "first.contract": _EntryWithDetachedIssues(first_entry),
            "second.contract": _EntryWithDetachedIssues(second_entry),
        }
    )

    issues = registry.validate_all().issues

    assert issues == [
        RegistryValidationIssue(
            message="missing source path",
            severity=RegistryValidationSeverity.WARNING,
            contract_ref="first.contract",
            field="source_path",
        ),
        RegistryValidationIssue(
            message="missing source path",
            severity=RegistryValidationSeverity.WARNING,
            contract_ref="second.contract",
            field="source_path",
        ),
    ]


def test_registry_hash_is_stable_for_insertion_order_invariant_payload() -> None:
    entry_a = _make_entry(contract_ref="alpha.contract")
    entry_b = _make_entry(contract_ref="beta.contract")

    registry_one = ContractRegistry(
        entries={"alpha.contract": entry_a, "beta.contract": entry_b}
    )
    registry_two = ContractRegistry(
        entries={"beta.contract": entry_b, "alpha.contract": entry_a}
    )

    assert registry_one.registry_hash == registry_two.registry_hash
    assert registry_one.registry_hash_v1 == registry_two.registry_hash_v1


def test_gold_contract_identity_golden_fixture() -> None:
    contract = _make_gold_contract()
    payload = {
        "contract_ref": contract.identity.contract_ref,
        "contract_version": contract.identity.contract_version,
        "compatibility_level": contract.identity.compatibility_level.value,
        "schema_hash": contract.identity.schema_hash,
        "dq_policy_ref": contract.identity.dq_policy_ref,
        "rule_bundle_version": contract.identity.rule_bundle_version,
        "lifecycle_status": contract.lifecycle_status.value,
    }

    fixture_path = FIXTURE_DIR / "gold_contract_identity.json"
    if UPDATE_SNAPSHOTS:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        pytest.skip("Updated gold contract identity golden fixture")

    if not fixture_path.exists():
        pytest.fail(
            f"Missing gold contract identity fixture {fixture_path}. "
            "Run with UPDATE_SNAPSHOTS=1 to create it."
        )

    assert payload == json.loads(fixture_path.read_text(encoding="utf-8"))
