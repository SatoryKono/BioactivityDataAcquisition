"""Unit tests for contract rollout value objects."""

from __future__ import annotations

import pytest

from bioetl.domain.types.contract_rollout import ContractRolloutPolicy

pytestmark = pytest.mark.unit


def test_single_rollout_policy_builds_active_read_and_write_targets() -> None:
    policy = ContractRolloutPolicy(
        contract_ref="gold.publication",
        active_version="1.0.0",
        read_order=("1.0.0",),
        write_versions=("1.0.0",),
    )

    read_targets = policy.read_targets("publication")
    write_targets = policy.write_targets("publication")

    assert read_targets == write_targets
    assert read_targets[0].logical_name == "publication"
    assert read_targets[0].contract_ref == "gold.publication"
    assert read_targets[0].contract_version == "1.0.0"
    assert read_targets[0].is_active is True


def test_dual_rollout_policy_marks_only_active_version() -> None:
    policy = ContractRolloutPolicy(
        contract_ref="gold.publication",
        active_version="2.0.0",
        mode="dual_read_write",
        read_order=("2.0.0", "1.0.0"),
        write_versions=("1.0.0", "2.0.0"),
        affects_hash=True,
    )

    assert [
        target.contract_version for target in policy.read_targets("publication")
    ] == [
        "2.0.0",
        "1.0.0",
    ]
    assert [target.is_active for target in policy.write_targets("publication")] == [
        False,
        True,
    ]
    assert policy.affects_hash is True


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        (
            {
                "contract_ref": " ",
                "active_version": "1.0.0",
                "read_order": ("1.0.0",),
                "write_versions": ("1.0.0",),
            },
            "contract_ref cannot be empty",
        ),
        (
            {
                "contract_ref": "gold.publication",
                "active_version": " ",
                "read_order": ("1.0.0",),
                "write_versions": ("1.0.0",),
            },
            "active_version cannot be empty",
        ),
        (
            {
                "contract_ref": "gold.publication",
                "active_version": "1.0.0",
                "mode": "bad",
                "read_order": ("1.0.0",),
                "write_versions": ("1.0.0",),
            },
            "mode must be one of",
        ),
        (
            {
                "contract_ref": "gold.publication",
                "active_version": "2.0.0",
                "read_order": ("1.0.0",),
                "write_versions": ("2.0.0",),
            },
            "active_version must be present in read_order",
        ),
        (
            {
                "contract_ref": "gold.publication",
                "active_version": "2.0.0",
                "read_order": ("2.0.0",),
                "write_versions": ("1.0.0",),
            },
            "active_version must be present in write_versions",
        ),
        (
            {
                "contract_ref": "gold.publication",
                "active_version": "1.0.0",
                "read_order": ("1.0.0", "1.0.0"),
                "write_versions": ("1.0.0",),
            },
            "read_order must not contain duplicate versions",
        ),
        (
            {
                "contract_ref": "gold.publication",
                "active_version": "1.0.0",
                "read_order": ("1.0.0",),
                "write_versions": ("1.0.0", "1.0.0"),
            },
            "write_versions must not contain duplicate versions",
        ),
        (
            {
                "contract_ref": "gold.publication",
                "active_version": "1.0.0",
                "read_order": ("1.0.0", "2.0.0"),
                "write_versions": ("1.0.0",),
            },
            "single mode requires read_order",
        ),
        (
            {
                "contract_ref": "gold.publication",
                "active_version": "1.0.0",
                "read_order": ("1.0.0",),
                "write_versions": ("1.0.0", "2.0.0"),
            },
            "single mode requires write_versions",
        ),
    ],
)
def test_rollout_policy_validates_invariants(
    kwargs: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        ContractRolloutPolicy(**kwargs)  # type: ignore[arg-type]
