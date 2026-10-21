"""Terminal observations preserve the primary write outcome and parent evidence."""

from __future__ import annotations

import pytest

from bioetl.application.services.run_reports import observations
from bioetl.domain.exceptions.gold_write import GoldWriteFailure
from bioetl.domain.types.gold_contracts import GoldWriteCategory, GoldWriteReceipt
from bioetl.domain.types.gold_contracts_rejects import (
    GoldContractValidationError,
    GoldRejectReasonCode,
    build_gold_contract_reject_reason,
)

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
@pytest.mark.parametrize("contract_failure", [True, False])
async def test_gold_outcome_records_only_proven_schema_failures(contract_failure):
    receipt = GoldWriteReceipt("gold", "1", GoldWriteCategory.NOT_COMMITTED)
    error = GoldWriteFailure(receipt)
    cause = (
        GoldContractValidationError(
            build_gold_contract_reject_reason(
                reason_code=GoldRejectReasonCode.CONTRACT_SCHEMA_FAILURE,
                message="schema rejected",
            )
        )
        if contract_failure
        else OSError("disk unavailable")
    )

    async def operation():
        raise error from cause

    token = observations.bind_run_observations()
    try:
        with pytest.raises(GoldWriteFailure) as caught:
            await observations.observe_gold_write(operation(), 3)
        assert caught.value is error
        assert caught.value.__cause__ is cause
        saved = observations.run_observations()
        if contract_failure:
            assert saved["Data Validation"]["verdict"] == "ERROR"
            assert saved["Data Validation"]["facts"] == {"valid": False, "records": 3}
        else:
            assert "Data Validation" not in saved
    finally:
        observations.reset_run_observations(token)


def test_existing_parent_workflow_observation_is_not_replaced_by_provisional_child():
    token = observations.bind_run_observations()
    try:
        observations.record_run_observation(
            "Workflow",
            verdict="ERROR",
            reason="parent_failed",
            facts={"manifest_id": "parent"},
        )
        before = observations.run_observations()
        observations.ensure_terminal_workflow_observation(
            workflow_run_id="workflow",
            workflow_id="workflow-name",
            workflow_step_id="step",
        )
        assert observations.run_observations() == before
    finally:
        observations.reset_run_observations(token)
