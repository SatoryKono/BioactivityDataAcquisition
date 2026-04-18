"""Coverage boost tests for silver_writer_delta_mixin.py.

Targets uncovered lines: 69-70, 130, 142-158, 195, 275, 297, 333.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pyarrow as pa
import pytest

from bioetl.domain.exceptions import (
    DeltaTransactionError,
    MergeConflictError,
    SchemaViolationError,
)
from bioetl.domain.medallion import SilverWriteMode
from bioetl.infrastructure.storage.silver.delta_mixin import (
    SilverWriterDeltaMixin,
)
from bioetl.infrastructure.storage.silver.delta_helpers import (
    _build_dispatch_policy,
    _build_merge_update_predicate,
    _DeltaWriteRequest,
    _MergeExecutionTimeoutError,
    _dispatch_request_by_mode,
    _raise_domain_write_error,
    _select_dispatch_handler,
)
from bioetl.infrastructure.storage.delta.resilience import (
    AdaptiveRetryPolicy,
    SilverMergeResiliencePolicy,
)


def _make_policy(
    commit_retries: int = 0,
    timeout_retries: int = 0,
    timeout_seconds: float = 30.0,
    delay: float = 0.0,
) -> SilverMergeResiliencePolicy:
    """Build a test resilience policy."""
    return SilverMergeResiliencePolicy(
        execution_timeout_seconds=timeout_seconds,
        commit_retry=AdaptiveRetryPolicy(
            enabled=commit_retries > 0,
            max_retries=commit_retries,
            base_delay_seconds=delay,
            max_delay_seconds=delay * 2 or 0.01,
            jitter_seconds=0.0,
        ),
        timeout_retry=AdaptiveRetryPolicy(
            enabled=timeout_retries > 0,
            max_retries=timeout_retries,
            base_delay_seconds=delay,
            max_delay_seconds=delay * 2 or 0.01,
            jitter_seconds=0.0,
        ),
    )


class _ConcreteDeltaMixin(SilverWriterDeltaMixin):
    """Concrete subclass for testing the mixin."""

    def __init__(
        self,
        policy: SilverMergeResiliencePolicy | None = None,
        metrics: MagicMock | None = None,
    ) -> None:
        self.logger = MagicMock()
        self.logger.info = MagicMock()
        self.logger.warning = MagicMock()
        self.logger.error = MagicMock()
        self.logger.debug = MagicMock()
        self._metrics = metrics
        self._merge_resilience_policy = policy or _make_policy()


def _make_arrow_table(n: int = 2) -> pa.Table:
    return pa.table(
        {
            "id": list(range(n)),
            "value": [float(i) for i in range(n)],
            "_run_type": ["incremental"] * n,
        }
    )


@pytest.mark.unit
class TestWriteDeleteLines:
    """Tests for _write_delete (lines 69-70)."""

    @pytest.mark.asyncio
    async def test_write_delete_calls_overwrite(self) -> None:
        """Lines 69-70: _write_delete uses overwrite mode."""
        mixin = _ConcreteDeltaMixin()
        data = _make_arrow_table()
        request = _DeltaWriteRequest(
            validated_mode=SilverWriteMode.DELETE,
            table_path="path/to/table",
            arrow_data=data,
            primary_keys=[],
            partition_cols=None,
        )

        write_calls: list[dict] = []

        def fake_write_deltalake(**kwargs: object) -> None:
            write_calls.append(kwargs)

        mock_module = MagicMock()
        mock_module.write_deltalake = fake_write_deltalake

        with patch.object(
            mixin, "_load_silver_writer_module", return_value=mock_module
        ):
            await mixin._write_delete(request)

        assert len(write_calls) == 1
        assert write_calls[0]["mode"] == "overwrite"
        assert write_calls[0]["schema_mode"] == "overwrite"


@pytest.mark.unit
def test_build_merge_update_predicate_ignores_run_type_precedence() -> None:
    """Silver merge predicate must stay content-hash based even if _run_type exists."""
    records = pa.table(
        {
            "id": [1],
            "content_hash": ["hash-1"],
            "_run_type": ["rebuild"],
        }
    )

    predicate = _build_merge_update_predicate(records)

    assert "source.content_hash <> target.content_hash" in predicate
    assert "_run_type" not in predicate

    @pytest.mark.asyncio
    async def test_write_delete_with_partition_cols(self) -> None:
        """Lines 69-70: partition_cols passed through."""
        mixin = _ConcreteDeltaMixin()
        data = _make_arrow_table()
        request = _DeltaWriteRequest(
            validated_mode=SilverWriteMode.DELETE,
            table_path="path/table",
            arrow_data=data,
            primary_keys=[],
            partition_cols=["date"],
        )

        write_calls: list[dict] = []

        def fake_write(**kwargs: object) -> None:
            write_calls.append(kwargs)

        mock_module = MagicMock()
        mock_module.write_deltalake = fake_write

        with patch.object(
            mixin, "_load_silver_writer_module", return_value=mock_module
        ):
            await mixin._write_delete(request)

        assert write_calls[0]["partition_by"] == ["date"]

    @pytest.mark.asyncio
    async def test_write_append_calls_append_mode(self) -> None:
        """Append writes should forward mode and partitioning to write_deltalake."""
        mixin = _ConcreteDeltaMixin()
        data = _make_arrow_table()
        request = _DeltaWriteRequest(
            validated_mode=SilverWriteMode.APPEND,
            table_path="path/table",
            arrow_data=data,
            primary_keys=[],
            partition_cols=["date"],
        )

        write_calls: list[dict] = []

        def fake_write_deltalake(**kwargs: object) -> None:
            write_calls.append(kwargs)

        mock_module = MagicMock()
        mock_module.write_deltalake = fake_write_deltalake

        with patch.object(
            mixin, "_load_silver_writer_module", return_value=mock_module
        ):
            await mixin._write_append(request)

        assert len(write_calls) == 1
        assert write_calls[0]["mode"] == "append"
        assert write_calls[0]["partition_by"] == ["date"]
        assert "schema_mode" not in write_calls[0]

    @pytest.mark.asyncio
    async def test_write_append_forwards_schema_mode_when_requested(self) -> None:
        """Append evolve writes should pass schema_mode through to Delta."""
        mixin = _ConcreteDeltaMixin()
        data = _make_arrow_table()
        request = _DeltaWriteRequest(
            validated_mode=SilverWriteMode.APPEND,
            table_path="path/table",
            arrow_data=data,
            primary_keys=[],
            partition_cols=None,
            schema_mode="merge",
        )

        write_calls: list[dict] = []

        def fake_write_deltalake(**kwargs: object) -> None:
            write_calls.append(kwargs)

        mock_module = MagicMock()
        mock_module.write_deltalake = fake_write_deltalake

        with patch.object(
            mixin, "_load_silver_writer_module", return_value=mock_module
        ):
            await mixin._write_append(request)

        assert len(write_calls) == 1
        assert write_calls[0]["mode"] == "append"
        assert write_calls[0]["schema_mode"] == "merge"


@pytest.mark.unit
class TestWriteMergeRetrySuccess:
    """Tests for _write_merge retry paths (lines 130, 142-158)."""

    @pytest.mark.asyncio
    async def test_merge_records_builds_predicate_and_executes_merge_chain(
        self,
    ) -> None:
        """Merge path should build the expected predicate and execute full chain."""
        mixin = _ConcreteDeltaMixin()
        data = _make_arrow_table()
        dt = MagicMock()
        merge_builder = MagicMock()
        dt.merge.return_value = merge_builder
        merge_builder.when_matched_update_all.return_value = merge_builder
        merge_builder.when_not_matched_insert_all.return_value = merge_builder

        await mixin._merge_records(
            dt,
            data,
            ["id", "value"],
            "path/table",
            timeout_seconds=5.0,
        )

        dt.merge.assert_called_once_with(
            source=data,
            predicate="target.id = source.id AND target.value = source.value",
            source_alias="source",
            target_alias="target",
            merge_schema=False,
        )
        merge_builder.when_matched_update_all.assert_called_once()
        matched_kwargs = merge_builder.when_matched_update_all.call_args.kwargs
        assert matched_kwargs["predicate"] == "true"
        merge_builder.when_not_matched_insert_all.assert_called_once()
        merge_builder.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_merge_records_enables_merge_schema_when_requested(self) -> None:
        """Merge path should opt into Delta schema evolution when payload requests it."""
        mixin = _ConcreteDeltaMixin()
        data = _make_arrow_table()
        dt = MagicMock()
        merge_builder = MagicMock()
        dt.merge.return_value = merge_builder
        merge_builder.when_matched_update_all.return_value = merge_builder
        merge_builder.when_not_matched_insert_all.return_value = merge_builder

        await mixin._merge_records(
            dt,
            data,
            ["id"],
            "path/table",
            timeout_seconds=5.0,
            merge_schema=True,
        )

        dt.merge.assert_called_once_with(
            source=data,
            predicate="target.id = source.id",
            source_alias="source",
            target_alias="target",
            merge_schema=True,
        )

    @pytest.mark.asyncio
    async def test_write_merge_logs_recovery_after_retry(self) -> None:
        """Line 130: logs info when commit_retry_count > 0 on success."""
        from deltalake.exceptions import CommitFailedError

        policy = _make_policy(commit_retries=3, delay=0.0)
        mixin = _ConcreteDeltaMixin(policy=policy)
        data = _make_arrow_table()
        request = _DeltaWriteRequest(
            validated_mode=SilverWriteMode.MERGE,
            table_path="path/table",
            arrow_data=data,
            primary_keys=["id"],
            partition_cols=None,
        )

        call_count = {"count": 0}

        mock_module = MagicMock()

        def fake_delta_table(path: str) -> MagicMock:
            dt = MagicMock()
            dt.merge.return_value = dt
            dt.when_matched_update_all.return_value = dt
            dt.when_not_matched_insert_all.return_value = dt

            def fake_execute() -> None:
                call_count["count"] += 1
                if call_count["count"] == 1:
                    raise CommitFailedError("conflict")

            dt.execute = fake_execute
            return dt

        mock_module.DeltaTable = fake_delta_table
        mock_module.TableNotFoundError = type("TableNotFoundError", (Exception,), {})

        with patch.object(
            mixin, "_load_silver_writer_module", return_value=mock_module
        ):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                await mixin._write_merge(request)

        # Should log recovery
        mixin.logger.info.assert_called()
        recovery_calls = [
            call
            for call in mixin.logger.info.call_args_list
            if call.args and call.args[0] == "silver_merge_recovered_after_retry"
        ]
        assert len(recovery_calls) >= 1

    @pytest.mark.asyncio
    async def test_write_merge_table_not_found_falls_back_to_append(
        self,
    ) -> None:
        """Lines 142-143: DeltaTableNotFoundError triggers write_append fallback."""
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        policy = _make_policy()
        mixin = _ConcreteDeltaMixin(policy=policy)
        data = _make_arrow_table()
        request = _DeltaWriteRequest(
            validated_mode=SilverWriteMode.MERGE,
            table_path="path/table",
            arrow_data=data,
            primary_keys=["id"],
            partition_cols=None,
        )

        mock_module = MagicMock()
        mock_module.DeltaTable = MagicMock(
            side_effect=DeltaTableNotFoundError("not found")
        )
        mock_module.TableNotFoundError = DeltaTableNotFoundError

        append_calls: list[dict] = []

        def fake_write_deltalake(**kwargs: object) -> None:
            append_calls.append(kwargs)

        mock_module.write_deltalake = fake_write_deltalake

        with patch.object(
            mixin, "_load_silver_writer_module", return_value=mock_module
        ):
            await mixin._write_merge(request)

        assert len(append_calls) == 1
        assert append_calls[0]["mode"] == "append"

    @pytest.mark.asyncio
    async def test_write_merge_commit_retries_exhausted_raises(self) -> None:
        """Lines 144-147: CommitFailedError after max retries re-raises."""
        from deltalake.exceptions import CommitFailedError

        # Only 1 retry allowed
        policy = _make_policy(commit_retries=1, delay=0.0)
        mixin = _ConcreteDeltaMixin(policy=policy)
        data = _make_arrow_table()
        request = _DeltaWriteRequest(
            validated_mode=SilverWriteMode.MERGE,
            table_path="path/table",
            arrow_data=data,
            primary_keys=["id"],
            partition_cols=None,
        )

        mock_module = MagicMock()

        def always_conflict_dt(path: str) -> MagicMock:
            dt = MagicMock()
            dt.merge.return_value = dt
            dt.when_matched_update_all.return_value = dt
            dt.when_not_matched_insert_all.return_value = dt
            dt.execute = MagicMock(side_effect=CommitFailedError("always conflict"))
            return dt

        mock_module.DeltaTable = always_conflict_dt
        mock_module.TableNotFoundError = type("TableNotFoundError", (Exception,), {})

        with patch.object(
            mixin, "_load_silver_writer_module", return_value=mock_module
        ):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(CommitFailedError):
                    await mixin._write_merge(request)

        # Final telemetry should be emitted
        mixin.logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_write_merge_timeout_retry_exhausted_raises_delta_transaction_error(
        self,
    ) -> None:
        """Lines 159-172: Timeout retries exhausted raises DeltaTransactionError."""
        # Use 0 timeout retries so it exhausts immediately
        policy = _make_policy(timeout_retries=0, timeout_seconds=30.0, delay=0.0)
        mixin = _ConcreteDeltaMixin(policy=policy)
        data = _make_arrow_table()
        request = _DeltaWriteRequest(
            validated_mode=SilverWriteMode.MERGE,
            table_path="path/table",
            arrow_data=data,
            primary_keys=["id"],
            partition_cols=None,
        )

        # Directly mock _merge_records to raise _MergeExecutionTimeoutError
        async def always_timeout(
            dt, records, primary_keys, table_path, *, timeout_seconds, merge_schema
        ):
            _ = merge_schema
            await asyncio.sleep(0)
            raise _MergeExecutionTimeoutError(timeout_seconds)

        mock_module = MagicMock()

        def dt_factory(path: str) -> MagicMock:
            return MagicMock()

        mock_module.DeltaTable = dt_factory
        mock_module.TableNotFoundError = type("TableNotFoundError", (Exception,), {})

        with patch.object(
            mixin, "_load_silver_writer_module", return_value=mock_module
        ):
            with patch.object(mixin, "_merge_records", side_effect=always_timeout):
                with pytest.raises(DeltaTransactionError):
                    await mixin._write_merge(request)


@pytest.mark.unit
class TestDispatchWriteMode:
    """Tests for _dispatch_write (line 195)."""

    @pytest.mark.asyncio
    async def test_dispatch_delete_mode(self) -> None:
        """Line 194-195: DELETE mode dispatches to _write_delete."""
        mixin = _ConcreteDeltaMixin()
        data = _make_arrow_table()
        request = _DeltaWriteRequest(
            validated_mode=SilverWriteMode.DELETE,
            table_path="path",
            arrow_data=data,
            primary_keys=[],
            partition_cols=None,
        )

        with patch.object(mixin, "_write_delete", new_callable=AsyncMock) as mock_del:
            await mixin._dispatch_write(request)
        mock_del.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_append_mode(self) -> None:
        """Line 195: APPEND mode dispatches to _write_append."""
        mixin = _ConcreteDeltaMixin()
        data = _make_arrow_table()
        request = _DeltaWriteRequest(
            validated_mode=SilverWriteMode.APPEND,
            table_path="path",
            arrow_data=data,
            primary_keys=[],
            partition_cols=None,
        )

        with patch.object(mixin, "_write_append", new_callable=AsyncMock) as mock_app:
            await mixin._dispatch_write(request)
        mock_app.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_merge_mode(self) -> None:
        """Line 195: MERGE mode dispatches to _write_merge."""
        mixin = _ConcreteDeltaMixin()
        data = _make_arrow_table()
        request = _DeltaWriteRequest(
            validated_mode=SilverWriteMode.MERGE,
            table_path="path",
            arrow_data=data,
            primary_keys=["id"],
            partition_cols=None,
        )

        with patch.object(mixin, "_write_merge", new_callable=AsyncMock) as mock_merge:
            await mixin._dispatch_write(request)
        mock_merge.assert_called_once()


@pytest.mark.unit
class TestDispatchRequestByMode:
    """Direct tests for the module-level mode dispatch helper."""

    @pytest.mark.asyncio
    async def test_dispatch_request_by_mode_routes_append(self) -> None:
        """Append requests should route to the append handler."""
        request = _DeltaWriteRequest(
            validated_mode=SilverWriteMode.APPEND,
            table_path="path",
            arrow_data=_make_arrow_table(),
            primary_keys=[],
            partition_cols=None,
        )
        write_delete = AsyncMock()
        write_append = AsyncMock()
        write_merge = AsyncMock()
        policy = _build_dispatch_policy(
            write_delete=write_delete,
            write_append=write_append,
            write_merge=write_merge,
        )

        await _dispatch_request_by_mode(
            request=request,
            policy=policy,
        )

        write_delete.assert_not_called()
        write_append.assert_called_once_with(request)
        write_merge.assert_not_called()

    def test_select_dispatch_handler_routes_delete(self) -> None:
        """Delete mode should select the delete handler from dispatch policy."""
        write_delete = AsyncMock()
        write_append = AsyncMock()
        write_merge = AsyncMock()
        policy = _build_dispatch_policy(
            write_delete=write_delete,
            write_append=write_append,
            write_merge=write_merge,
        )

        handler = _select_dispatch_handler(
            validated_mode=SilverWriteMode.DELETE,
            policy=policy,
        )

        assert handler is write_delete


@pytest.mark.unit
class TestEmitMergeRetryTelemetry:
    """Tests for _emit_merge_retry_telemetry with metrics (line 275)."""

    def test_emit_retry_telemetry_with_metrics(self) -> None:
        """Line 275: metrics.increment_counter called when metrics is set."""
        metrics = MagicMock()
        mixin = _ConcreteDeltaMixin(metrics=metrics)

        mixin._emit_merge_retry_telemetry(
            table_path="path/table",
            retry_type="commit_conflict",
            attempt=1,
            max_retries=3,
            delay_seconds=0.25,
        )

        metrics.increment_counter.assert_called_once()
        call_args = metrics.increment_counter.call_args
        assert call_args[0][0] == "bioetl_silver_merge_retries_total"
        labels = call_args[0][2]
        assert labels["pipeline"] == "table"
        assert labels["retry_type"] == "commit_conflict"

    def test_emit_retry_telemetry_without_metrics(self) -> None:
        """Line 274: metrics is None, no counter increment."""
        mixin = _ConcreteDeltaMixin(metrics=None)

        # Should not raise
        mixin._emit_merge_retry_telemetry(
            table_path="path/table",
            retry_type="timeout",
            attempt=1,
            max_retries=1,
            delay_seconds=0.1,
        )

        # Warning should still be logged
        mixin.logger.warning.assert_called_once()


@pytest.mark.unit
class TestEmitMergeFinalTelemetry:
    """Tests for _emit_merge_final_telemetry with metrics (line 297)."""

    def test_emit_final_telemetry_with_metrics(self) -> None:
        """Line 297: metrics.increment_counter called when metrics is set."""
        metrics = MagicMock()
        mixin = _ConcreteDeltaMixin(metrics=metrics)

        mixin._emit_merge_final_telemetry(
            table_path="path/table",
            final_reason="commit_conflict_retries_exhausted",
        )

        metrics.increment_counter.assert_called_once()
        assert (
            metrics.increment_counter.call_args[0][0]
            == "bioetl_silver_merge_failures_total"
        )
        labels = metrics.increment_counter.call_args[0][2]
        assert labels["pipeline"] == "table"
        assert labels["final_reason"] == "commit_conflict_retries_exhausted"

    def test_emit_final_telemetry_without_metrics(self) -> None:
        """Line 296: metrics is None, no counter called."""
        mixin = _ConcreteDeltaMixin(metrics=None)

        mixin._emit_merge_final_telemetry(
            table_path="path/table",
            final_reason="timeout_retries_exhausted",
        )

        mixin.logger.error.assert_called_once()


@pytest.mark.unit
class TestDispatchWriteWithDomainErrors:
    """Tests for _dispatch_write_with_domain_errors (line 333)."""

    @pytest.mark.asyncio
    async def test_schema_mismatch_raises_schema_violation_error(self) -> None:
        """Line 328-329: SchemaMismatchError translated to SchemaViolationError."""
        from deltalake.exceptions import SchemaMismatchError

        mixin = _ConcreteDeltaMixin()
        data = _make_arrow_table()
        request = _DeltaWriteRequest(
            validated_mode=SilverWriteMode.MERGE,
            table_path="path/table",
            arrow_data=data,
            primary_keys=["id"],
            partition_cols=None,
        )

        with patch.object(
            mixin,
            "_dispatch_write",
            side_effect=SchemaMismatchError("schema mismatch"),
        ):
            with pytest.raises(SchemaViolationError):
                await mixin._dispatch_write_with_domain_errors(
                    table_name="chembl.activity",
                    request=request,
                )


@pytest.mark.unit
class TestRaiseDomainWriteError:
    """Direct tests for the Delta-to-domain translation helper."""

    def test_merge_conflict_is_translated(self) -> None:
        """Merge conflict DeltaError should become MergeConflictError."""
        from deltalake.exceptions import DeltaError

        with pytest.raises(MergeConflictError):
            _raise_domain_write_error(
                table_name="chembl.activity",
                exc=DeltaError("Merge-conflict detected"),
            )

    def test_non_conflict_delta_error_is_reraised(self) -> None:
        """Non-conflict DeltaError should propagate unchanged."""
        from deltalake.exceptions import DeltaError

        with pytest.raises(DeltaError, match="other delta error"):
            _raise_domain_write_error(
                table_name="chembl.activity",
                exc=DeltaError("other delta error"),
            )

    @pytest.mark.asyncio
    async def test_arrow_type_error_raises_schema_violation_error(self) -> None:
        """Line 328-329: ArrowTypeError translated to SchemaViolationError."""
        mixin = _ConcreteDeltaMixin()
        data = _make_arrow_table()
        request = _DeltaWriteRequest(
            validated_mode=SilverWriteMode.MERGE,
            table_path="path/table",
            arrow_data=data,
            primary_keys=["id"],
            partition_cols=None,
        )

        with patch.object(
            mixin,
            "_dispatch_write",
            side_effect=pa.ArrowTypeError("type error"),
        ):
            with pytest.raises(SchemaViolationError):
                await mixin._dispatch_write_with_domain_errors(
                    table_name="chembl.activity",
                    request=request,
                )

    @pytest.mark.asyncio
    async def test_delta_error_with_merge_conflict_raises_merge_conflict(
        self,
    ) -> None:
        """Line 331-332: DeltaError with 'Merge-conflict' string becomes MergeConflictError."""
        from deltalake.exceptions import DeltaError

        mixin = _ConcreteDeltaMixin()
        data = _make_arrow_table()
        request = _DeltaWriteRequest(
            validated_mode=SilverWriteMode.MERGE,
            table_path="path/table",
            arrow_data=data,
            primary_keys=["id"],
            partition_cols=None,
        )

        with patch.object(
            mixin,
            "_dispatch_write",
            side_effect=DeltaError("Merge-conflict detected"),
        ):
            with pytest.raises(MergeConflictError):
                await mixin._dispatch_write_with_domain_errors(
                    table_name="chembl.activity",
                    request=request,
                )

    @pytest.mark.asyncio
    async def test_delta_error_without_merge_conflict_reraises(self) -> None:
        """Line 333: DeltaError without 'Merge-conflict' is re-raised as-is."""
        from deltalake.exceptions import DeltaError

        mixin = _ConcreteDeltaMixin()
        data = _make_arrow_table()
        request = _DeltaWriteRequest(
            validated_mode=SilverWriteMode.MERGE,
            table_path="path/table",
            arrow_data=data,
            primary_keys=["id"],
            partition_cols=None,
        )

        with patch.object(
            mixin,
            "_dispatch_write",
            side_effect=DeltaError("some other delta error"),
        ):
            with pytest.raises(DeltaError):
                await mixin._dispatch_write_with_domain_errors(
                    table_name="chembl.activity",
                    request=request,
                )


@pytest.mark.unit
class TestMergeExecutionTimeoutError:
    """Tests for _MergeExecutionTimeoutError."""

    def test_timeout_error_message(self) -> None:
        """Timeout error includes seconds."""
        err = _MergeExecutionTimeoutError(45.0)
        assert "45" in str(err)
        assert err.timeout_seconds == pytest.approx(45.0)
