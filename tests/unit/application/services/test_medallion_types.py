"""Direct unit tests for medallion lifecycle result models."""

from __future__ import annotations

import pytest

from bioetl.application.services.medallion_types import (
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
