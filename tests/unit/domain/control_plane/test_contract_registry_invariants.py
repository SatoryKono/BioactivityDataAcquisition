"""Domain-only invariant tests for contract registry validation semantics."""

from __future__ import annotations

import json
import os
from dataclasses import MISSING
from dataclasses import fields as dataclass_fields
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from bioetl.domain.control_plane.contract_registry_service import ContractRegistry
from bioetl.domain.control_plane.contract_registry_types import (
    ContractRegistryEntry,
    RegistryValidationIssue,
    RegistryValidationSeverity,
)
from bioetl.domain.control_plane.gold_contract import GoldContract
from bioetl.domain.control_plane.run_ledger import (
    CANONICAL_RUN_LEDGER_STAGE_NAMES,
    RUN_LEDGER_BASELINE_EVENT_TYPES,
    RUN_LEDGER_STAGE_EVENT_TYPES,
    RunLedgerEntry,
)
from bioetl.domain.control_plane.run_manifest import (
    DOCUMENTED_SOURCE_REVISION_STATES,
    ReplayCapability,
    RunArtifactRef,
    RunCodeProvenance,
    RunInputSnapshotRef,
    RunManifest,
    RunSourceRef,
)
from bioetl.domain.types import RunID, RunType
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


def _field_contract(dataclass_type: type[object]) -> list[dict[str, str]]:
    payload: list[dict[str, str]] = []
    for field in dataclass_fields(dataclass_type):
        default_kind = "required"
        if field.default is not MISSING:
            default_kind = "literal"
        elif field.default_factory is not MISSING:
            default_kind = "factory"
        payload.append({"name": field.name, "default": default_kind})
    return payload


def _assert_golden_payload(payload: dict[str, object], fixture_name: str) -> None:
    fixture_path = FIXTURE_DIR / fixture_name
    if UPDATE_SNAPSHOTS:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        pytest.skip(f"Updated control-plane golden fixture {fixture_path}")

    if not fixture_path.exists():
        pytest.fail(
            f"Missing control-plane golden fixture {fixture_path}. "
            "Run with UPDATE_SNAPSHOTS=1 to create it."
        )

    assert payload == json.loads(fixture_path.read_text(encoding="utf-8"))


def _run_manifest_contract_payload() -> dict[str, object]:
    return {
        "contract": "RunManifest",
        "version": 1,
        "field_contracts": {
            "RunArtifactRef": _field_contract(RunArtifactRef),
            "RunCodeProvenance": _field_contract(RunCodeProvenance),
            "RunInputSnapshotRef": _field_contract(RunInputSnapshotRef),
            "RunManifest": _field_contract(RunManifest),
            "RunSourceRef": _field_contract(RunSourceRef),
        },
        "documented_source_revision_states": sorted(DOCUMENTED_SOURCE_REVISION_STATES),
        "replay_capability_values": sorted(item.value for item in ReplayCapability),
        "run_type_values": sorted(item.value for item in RunType),
        "default_payload": RunManifest().to_dict(),
    }


def _run_ledger_contract_payload() -> dict[str, object]:
    sample_entry = RunLedgerEntry(
        entry_id="ledger-entry-0001",
        manifest_id="manifest-0001",
        run_id=RunID(UUID(int=1)),
        event_type="stage_completed",
        occurred_at=datetime(2026, 7, 10, 0, 0, 0, tzinfo=UTC),
        status="success",
        stage="execute_pipeline",
        message="sample ledger contract event",
        dataset_ref="silver://chembl/activity",
        idempotency_key="sample-idempotency-key",
        metrics_snapshot={"records": 1},
        details={"contract": "sample"},
    )
    return {
        "contract": "RunLedgerEntry",
        "version": 1,
        "field_contracts": {
            "RunLedgerEntry": _field_contract(RunLedgerEntry),
        },
        "baseline_event_types": sorted(RUN_LEDGER_BASELINE_EVENT_TYPES),
        "canonical_stage_names": sorted(CANONICAL_RUN_LEDGER_STAGE_NAMES),
        "stage_event_types": sorted(RUN_LEDGER_STAGE_EVENT_TYPES),
        "sample_payload": sample_entry.to_dict(),
    }


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


def test_run_manifest_contract_golden_fixture() -> None:
    _assert_golden_payload(
        _run_manifest_contract_payload(),
        "run_manifest_contract.json",
    )


def test_run_ledger_contract_golden_fixture() -> None:
    _assert_golden_payload(
        _run_ledger_contract_payload(),
        "run_ledger_contract.json",
    )
