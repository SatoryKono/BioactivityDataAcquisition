# pyright: reportArgumentType=false
"""Focused tests for CR-FULL 20260816 types criticals (#8893)."""

from __future__ import annotations

import pytest

from bioetl.domain.types.contract_identity import ContractIdentity, _normalize_semver
from bioetl.domain.types.contract_rollout import ContractRolloutPolicy

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1", "1.0.0"),
        ("1.2", "1.2.0"),
        ("1.2.3", "1.2.3"),
        ("1.2.3.4", "1.2.3"),
        ("01.02", "1.2.0"),
    ],
)
def test_normalize_semver_pads_or_trims_to_xyz(raw: str, expected: str) -> None:
    assert _normalize_semver(raw) == expected


@pytest.mark.parametrize("raw", ["1", "1.2", "1.2.3", "1.2.3.4"])
def test_from_legacy_produces_validating_semver_identity(raw: str) -> None:
    identity = ContractIdentity.from_legacy("chembl_molecule", raw)
    assert identity.contract_version.count(".") == 2
    assert identity.validate() == []
    assert identity.contract_ref.endswith(f".v{identity.contract_version}")


def test_single_rollout_policy_defaults_read_and_write_to_active_version() -> None:
    policy = ContractRolloutPolicy(
        contract_ref="gold.publication",
        active_version="1.0.0",
    )
    assert policy.mode == "single"
    assert policy.read_order == ("1.0.0",)
    assert policy.write_versions == ("1.0.0",)
    targets = policy.read_targets("publication")
    assert len(targets) == 1
    assert targets[0].contract_version == "1.0.0"
    assert targets[0].is_active is True
