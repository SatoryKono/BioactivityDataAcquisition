"""Focused regression coverage for CR-20260925 P0/P2 closeouts."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bioetl.application.core.batch_executor_loop_helpers import (
    BatchExtractionIterationContext,
    BatchExtractionLoopState,
)
from bioetl.application.core.batch_executor_loop_flow import (
    process_extracted_record_iteration,
)
from bioetl.domain.control_plane.reproducibility_policy import (
    require_input_snapshots,
    validate_exact_replay_boundary,
    validate_required_persistence_profile,
)


@pytest.mark.asyncio
async def test_periodic_checkpoint_uses_confirmed_bronze_after_flush() -> None:
    """#11221: checkpoint count is confirmed bronze; only after flush."""
    checkpoint = AsyncMock()
    progress_state = MagicMock(
        records_fetched=1,
        records_bronze=3,
        records_silver=0,
        records_filtered_out=0,
    )

    async def _process_batch(records: list[object], start_index: int) -> None:
        _ = records, start_index
        progress_state.records_bronze = 4

    memory_manager = MagicMock()
    memory_manager.check_pressure.side_effect = lambda *_a: 1
    memory_manager.maybe_recover.side_effect = lambda size: size
    iteration_context = BatchExtractionIterationContext(
        checkpoint_recovery_service=checkpoint,
        resume_offset=10,
        process_batch=_process_batch,
        memory_manager=memory_manager,
        progress_service=MagicMock(),
        progress_state=progress_state,
        checkpoint_interval=1,
    )
    loop_state = BatchExtractionLoopState(current_batch_size=1, check_interval=10)

    await process_extracted_record_iteration(
        loop_state=loop_state,
        raw_record={"id": "1"},
        shutdown_requested=False,
        records_fetched=0,
        update_batch_size=memory_manager.check_pressure,
        iteration_context=iteration_context,
    )

    checkpoint.save_periodic_checkpoint.assert_awaited_once()
    kwargs = checkpoint.save_periodic_checkpoint.await_args.kwargs
    assert kwargs["records_fetched"] == 4
    assert kwargs["resume_offset"] == 10


@pytest.mark.asyncio
async def test_periodic_checkpoint_skipped_when_batch_not_flushed() -> None:
    """#11221: no periodic checkpoint while records remain buffered."""
    checkpoint = AsyncMock()
    progress_state = MagicMock(
        records_fetched=0,
        records_bronze=2,
        records_silver=0,
        records_filtered_out=0,
    )
    memory_manager = MagicMock()
    memory_manager.check_pressure.side_effect = lambda *_a: 10
    iteration_context = BatchExtractionIterationContext(
        checkpoint_recovery_service=checkpoint,
        resume_offset=0,
        process_batch=AsyncMock(),
        memory_manager=memory_manager,
        progress_service=MagicMock(),
        progress_state=progress_state,
        checkpoint_interval=1,
    )
    loop_state = BatchExtractionLoopState(current_batch_size=10, check_interval=10)

    await process_extracted_record_iteration(
        loop_state=loop_state,
        raw_record={"id": "1"},
        shutdown_requested=False,
        records_fetched=0,
        update_batch_size=memory_manager.check_pressure,
        iteration_context=iteration_context,
    )

    checkpoint.save_periodic_checkpoint.assert_not_awaited()
    assert len(loop_state.batch) == 1


def test_resource_bootstrap_uses_providers_scope() -> None:
    """#11222: bootstrap/cleanup register providers without pipeline registry."""
    with (
        patch(
            "bioetl.composition._resource_management.ensure_runtime_registrations"
        ) as ensure,
        patch(
            "bioetl.composition._resource_management.bootstrap_lifecycle_service",
            return_value=MagicMock(),
        ),
    ):
        from bioetl.composition._registration import RuntimeRegistrationScope
        from bioetl.composition.resources_runtime import get_lifecycle_service

        get_lifecycle_service()

    ensure.assert_called_once_with(scope=RuntimeRegistrationScope.PROVIDERS)


def test_require_input_snapshots_strict_gate() -> None:
    with pytest.raises(RuntimeError, match="immutable input snapshots"):
        require_input_snapshots(
            exact_replay=True,
            required_persistence_profile="replay_ready",
            input_snapshots=(),
        )


def test_validate_exact_replay_boundary_rejects_unsupported() -> None:
    with pytest.raises(RuntimeError, match="support boundary"):
        validate_exact_replay_boundary(
            exact_replay=True,
            strict_exact_replay_supported=False,
        )


def test_validate_required_persistence_profile_domain() -> None:
    with pytest.raises(RuntimeError, match="run manifests"):
        validate_required_persistence_profile(
            manifest_enabled=False,
            ledger_enabled=True,
            required_profile="replay_ready",
            execution_label="test",
        )
