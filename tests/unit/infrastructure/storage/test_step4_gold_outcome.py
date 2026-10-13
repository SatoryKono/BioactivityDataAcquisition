"""Gold physical outcome, immutable exceptions and cancellation regressions."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
import pytest
from bioetl.domain.exceptions.base_exceptions import BioETLDomainError
from bioetl.domain.exceptions.gold_write import GoldWriteFailure
from bioetl.infrastructure.storage.gold.commit_outcome import GoldWriteCancelled
from bioetl.domain.types.gold_contracts import (
    GoldWriteCategory as Category,
    GoldWriteReceipt,
)
from bioetl.infrastructure.storage.gold import writer_implementation as impl
from bioetl.infrastructure.storage.gold.commit_outcome import (
    await_physical_commit,
    receipt_for,
)
from bioetl.infrastructure.storage.gold.pipeline_helpers import GoldWriteRequest

pytestmark = pytest.mark.unit


def request():
    return GoldWriteRequest(
        "synthetic", [{"id": 1}], MagicMock(), contract_version="1.0.0"
    )


def writer():
    return SimpleNamespace(
        _prepare_write_gold=AsyncMock(return_value=MagicMock()),
        _dispatch_write=AsyncMock(),
        _post_write_gold=AsyncMock(),
        logger=MagicMock(),
    )


@pytest.mark.asyncio
async def test_single_complete_receipt():
    result = await impl._write_single_target_impl(writer(), request=request())
    assert result.category == Category.COMPLETE
    assert result.committed_targets == ("synthetic",)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [BioETLDomainError("synthetic"), TypeError("synthetic"), OSError("synthetic")],
)
async def test_single_postwrite_retains_frozen_original(error):
    host = writer()
    host._post_write_gold.side_effect = error
    with pytest.raises(GoldWriteFailure) as found:
        await impl._write_single_target_impl(host, request=request())
    assert found.value.__cause__ is error
    assert found.value.receipt.category == Category.COMMITTED_POSTWRITE_PENDING
    assert not hasattr(error, "gold_receipt")
    assert error.__traceback__ is not None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("stage", "expected"),
    [
        ("_prepare_write_gold", Category.NOT_COMMITTED),
        ("_dispatch_write", Category.UNKNOWN),
        ("_post_write_gold", Category.COMMITTED_POSTWRITE_PENDING),
    ],
)
async def test_single_cancellation_preserves_meaning(stage, expected):
    host = writer()
    getattr(host, stage).side_effect = asyncio.CancelledError("synthetic")
    with pytest.raises(GoldWriteCancelled) as found:
        await impl._write_single_target_impl(host, request=request())
    assert isinstance(found.value, asyncio.CancelledError)
    assert found.value.receipt.category == expected
    if stage != "_post_write_gold":
        host._post_write_gold.assert_not_awaited()


@pytest.mark.asyncio
async def test_physical_cancellation_drains_without_repeating_commit():
    entered = asyncio.Event()
    finish = asyncio.Event()
    calls = []

    async def commit():
        calls.append("started")
        entered.set()
        await finish.wait()
        calls.append("committed")

    task = asyncio.create_task(await_physical_commit(commit, receipt_for("synthetic")))
    await entered.wait()
    task.cancel()
    await asyncio.sleep(0)
    task.cancel()
    finish.set()
    with pytest.raises(GoldWriteCancelled) as found:
        await task
    assert task.cancelled()
    assert found.value.receipt.category == Category.COMMITTED_POSTWRITE_PENDING
    assert calls == ["started", "committed"]


@pytest.mark.asyncio
async def test_physical_error_is_unknown_not_retryable():
    calls = []

    async def uncertain():
        calls.append(1)
        raise OSError("synthetic uncertain commit")

    with pytest.raises(GoldWriteFailure) as found:
        await await_physical_commit(uncertain, receipt_for("synthetic"))
    assert found.value.receipt.category == Category.UNKNOWN
    assert calls == [1]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure", [TypeError("synthetic"), asyncio.CancelledError("synthetic")]
)
@pytest.mark.parametrize("committed", [False, True])
async def test_dual_second_failure_retains_proven_targets(
    monkeypatch, failure, committed
):
    host = writer()
    host._contract_rollout_policy = SimpleNamespace(
        write_versions=["1.0.0", "2.0.0"], active_version="2.0.0"
    )
    seen = []

    async def single(*, request):
        seen.append(request.table_name)
        if len(seen) == 1:
            return GoldWriteReceipt(
                request.table_name,
                request.contract_version,
                Category.COMPLETE,
                (request.table_name,),
            )
        receipt = GoldWriteReceipt(
            request.table_name,
            request.contract_version,
            Category.COMMITTED_POSTWRITE_PENDING if committed else Category.UNKNOWN,
        )
        wrapper = (
            GoldWriteCancelled
            if isinstance(failure, asyncio.CancelledError)
            else GoldWriteFailure
        )
        raise wrapper(receipt) from failure

    host._write_single_target = single
    monkeypatch.setattr(
        impl, "_project_records_for_gold_schema", lambda records, schema: records
    )
    wrapper = (
        GoldWriteCancelled
        if isinstance(failure, asyncio.CancelledError)
        else GoldWriteFailure
    )
    with pytest.raises(wrapper) as found:
        await impl._write_dual_targets_impl(
            host,
            request=request(),
            schema_policy=SimpleNamespace(for_version=lambda _: MagicMock()),
        )
    assert found.value.__cause__ is failure
    assert found.value.receipt.committed_targets == tuple(
        seen if committed else seen[:1]
    )
    assert host.logger.error.call_args.kwargs["committed_targets"]


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["value_error", "pending", "identity"])
async def test_dual_does_not_invent_or_discard_commit(monkeypatch, kind):
    host = writer()
    host._contract_rollout_policy = SimpleNamespace(
        write_versions=["1.0.0", "2.0.0"], active_version="2.0.0"
    )
    seen = []

    async def single(*, request):
        seen.append(request.table_name)
        if len(seen) == 2 and kind == "value_error":
            raise ValueError("synthetic uncertain outcome")
        pending = len(seen) == 2 and kind == "pending"
        return GoldWriteReceipt(
            "wrong" if len(seen) == 2 and kind == "identity" else request.table_name,
            request.contract_version,
            Category.COMMITTED_POSTWRITE_PENDING if pending else Category.COMPLETE,
            (request.table_name,),
        )

    host._write_single_target = single
    monkeypatch.setattr(
        impl, "_project_records_for_gold_schema", lambda records, schema: records
    )
    with pytest.raises(GoldWriteFailure) as found:
        await impl._write_dual_targets_impl(
            host,
            request=request(),
            schema_policy=SimpleNamespace(for_version=lambda _: MagicMock()),
        )
    assert found.value.receipt.category == (
        Category.COMMITTED_POSTWRITE_PENDING if kind == "pending" else Category.UNKNOWN
    )
    assert found.value.receipt.committed_targets == tuple(
        seen if kind == "pending" else seen[:1]
    )


@pytest.mark.asyncio
async def test_prepare_failure_has_explicit_noncommit_receipt():
    host = writer()
    original = ValueError("synthetic invalid schema")
    host._prepare_write_gold.side_effect = original
    with pytest.raises(GoldWriteFailure) as found:
        await impl._write_single_target_impl(host, request=request())
    assert found.value.__cause__ is original
    assert found.value.receipt.category == Category.NOT_COMMITTED
    host._dispatch_write.assert_not_awaited()


@pytest.mark.asyncio
async def test_outcome_wrapper_keeps_operational_failure_handlers():
    from bioetl.application.services.batch_processing.operation_errors import (
        OPERATION_ERRORS,
    )
    from bioetl.application.core.batch_processing_runtime import execute_with_layer_span

    host = writer()
    error = TypeError("synthetic programming failure")
    host._post_write_gold.side_effect = error
    tracing = MagicMock()
    on_error = MagicMock()
    with pytest.raises(GoldWriteFailure) as found:
        await execute_with_layer_span(
            tracing=tracing,
            name="gold",
            coro=impl._write_single_target_impl(host, request=request()),
            batch_id="synthetic",
            count=1,
            on_error=on_error,
        )
    assert isinstance(found.value, OPERATION_ERRORS)
    from bioetl.domain.error_classifier import ErrorClassifier

    assert ErrorClassifier().classify(found.value).is_critical()
    assert not ErrorClassifier().classify(found.value).is_recoverable()
    assert found.value.__cause__ is error
    on_error.assert_called_once_with(found.value)
    tracing.end_span.assert_called_once_with(
        tracing.start_layer_span.return_value, found.value
    )


@pytest.mark.asyncio
async def test_cancel_before_physical_task_enters_proves_noncommit(monkeypatch):
    original_create_task = asyncio.create_task
    spawned = asyncio.Event()
    release = asyncio.Event()
    calls = []

    async def physical():
        calls.append(1)

    def deferred_create_task(coro):
        async def deferred():
            spawned.set()
            try:
                await release.wait()
                return await coro
            finally:
                coro.close()

        return original_create_task(deferred())

    monkeypatch.setattr(asyncio, "create_task", deferred_create_task)
    task = original_create_task(
        await_physical_commit(physical, receipt_for("synthetic"))
    )
    await spawned.wait()
    task.cancel()
    with pytest.raises(GoldWriteCancelled) as found:
        await task
    assert found.value.receipt.category == Category.NOT_COMMITTED
    assert calls == []


@pytest.mark.asyncio
async def test_self_cancelled_physical_task_has_unknown_outcome():
    async def physical():
        raise asyncio.CancelledError("synthetic self cancellation")

    with pytest.raises(GoldWriteCancelled) as found:
        await await_physical_commit(physical, receipt_for("synthetic"))
    assert found.value.receipt.category == Category.UNKNOWN
    assert found.value.receipt.committed_targets == ()


@pytest.mark.asyncio
async def test_outer_cancellation_with_failed_physical_drain_is_unknown():
    entered = asyncio.Event()
    release = asyncio.Event()

    async def physical():
        entered.set()
        await release.wait()
        raise OSError("synthetic uncertain outcome")

    task = asyncio.create_task(
        await_physical_commit(physical, receipt_for("synthetic"))
    )
    await entered.wait()
    task.cancel()
    await asyncio.sleep(0)
    release.set()
    with pytest.raises(GoldWriteCancelled) as found:
        await task
    assert found.value.receipt.category == Category.UNKNOWN
    assert found.value.receipt.committed_targets == ()


@pytest.mark.asyncio
async def test_pending_cancellation_before_helper_never_starts_physical_write():
    calls = []

    async def physical():
        calls.append("write")

    async def caller():
        asyncio.current_task().cancel()
        await await_physical_commit(physical, receipt_for("synthetic"))

    task = asyncio.create_task(caller())
    with pytest.raises(GoldWriteCancelled) as found:
        await task
    assert found.value.receipt.category == Category.NOT_COMMITTED
    assert task.cancelled()
    assert calls == []


@pytest.mark.parametrize("category", list(Category))
def test_complete_receipt_guard_keeps_incomplete_proof(category):
    from bioetl.domain.types.gold_contracts import require_complete_gold_receipt

    receipt = GoldWriteReceipt("synthetic", "1.0.0", category)
    if category == Category.COMPLETE:
        assert require_complete_gold_receipt(receipt) is receipt
    else:
        with pytest.raises(GoldWriteFailure) as found:
            require_complete_gold_receipt(receipt)
        assert found.value.receipt is receipt


def test_receipt_guard_rejects_untyped_success():
    from bioetl.domain.types.gold_contracts import require_complete_gold_receipt

    with pytest.raises(TypeError):
        require_complete_gold_receipt(None)


@pytest.mark.parametrize("failure", [SystemExit(2), KeyboardInterrupt()])
def test_phase_boundary_preserves_process_exit(failure):
    from bioetl.infrastructure.storage.gold.commit_outcome import GoldOutcomeBoundary

    with pytest.raises(type(failure)) as found:
        with GoldOutcomeBoundary(receipt_for("synthetic")):
            raise failure
    assert found.value is failure


@pytest.mark.asyncio
@pytest.mark.parametrize("primary_type", [ValueError, asyncio.CancelledError])
@pytest.mark.parametrize("diagnostic_type", [TypeError, asyncio.CancelledError])
async def test_dual_failure_logging_cannot_discard_primary_outcome(
    monkeypatch, primary_type, diagnostic_type
):
    host = writer()
    host._contract_rollout_policy = SimpleNamespace(
        write_versions=["1.0.0", "2.0.0"], active_version="2.0.0"
    )
    committed = []
    attempts = []
    primary = primary_type("synthetic second target")
    diagnostic = diagnostic_type("synthetic diagnostic publication")

    async def single(*, request):
        attempts.append(request.table_name)
        if committed:
            raise primary
        committed.append(request.table_name)
        return GoldWriteReceipt(
            request.table_name,
            request.contract_version,
            Category.COMPLETE,
            (request.table_name,),
        )

    host._write_single_target = single
    host.logger.error.side_effect = diagnostic
    monkeypatch.setattr(
        impl, "_project_records_for_gold_schema", lambda records, schema: records
    )
    wrapper = (
        GoldWriteCancelled
        if asyncio.CancelledError in (primary_type, diagnostic_type)
        else GoldWriteFailure
    )
    with pytest.raises(wrapper) as found:
        await impl._write_dual_targets_impl(
            host,
            request=request(),
            schema_policy=SimpleNamespace(for_version=lambda _: MagicMock()),
        )
    assert len(attempts) == 2
    assert found.value.receipt.committed_targets == tuple(committed)
    assert found.value.__cause__ is primary
    assert found.value.diagnostic_error is diagnostic


@pytest.mark.asyncio
@pytest.mark.parametrize("contract_error", [False, True])
async def test_precommit_validation_preserves_error_classification(contract_error):
    from bioetl.domain.error_classifier import ErrorClassifier
    from bioetl.domain.types.gold_contracts import (
        GoldContractValidationError,
        GoldRejectReason,
        GoldRejectReasonCode,
    )

    original = (
        GoldContractValidationError(
            GoldRejectReason(
                reason_code=GoldRejectReasonCode.CONTRACT_SCHEMA_FAILURE,
                message="synthetic validation",
            )
        )
        if contract_error
        else ValueError("synthetic validation")
    )
    host = writer()
    host._prepare_write_gold.side_effect = original
    with pytest.raises(GoldWriteFailure) as found:
        await impl._write_single_target_impl(host, request=request())
    assert ErrorClassifier().classify(found.value) == ErrorClassifier().classify(
        original
    )
    assert found.value.get_reason_code() == "gold_write_validation_failed"
    assert found.value.receipt.category == Category.NOT_COMMITTED
    assert found.value.__cause__ is original
    host._dispatch_write.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("postwrite", [None, ValueError, asyncio.CancelledError])
async def test_merged_outcome_binds_schema_contract_version(monkeypatch, postwrite):
    from bioetl.infrastructure.storage.gold import io_execution

    schema = SimpleNamespace(metadata={"contract_version": "3.1.4"})
    prepared = SimpleNamespace(
        request=SimpleNamespace(table_name="synthetic", schema=schema)
    )
    monkeypatch.setattr(io_execution, "_write_gold_merged_delta", AsyncMock())
    monkeypatch.setattr(
        io_execution,
        "_export_gold_merged_csv",
        AsyncMock(
            side_effect=postwrite("synthetic postwrite") if postwrite else None,
        ),
    )
    monkeypatch.setattr(io_execution, "_write_gold_merged_sidecar", AsyncMock())
    if postwrite:
        wrapper = (
            GoldWriteCancelled
            if postwrite is asyncio.CancelledError
            else GoldWriteFailure
        )
        with pytest.raises(wrapper) as found:
            await io_execution._complete_gold_merged_write(writer(), prepared)
        receipt = found.value.receipt
        assert receipt.category == Category.COMMITTED_POSTWRITE_PENDING
    else:
        receipt = await io_execution._complete_gold_merged_write(writer(), prepared)
        assert receipt.category == Category.COMPLETE
    assert receipt.contract_version == "3.1.4"


@pytest.mark.asyncio
@pytest.mark.parametrize("previous_commit", [False, True])
@pytest.mark.parametrize("diagnostic_failure", [False, True])
async def test_dual_validation_classification_depends_on_proven_commits(
    monkeypatch,
    previous_commit,
    diagnostic_failure,
):
    from bioetl.domain.error_classifier import ErrorClassifier
    from bioetl.domain.exceptions.gold_write import GoldWriteValidationFailure
    from bioetl.domain.types import ErrorType

    host = writer()
    host._contract_rollout_policy = SimpleNamespace(
        write_versions=["1.0.0", "2.0.0"],
        active_version="2.0.0",
    )
    attempts = []
    original = ValueError("synthetic validation")

    async def single(*, request):
        attempts.append(request.table_name)
        if previous_commit and len(attempts) == 1:
            return GoldWriteReceipt(
                request.table_name,
                request.contract_version,
                Category.COMPLETE,
                (request.table_name,),
            )
        raise GoldWriteValidationFailure(
            GoldWriteReceipt(
                request.table_name, request.contract_version, Category.NOT_COMMITTED
            ),
            original,
        ) from original

    host._write_single_target = single
    if diagnostic_failure:
        host.logger.error.side_effect = TypeError("synthetic diagnostics")
    monkeypatch.setattr(
        impl, "_project_records_for_gold_schema", lambda records, schema: records
    )
    with pytest.raises(GoldWriteFailure) as found:
        await impl._write_dual_targets_impl(
            host,
            request=request(),
            schema_policy=SimpleNamespace(for_version=lambda _: MagicMock()),
        )
    assert found.value.receipt.category == Category.NOT_COMMITTED
    assert bool(found.value.receipt.committed_targets) is previous_commit
    assert found.value.__cause__ is original
    assert ErrorClassifier().classify(found.value) == (
        ErrorType.DB_UNAVAILABLE if previous_commit else ErrorType.INVALID_DATA
    )
    assert len(attempts) == (2 if previous_commit else 1)


@pytest.mark.parametrize("original", [KeyboardInterrupt(), SystemExit(1)])
def test_gold_outcome_boundary_preserves_process_control(original):
    from bioetl.infrastructure.storage.gold.commit_outcome import GoldOutcomeBoundary

    with pytest.raises(type(original)) as found:
        with GoldOutcomeBoundary(receipt_for("synthetic")):
            raise original
    assert found.value is original


def test_gold_outcome_boundary_adapts_domain_cancellation():
    from bioetl.infrastructure.storage.gold.commit_outcome import GoldOutcomeBoundary

    receipt = receipt_for("synthetic", category=Category.COMMITTED_POSTWRITE_PENDING)
    from bioetl.domain.exceptions.gold_write import (
        GoldWriteCancelled as DomainGoldWriteCancelled,
    )

    original = DomainGoldWriteCancelled(receipt)
    with pytest.raises(asyncio.CancelledError) as found:
        with GoldOutcomeBoundary(receipt):
            raise original
    assert isinstance(found.value, GoldWriteCancelled)
    assert found.value.receipt is receipt
    assert not isinstance(found.value, Exception)
    assert found.value.__cause__ is original


@pytest.mark.asyncio
async def test_physical_commit_drains_many_cancellations_without_recursion():
    started, release = asyncio.Event(), asyncio.Event()

    async def physical():
        started.set()
        await release.wait()

    pending = asyncio.create_task(
        await_physical_commit(physical, receipt_for("synthetic"))
    )
    await started.wait()
    for _ in range(1500):
        pending.cancel()
        await asyncio.sleep(0)
    assert not pending.done()
    release.set()
    with pytest.raises(GoldWriteCancelled) as found:
        await pending
    assert isinstance(found.value, asyncio.CancelledError)
    assert found.value.receipt.category == Category.COMMITTED_POSTWRITE_PENDING
    assert found.value.receipt.committed_targets == ("synthetic",)
