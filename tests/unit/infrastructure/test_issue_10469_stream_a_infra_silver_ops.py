"""Silver validation/merge/schema residuals without gold_writer."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pyarrow as pa
import pytest
from deltalake.exceptions import CommitFailedError
from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

from bioetl.domain.exceptions import (
    DeltaTransactionError,
    PolicyViolationError,
    SchemaEvolutionError,
)
from bioetl.domain.medallion import SilverWriteMode, WriteMode, WriteModePolicy
from bioetl.infrastructure.storage.delta.resilience import (
    AdaptiveRetryPolicy,
    SilverMergeResiliencePolicy,
)
from bioetl.infrastructure.storage.silver.delta_merge_helpers import (
    _MergeExecutionTimeoutError,
    _build_content_changed_predicate,
    _build_merge_condition,
    _build_merge_update_predicate,
    _delta_table_has_parquet_data,
    build_replay_safe_rerun_contract,
)
from bioetl.infrastructure.storage.silver.delta_request_models import _DeltaWriteRequest
from bioetl.infrastructure.storage.silver.merge_resilience_helpers import (
    _emit_merge_final_event,
    _emit_merge_recovered_after_retry,
    _emit_merge_retry_event,
    _execute_merge_write_request,
    _handle_commit_retry,
    _handle_merge_execution_error,
    _handle_timeout_retry,
    _maybe_pre_evolve_on_duplicate_field_error,
    _pre_evolve_existing_table_schema,
)
from bioetl.infrastructure.storage.silver.metadata_write_models import (
    _SilverMetadataWriteRequest,
)
from bioetl.infrastructure.storage.silver.operations.metadata_write_facade import (
    _SilverMetadataWriteFacade,
    _resolve_execute_silver_metadata_write,
)
from bioetl.infrastructure.storage.silver.operations.metadata_write_operations import (
    write_internal_silver_metadata_operation,
    write_silver_merged_metadata_operation,
)
from bioetl.infrastructure.storage.silver.operations.validation_operations import (
    _enforce_replay_safe_merge_contract,
    _strict_replay_merge_contract_required,
)
from bioetl.infrastructure.storage.silver.schema_drift_operations import (
    _build_schema_drift_info,
    _build_silver_schema_drift_diff,
    _check_schema_drift,
    _detect_schema_drift,
    _diff_schema_fields,
)
from bioetl.infrastructure.storage.silver.validation_operations import (
    _SilverSchemaPolicyRequest,
    _SilverWritePreparationRequest,
    _build_prepared_silver_write_payload,
    _enforce_write_policy,
    _finalize_silver_write_payload,
    _sync_validate_and_build_arrow,
    _to_policy_write_mode_impl,
    _validate_write_mode_impl,
)

pytestmark = pytest.mark.unit


def _delta_request(*, merge_schema: bool = False) -> _DeltaWriteRequest:
    return _DeltaWriteRequest(
        validated_mode=SilverWriteMode.MERGE,
        table_path="/tmp/silver-table",
        arrow_data=pa.table({"id": ["1"]}),
        primary_keys=["id"],
        partition_cols=None,
        merge_schema=merge_schema,
    )


def _exhausted_policy() -> SilverMergeResiliencePolicy:
    disabled = AdaptiveRetryPolicy(
        enabled=False,
        max_retries=0,
        base_delay_seconds=0.0,
        max_delay_seconds=0.0,
    )
    return SilverMergeResiliencePolicy(
        execution_timeout_seconds=1.0,
        commit_retry=disabled,
        timeout_retry=disabled,
    )


class TestSilverValidationOperations:
    def test_write_mode_and_policy_payload(self) -> None:
        assert _validate_write_mode_impl("merge") is SilverWriteMode.MERGE
        with pytest.raises(ValueError, match="Invalid Silver write mode"):
            _validate_write_mode_impl("upsert")
        assert _to_policy_write_mode_impl(SilverWriteMode.DELETE) is WriteMode.OVERWRITE
        host = SimpleNamespace(
            logger=MagicMock(),
            _write_policy=WriteModePolicy(),
            _metrics=MagicMock(),
            _to_policy_write_mode=_to_policy_write_mode_impl,
        )
        with pytest.raises(PolicyViolationError, match="does not allow overwrite"):
            _enforce_write_policy(host, SilverWriteMode.DELETE, "chembl.activity")
        host._metrics.increment_counter.assert_called()
        schema_request = _SilverSchemaPolicyRequest(
            table_name="chembl.activity",
            records=[{"id": "1"}],
            on_schema_mismatch="evolve",
            validated_mode=SilverWriteMode.APPEND,
            arrow_data=pa.table({"id": ["1"]}),
        )
        append_payload = _build_prepared_silver_write_payload(
            table_path="/t", schema_request=schema_request
        )
        assert append_payload.schema_mode == "merge"
        merge_payload = _build_prepared_silver_write_payload(
            table_path="/t",
            schema_request=_SilverSchemaPolicyRequest(
                table_name="chembl.activity",
                records=[{"id": "1"}],
                on_schema_mismatch="evolve",
                validated_mode=SilverWriteMode.MERGE,
                arrow_data=pa.table({"id": ["1"]}),
            ),
        )
        assert merge_payload.merge_schema is True

    def test_sync_validate_builds_arrow(self) -> None:
        records = [{"id": "1"}]
        arrow = pa.table({"id": ["1"]})
        host = SimpleNamespace(
            _deduplicate_by_primary_keys=lambda rows, _keys: records,
            _validate_write_mode=_validate_write_mode_impl,
            _to_policy_write_mode=_to_policy_write_mode_impl,
            _write_policy=WriteModePolicy(),
            logger=MagicMock(),
            _metrics=None,
            _validate_key_nullability=lambda *_a, **_k: None,
            _prepare_arrow_data=lambda *_a, **_k: arrow,
            _silver_validator=SimpleNamespace(
                _schema=None,
                validate=lambda _rows: SimpleNamespace(valid=True, errors=[]),
            ),
        )
        context = _sync_validate_and_build_arrow(
            host,
            _SilverWritePreparationRequest(
                table_name="chembl.activity",
                records=records,
                primary_keys=["id"],
                schema=pa.schema([("id", pa.string())]),
                mode="append",
                column_order=None,
                partition_cols=None,
                key_nullability_rules=None,
            ),
        )
        assert context.validated_mode is SilverWriteMode.APPEND
        assert context.arrow_data.num_rows == 1

    async def test_finalize_payload(self) -> None:
        host = SimpleNamespace(
            _check_schema_drift=AsyncMock(),
            _resolve_table_path=lambda name: f"/silver/{name}",
        )
        payload = await _finalize_silver_write_payload(
            host,
            _SilverSchemaPolicyRequest(
                table_name="chembl.activity",
                records=[{"id": "1"}],
                on_schema_mismatch="ignore",
                validated_mode=SilverWriteMode.MERGE,
                arrow_data=pa.table({"id": ["1"]}),
            ),
        )
        assert payload.table_path == "/silver/chembl.activity"
        host._check_schema_drift.assert_awaited()


class TestSchemaDriftAndReplay:
    async def test_schema_drift_empty_ignore_and_error(self) -> None:
        host = SimpleNamespace(
            logger=MagicMock(),
            _get_table_schema=AsyncMock(return_value=None),
        )
        await _check_schema_drift(host, "t", [{"id": "1"}], "error")
        assert _diff_schema_fields(None, [{"id": "1"}]) is None
        assert _build_silver_schema_drift_diff(pa.schema([("id", pa.string())]), []) is None
        existing = pa.schema([("id", pa.string()), ("gone", pa.string())])
        drift_host = SimpleNamespace(
            logger=MagicMock(),
            _get_table_schema=AsyncMock(return_value=existing),
        )
        with pytest.raises(SchemaEvolutionError):
            await _check_schema_drift(
                drift_host, "t", [{"id": "1", "extra": "x"}], "error"
            )
        await _check_schema_drift(
            drift_host, "t", [{"id": "1", "extra": "x"}], "ignore"
        )
        info = await _detect_schema_drift(
            drift_host, "t", [{"id": "1", "a": 1, "b": 2, "c": 3, "d": 4}]
        )
        assert info is not None
        assert info.status in {"warn", "critical", "info"}
        same = _build_silver_schema_drift_diff(
            pa.schema([("id", pa.string())]), [{"id": "1"}]
        )
        assert same is None
        critical = _build_schema_drift_info(
            _build_silver_schema_drift_diff(
                pa.schema([("id", pa.string()), ("name", pa.string())]),
                [{"id": "1"}],
            )
        )
        assert critical.status == "critical"

    def test_replay_safe_merge_contract(self) -> None:
        assert _strict_replay_merge_contract_required(SimpleNamespace()) is False
        required = SimpleNamespace(
            _metadata_coordinator=SimpleNamespace(
                run_context=SimpleNamespace(
                    exact_replay=True, required_persistence_profile=""
                )
            )
        )
        assert _strict_replay_merge_contract_required(required) is True
        _enforce_replay_safe_merge_contract(
            runtime_host=required,
            table_name="t",
            validated_mode=SilverWriteMode.APPEND,
            arrow_data=pa.table({"id": ["1"]}),
        )
        with pytest.raises(ValueError, match="requires content_hash"):
            _enforce_replay_safe_merge_contract(
                runtime_host=required,
                table_name="t",
                validated_mode=SilverWriteMode.MERGE,
                arrow_data=pa.table({"id": ["1"]}),
            )
        _enforce_replay_safe_merge_contract(
            runtime_host=required,
            table_name="t",
            validated_mode=SilverWriteMode.MERGE,
            arrow_data=pa.table({"id": ["1"], "content_hash": ["abc"]}),
        )


class TestMetadataWriteFacadeSkip:
    async def test_internal_and_merged_skip_empty_records(self) -> None:
        execute = AsyncMock()
        host = SimpleNamespace(
            _should_skip_silver_metadata_write=lambda **_k: True,
        )
        request = _SilverMetadataWriteRequest(
            table_path="/t",
            table_name="chembl.activity",
            records=[],
            primary_keys=["id"],
            mode=SilverWriteMode.MERGE,
        )
        await write_internal_silver_metadata_operation(
            host, request, execute_silver_metadata_write=execute
        )
        execute.assert_not_awaited()
        await write_silver_merged_metadata_operation(
            host,
            table_path="/t",
            table_name="chembl.activity",
            records=[],
            primary_keys=["id"],
            execute_silver_metadata_write=execute,
        )
        execute.assert_not_awaited()

    async def test_facade_skips_empty_records(self) -> None:
        facade = _SilverMetadataWriteFacade()
        await facade._write_silver_metadata(
            _SilverMetadataWriteRequest(
                table_path="/t",
                table_name="chembl.activity",
                records=[],
                primary_keys=["id"],
                mode=SilverWriteMode.MERGE,
            )
        )
        await facade._write_silver_merged_metadata(
            table_path="/t",
            table_name="chembl.activity",
            records=[],
            primary_keys=["id"],
        )
        assert callable(_resolve_execute_silver_metadata_write())

    async def test_internal_write_executes_when_not_skipped(self) -> None:
        execute = AsyncMock()
        host = SimpleNamespace(
            _should_skip_silver_metadata_write=lambda **_k: False,
        )
        request = _SilverMetadataWriteRequest(
            table_path="/t",
            table_name="chembl.activity",
            records=[{"id": "1"}],
            primary_keys=["id"],
            mode=SilverWriteMode.MERGE,
        )
        await write_internal_silver_metadata_operation(
            host, request, execute_silver_metadata_write=execute
        )
        execute.assert_awaited()


class TestMergeAndSchemaHelpers:
    def test_merge_predicates_and_remote_path(self) -> None:
        hashed = pa.table({"id": ["1"], "content_hash": ["abc"]})
        contract = build_replay_safe_rerun_contract(hashed)
        assert contract.requires_content_hash is True
        assert contract.strict_replay_safe is True
        plain = pa.table({"id": ["1"]})
        assert build_replay_safe_rerun_contract(plain).strict_replay_safe is False
        assert _build_merge_update_predicate(plain) == "true"
        assert "content_hash" in _build_content_changed_predicate()
        assert _build_merge_condition(["id", "batch"]) == (
            "target.id = source.id AND target.batch = source.batch"
        )
        assert _delta_table_has_parquet_data("s3://bucket/table") is True

    def test_local_parquet_detection(self, tmp_path: object) -> None:
        from pathlib import Path

        empty = Path(str(tmp_path)) / "empty-delta"
        empty.mkdir()
        assert _delta_table_has_parquet_data(str(empty)) is False
        (empty / "_delta_log").mkdir()
        (empty / "part.parquet").write_bytes(b"x")
        assert _delta_table_has_parquet_data(str(empty)) is True

    def test_merge_recovery_and_events(self) -> None:
        logger = MagicMock()
        _emit_merge_recovered_after_retry(
            logger=logger, table_path="/t", commit_retry_count=0, timeout_retry_count=0
        )
        logger.info.assert_not_called()
        _emit_merge_recovered_after_retry(
            logger=logger, table_path="/t", commit_retry_count=1, timeout_retry_count=0
        )
        logger.info.assert_called()
        metrics = MagicMock()
        _emit_merge_retry_event(
            logger=logger,
            metrics=metrics,
            table_path="/t",
            retry_type="timeout",
            attempt=1,
            max_retries=1,
            delay_seconds=0.0,
        )
        metrics.increment_counter.assert_called()
        _emit_merge_final_event(
            logger=logger,
            metrics=None,
            table_path="/t",
            final_reason="timeout_retries_exhausted",
        )

    async def test_pre_evolve_and_timeout_exhausted(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        request = _delta_request(merge_schema=False)
        unchanged, evolved = await _pre_evolve_existing_table_schema(
            request=request, load_module=lambda: object()
        )
        assert evolved is False
        assert unchanged.merge_schema is False

        async def _missing(**_k: object) -> object:
            raise DeltaTableNotFoundError("missing")

        monkeypatch.setattr(
            "bioetl.infrastructure.storage.silver.merge_resilience_helpers._load_delta_table",
            _missing,
        )
        missing_request = _delta_request(merge_schema=True)
        skipped, pre_evolved = await _pre_evolve_existing_table_schema(
            request=missing_request, load_module=lambda: object()
        )
        assert pre_evolved is False
        assert skipped is missing_request

        none = await _maybe_pre_evolve_on_duplicate_field_error(
            exc=ValueError("other"),
            request=missing_request,
            schema_pre_evolved=False,
            load_module=lambda: object(),
        )
        assert none is None
        already = await _maybe_pre_evolve_on_duplicate_field_error(
            exc=ValueError("Duplicate field name: x"),
            request=missing_request,
            schema_pre_evolved=True,
            load_module=lambda: object(),
        )
        assert already is None

        policy = _exhausted_policy()
        logger = MagicMock()
        with pytest.raises(DeltaTransactionError, match="timed out"):
            await _handle_timeout_retry(
                table_path="/t",
                policy=policy,
                retry_count=0,
                cause=_MergeExecutionTimeoutError(1.0),
                emit_final=lambda **_k: None,
                emit_retry=lambda **_k: None,
                logger=logger,
            )

        exhausted = await _handle_commit_retry(
            table_path="/t",
            policy=policy,
            retry_count=0,
            emit_final=lambda **_k: None,
            emit_retry=lambda **_k: None,
        )
        assert exhausted is None

        with pytest.raises(RuntimeError, match="boom"):
            await _handle_merge_execution_error(
                exc=RuntimeError("boom"),
                active_request=request,
                schema_pre_evolved=True,
                timeout_retry_count=0,
                policy=policy,
                load_module=lambda: object(),
                emit_final=lambda **_k: None,
                emit_retry=lambda **_k: None,
                logger=logger,
            )

    async def test_merge_create_on_missing_table(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def _missing(**_k: object) -> object:
            raise DeltaTableNotFoundError("missing")

        monkeypatch.setattr(
            "bioetl.infrastructure.storage.silver.merge_resilience_helpers._load_delta_table",
            _missing,
        )
        created: list[_DeltaWriteRequest] = []

        async def _create(request: _DeltaWriteRequest) -> None:
            created.append(request)

        await _execute_merge_write_request(
            request=_delta_request(),
            policy=_exhausted_policy(),
            load_module=lambda: object(),
            write_append=_create,
            merge_records=AsyncMock(),
            emit_final=lambda **_k: None,
            emit_retry=lambda **_k: None,
            logger=MagicMock(),
        )
        assert created

    async def test_merge_commit_conflict_exhausted(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def _conflict(**_k: object) -> object:
            raise CommitFailedError("conflict")

        monkeypatch.setattr(
            "bioetl.infrastructure.storage.silver.merge_resilience_helpers._load_delta_table",
            _conflict,
        )
        with pytest.raises(CommitFailedError, match="conflict"):
            await _execute_merge_write_request(
                request=_delta_request(),
                policy=_exhausted_policy(),
                load_module=lambda: object(),
                write_append=AsyncMock(),
                merge_records=AsyncMock(),
                emit_final=lambda **_k: None,
                emit_retry=lambda **_k: None,
                logger=MagicMock(),
            )
