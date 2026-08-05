# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
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
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for ContractMigrationService."""

from __future__ import annotations

import pytest

from dataclasses import dataclass
from unittest.mock import MagicMock

from bioetl.application.services.ops.config_service import PipelineInfo
from bioetl.application.services.contract.contract_migration_service import (
    ContractMigrationService,
)


pytestmark = pytest.mark.unit


@dataclass(frozen=True, slots=True)
class _Policy:
    contract_ref: str
    active_version: str
    rollout_mode: str
    read_order: list[str]
    write_versions: list[str]
    affects_hash: bool


def _build_service(
    *,
    policy: _Policy,
    registry_entries: dict[str, dict[str, object]] | None = None,
) -> ContractMigrationService:
    return ContractMigrationService(
        logger=MagicMock(),
        _pipeline_info_loader=lambda _pipeline_name: PipelineInfo(
            name="chembl_activity",
            provider="chembl",
            entity_type="activity",
            silver_table="chembl.activity",
            gold_table="chembl.activity",
        ),
        _contract_policy_loader=lambda _provider, _entity: policy,
        _registry_entries_loader=lambda: registry_entries or {},
    )


def test_plan_pipeline_returns_steady_state_when_no_shadow_versions() -> None:
    service = _build_service(
        policy=_Policy(
            contract_ref="chembl.activity",
            active_version="1.0.0",
            rollout_mode="single",
            read_order=["1.0.0"],
            write_versions=["1.0.0"],
            affects_hash=False,
        )
    )

    plan = service.plan_pipeline("chembl_activity")

    assert plan.shadow_versions == ()
    assert plan.transitions == ()
    assert plan.required_actions == ()
    assert plan.notes == (
        "No shadow contract versions are configured; rollout is in steady-state.",
    )


def test_plan_pipeline_uses_verification_only_when_hash_is_stable() -> None:
    service = _build_service(
        policy=_Policy(
            contract_ref="chembl.activity",
            active_version="1.0.0",
            rollout_mode="dual_read_write",
            read_order=["1.0.0", "2.0.0"],
            write_versions=["1.0.0", "2.0.0"],
            affects_hash=False,
        ),
        registry_entries={
            "chembl.activity": {
                "supported_versions": ["1.0.0", "2.0.0"],
                "migration_guides": {
                    "1.0.0->2.0.0": "docs/migrations/chembl-activity-v2.md"
                },
            }
        },
    )

    plan = service.plan_pipeline("chembl_activity")

    assert plan.shadow_versions == ("2.0.0",)
    assert [action.code for action in plan.required_actions] == [
        "verification_before_cutover"
    ]
    assert plan.transitions[0].migration_guide == (
        "docs/migrations/chembl-activity-v2.md"
    )
    assert plan.supported_versions == ("1.0.0", "2.0.0")


def test_plan_pipeline_requires_rebuilds_when_hash_changes() -> None:
    service = _build_service(
        policy=_Policy(
            contract_ref="chembl.activity",
            active_version="1.0.0",
            rollout_mode="dual_read_write",
            read_order=["1.0.0", "2.0.0"],
            write_versions=["1.0.0", "2.0.0"],
            affects_hash=True,
        )
    )

    plan = service.plan_pipeline("chembl_activity")

    assert [action.code for action in plan.required_actions] == [
        "silver_backfill_rebuild",
        "gold_backfill_rebuild",
        "verification_before_cutover",
    ]
    assert plan.transitions == (plan.transitions[0],)
    assert plan.transitions[0].affects_hash is True
    assert any("historical Silver" in note for note in plan.notes)
