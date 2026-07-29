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
"""Direct unit tests for medallion lifecycle result models."""

from __future__ import annotations

import pytest

from bioetl.application.services.medallion.medallion_types import (
    ClearResult,
    PrepareResult,
    VacuumResult,
)
from bioetl.domain.medallion import ClearPolicy, MedallionPolicy
from bioetl.domain.types import RunType


@pytest.mark.unit
class TestMedallionTypeResults:
    def test_clear_result_total_cleared_sums_layers(self) -> None:
        result = ClearResult(silver_cleared=4, gold_cleared=6, dry_run=False)

        assert result.total_cleared == 10

    def test_vacuum_result_preserves_fields(self) -> None:
        result = VacuumResult(
            silver_files_removed=3,
            gold_files_removed=5,
            skipped=False,
        )

        assert result.silver_files_removed == 3
        assert result.gold_files_removed == 5
        assert result.skipped is False

    def test_prepare_result_keeps_policy_and_clear_result(self) -> None:
        clear_result = ClearResult(silver_cleared=2, gold_cleared=1, dry_run=True)
        policy = MedallionPolicy(clear_policy=ClearPolicy.SILVER_AND_GOLD)

        result = PrepareResult(clear_result=clear_result, policy=policy)

        assert result.clear_result is clear_result
        assert result.policy.clear_policy == ClearPolicy.SILVER_AND_GOLD

    def test_prepare_result_supports_policy_from_run_type(self) -> None:
        result = PrepareResult(
            clear_result=ClearResult(silver_cleared=0, gold_cleared=0, dry_run=False),
            policy=MedallionPolicy.for_run_type(RunType.REBUILD),
        )

        assert result.policy.clear_policy == ClearPolicy.SILVER_AND_GOLD
