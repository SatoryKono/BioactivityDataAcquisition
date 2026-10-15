"""Remaining silver/quarantine residuals for #10469 / #10516 (no gold_writer)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pyarrow as pa
import pytest
from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

from bioetl.domain.medallion import SilverWriteMode
from bioetl.domain.types.contract_rollout import ContractRolloutPolicy
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.quarantine.filtered_reads import (
    _filtered_projection_columns,
    get_filtered_record,
)
from bioetl.infrastructure.quarantine.unified import UnifiedQuarantineAdapter
from bioetl.infrastructure.storage.silver.delta_request_models import _DeltaWriteRequest
from bioetl.infrastructure.storage.silver.delta_write_execution import (
    _build_plain_delta_write_kwargs,
    _decode_subprocess_output,
    _require_delta_write_request,
    _run_plain_delta_write_subprocess,
    _write_arrow_payload_for_subprocess,
)
from bioetl.infrastructure.storage.silver.maintenance_mixin import (
    SilverWriterMaintenanceMixin,
)
from bioetl.infrastructure.storage.silver.merged_operations import (
    _MergedSilverWriteRequest,
    _execute_merged_silver_write_flow,
    _export_silver_merged_csv,
    _prepare_merged_silver_write,
    _write_silver_merged_delta,
)
from bioetl.infrastructure.storage.silver.operations.merged_operations import (
    SilverMergedOperations,
)
from bioetl.infrastructure.storage.silver.operations.metadata_audit_operations import (
    log_silver_audit_via_support_request,
)
from bioetl.infrastructure.storage.silver.operations.metadata_context_facade import (
    _SilverMetadataContextFacade,
)
from bioetl.infrastructure.storage.silver.operations.metadata_dq_operations import (
    get_flat_structure,
    get_transform_steps,
    get_transform_version,
    should_skip_silver_metadata_write_operation,
)
from bioetl.infrastructure.storage.silver.operations.metadata_runtime_support import (
    _writer_parameters,
    resolve_transform_steps,
    resolve_transform_version,
)
from bioetl.infrastructure.storage.silver.runtime_helpers import (
    SilverWriterRuntimeServicesRequest,
    _build_merged_operations,
    _build_validation_operations,
    _resolve_operation_logger,
)
from bioetl.infrastructure.storage.silver.validation_record_support import (
    _validate_records,
)
from bioetl.infrastructure.storage.silver.writer_metadata_facade import (
    SilverWriterMetadataFacade,
)
from bioetl.infrastructure.storage.silver.writer_runtime_facade import (
    SilverWriterRuntimeFacade,
)
from bioetl.infrastructure.storage.silver.writer_runtime_invocation import (
    _validate_single_target_compat,
    _write_merged_metadata_via_operations,
)
from bioetl.infrastructure.storage.silver.writer_runtime_validation_facade import (
    _SilverWriterRuntimeValidationFacade,
)
from bioetl.infrastructure.storage.silver_writer import SilverWriter

pytestmark = pytest.mark.unit


class _MergedHost:
    def __init__(self) -> None:
        self.logger = MagicMock()
        self.csv_exporter = SimpleNamespace(export=AsyncMock())
        self._arrow_converter = SimpleNamespace(
            convert_records_to_arrow=lambda records, **_k: pa.table({"id": [1]})
        )

    def _resolve_table_path(self, table_name: str) -> str:
        return f"/tmp/{table_name}"


class _FacadeHost(SilverWriterRuntimeFacade):
    def _should_dual_write(self) -> bool:
        return False


def test_delta_write_execution_edges(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(TypeError, match="_DeltaWriteRequest"):
        _require_delta_write_request(object())

    request = _DeltaWriteRequest(
        validated_mode=SilverWriteMode.APPEND,
        table_path=str(tmp_path / "t"),
        arrow_data=pa.table({"id": [1]}),
        primary_keys=["id"],
        partition_cols=["pipeline"],
        schema_mode="overwrite",
    )
    kwargs = _build_plain_delta_write_kwargs(
        request, mode="append", schema_mode="overwrite"
    )
    assert kwargs["partition_by"] == ["pipeline"]
    assert kwargs["schema_mode"] == "overwrite"

    payload = _write_arrow_payload_for_subprocess(
        table_path="s3://bucket/table",
        table=pa.table({"id": [1]}),
    )
    assert payload.exists()
    payload.unlink()

    assert _decode_subprocess_output(b"ok") == "ok"

    def _timeout(*_args: object, **_kwargs: object) -> None:
        raise subprocess.TimeoutExpired(cmd="x", timeout=1)

    monkeypatch.setattr(
        "bioetl.infrastructure.storage.silver.delta_write_execution.subprocess.run",
        _timeout,
    )
    with pytest.raises(TimeoutError):
        _run_plain_delta_write_subprocess(
            kwargs={"table_or_uri": str(tmp_path / "delta")},
            arrow_data=pa.table({"id": [1]}),
            timeout_seconds=0.01,
        )

    def _fail(*_args: object, **_kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(returncode=2, stderr=b"fail", stdout=b"")

    monkeypatch.setattr(
        "bioetl.infrastructure.storage.silver.delta_write_execution.subprocess.run",
        _fail,
    )
    with pytest.raises(RuntimeError, match="exit_code=2"):
        _run_plain_delta_write_subprocess(
            kwargs={"table_or_uri": str(tmp_path / "delta2")},
            arrow_data=pa.table({"id": [1]}),
            timeout_seconds=1,
        )


@pytest.mark.asyncio
async def test_merged_operations_empty_schema_export_and_delta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host = _MergedHost()
    empty = _MergedSilverWriteRequest(table_name="activity", records=[])
    await _execute_merged_silver_write_flow(host, empty)  # type: ignore[arg-type]
    host.logger.warning.assert_called()

    with pytest.raises(TypeError, match="DataFrameSchema"):
        _prepare_merged_silver_write(
            host,  # type: ignore[arg-type]
            _MergedSilverWriteRequest(
                table_name="activity",
                records=[{"id": 1}],
                schema=object(),
            ),
        )

    class _Schema:
        def to_schema(self) -> object:
            return object()

    with pytest.raises(TypeError, match="DataFrameSchema"):
        _prepare_merged_silver_write(
            host,  # type: ignore[arg-type]
            _MergedSilverWriteRequest(
                table_name="activity",
                records=[{"id": 1}],
                schema=_Schema(),
            ),
        )

    monkeypatch.setattr(
        "bioetl.infrastructure.storage.silver.merged_operations.write_deltalake",
        lambda *_a, **_k: None,
    )
    await _write_silver_merged_delta(
        table_path="/tmp/activity",
        arrow_table=pa.table({"id": [1]}),
    )
    await _export_silver_merged_csv(
        host,  # type: ignore[arg-type]
        table_name="activity",
        arrow_table=pa.table({"id": [1]}),
    )
    host.csv_exporter.export.assert_awaited()

    ops = SilverMergedOperations(
        logger=NoOpLogger(),
        csv_exporter=None,
        _arrow_converter=host._arrow_converter,  # type: ignore[arg-type]
        _resolve_table_path=host._resolve_table_path,
        _write_silver_merged_metadata=AsyncMock(),
    )
    await ops._write_silver_merged_delta(
        table_path="/tmp/activity",
        arrow_table=pa.table({"id": [1]}),
    )
    await ops._export_silver_merged_csv(
        table_name="activity",
        arrow_table=pa.table({"id": [1]}),
    )


@pytest.mark.asyncio
async def test_runtime_helpers_and_invocation_compat() -> None:
    logger = NoOpLogger()
    assert _resolve_operation_logger(logger) is logger
    assert isinstance(_resolve_operation_logger(None), NoOpLogger)
    request = SilverWriterRuntimeServicesRequest()
    assert _build_merged_operations(request) is None
    assert (
        _build_validation_operations(
            request,
            write_policy=MagicMock(),
            silver_validator=MagicMock(),
        )
        is None
    )

    with_path = SilverWriterRuntimeServicesRequest(
        base_path=".",
        logger=NoOpLogger(),
    )
    merged = _build_merged_operations(with_path)
    assert merged is not None
    await merged._write_silver_merged_metadata(
        table_path="p",
        table_name="activity",
        records=[],
        primary_keys=["id"],
        completed_at=None,
        run_id=None,
        sources_used=None,
    )

    invocation = SimpleNamespace(
        table_name="t",
        run_id="r",
        run_type="full",
        source_batch_id="b",
        ingestion_ts=None,
    )
    with pytest.raises(TypeError, match="table_name"):
        _validate_single_target_compat(
            invocation=invocation,  # type: ignore[arg-type]
            table_name="other",
            run_id=None,
            run_type=None,
            source_batch_id=None,
            ingestion_ts=None,
        )
    with pytest.raises(TypeError, match="run_id"):
        _validate_single_target_compat(
            invocation=invocation,  # type: ignore[arg-type]
            table_name=None,
            run_id="x",
            run_type=None,
            source_batch_id=None,
            ingestion_ts=None,
        )
    with pytest.raises(TypeError, match="run_type"):
        _validate_single_target_compat(
            invocation=invocation,  # type: ignore[arg-type]
            table_name=None,
            run_id=None,
            run_type="delta",
            source_batch_id=None,
            ingestion_ts=None,
        )
    with pytest.raises(TypeError, match="source_batch_id"):
        _validate_single_target_compat(
            invocation=invocation,  # type: ignore[arg-type]
            table_name=None,
            run_id=None,
            run_type=None,
            source_batch_id="z",
            ingestion_ts=None,
        )


@pytest.mark.asyncio
async def test_runtime_facade_dual_merged_and_validation_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host = _FacadeHost()
    host._merged = SimpleNamespace(write_silver_merged=AsyncMock())
    await host.write_silver_merged("activity", [{"id": 1}])
    host._merged.write_silver_merged.assert_awaited()

    with pytest.raises(RuntimeError, match="merged operations"):
        empty = _FacadeHost()
        await empty.write_silver_merged("activity", [{"id": 1}])

    dual = _FacadeHost()

    async def _dual(_writer: object, *, invocation: object) -> str:
        del _writer, invocation
        return "ok"

    monkeypatch.setattr(
        "bioetl.infrastructure.storage.silver.writer_runtime_facade._write_dual_targets",
        _dual,
    )
    result = await dual._write_dual_targets(invocation=SimpleNamespace())
    assert result == "ok"

    validation = _SilverWriterRuntimeValidationFacade()
    with pytest.raises(RuntimeError, match="validation operations"):
        validation._enforce_write_policy(SilverWriteMode.APPEND, "t")
    with pytest.raises(RuntimeError, match="validation operations"):
        validation._validate_write_mode("append")
    with pytest.raises(RuntimeError, match="validation operations"):
        validation._to_policy_write_mode(SilverWriteMode.APPEND)
    with pytest.raises(RuntimeError, match="validation operations"):
        validation._validate_silver_pandera([{"id": 1}], "t")
    with pytest.raises(RuntimeError, match="validation operations"):
        await validation._check_schema_drift("t", [{"id": 1}], "error")
    with pytest.raises(RuntimeError, match="validation operations"):
        validation._sync_validate_and_build_arrow(MagicMock())


@pytest.mark.asyncio
async def test_metadata_facades_audit_and_skip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Ctx(_SilverMetadataContextFacade):
        def __init__(self) -> None:
            self._host = SimpleNamespace(
                _flat_structure=True,
                _transform_version="1.0.0",
                _transform_steps=("a", "b"),
            )

    ctx = _Ctx()
    assert ctx._flat_structure is True
    assert ctx._transform_version == "1.0.0"
    assert ctx._transform_steps == ("a", "b")

    ops = SimpleNamespace(_host=SimpleNamespace(_flat_structure=False))
    assert get_flat_structure(ops) is False
    assert get_transform_version(SimpleNamespace(_host=None)) is None
    assert get_transform_steps(SimpleNamespace(_host=None)) == ()
    assert resolve_transform_version(None) is None
    assert resolve_transform_steps(SimpleNamespace(_transform_steps=["x"])) == ("x",)

    monkeypatch.setattr(
        "bioetl.infrastructure.storage.silver.operations.metadata_dq_operations.should_skip_silver_metadata_write",
        lambda *_a, **_k: True,
    )
    assert (
        should_skip_silver_metadata_write_operation(
            ops, records=[], table_path="p", event_name="e"
        )
        is True
    )

    logged = AsyncMock()
    monkeypatch.setattr(
        "bioetl.infrastructure.storage.silver.operations.metadata_audit_operations._log_silver_audit_event",
        logged,
    )
    await log_silver_audit_via_support_request(
        SimpleNamespace(_audit=object()),
        table_name="activity",
        records=[{"id": 1}],
        validated_mode=SilverWriteMode.APPEND,
    )
    logged.assert_awaited()

    meta = SilverWriterMetadataFacade()
    meta._metadata_writer = object()
    meta._metadata_coordinator = None
    assert meta._should_skip_silver_metadata_write(records=[]) is True
    with pytest.raises(RuntimeError, match="MetadataCoordinator"):
        meta._should_skip_silver_metadata_write(records=[{"id": 1}])
    meta._metadata = None
    with pytest.raises(RuntimeError, match="metadata operations"):
        await meta._log_silver_audit(
            "activity",
            [{"id": 1}],
            "append",
            run_id=None,
            run_type=None,
            source_batch_id=None,
            ingestion_ts=None,
        )

    writer = SimpleNamespace(
        _metadata=object(),
        _should_skip_silver_metadata_write=lambda **_k: True,
    )
    await _write_merged_metadata_via_operations(
        writer,
        table_path="p",
        table_name="activity",
        records=[{"id": 1}],
        primary_keys=["id"],
    )
    assert _writer_parameters(object()) is None

    schema = pa.schema([("id", pa.int64()), ("extra", pa.string())])
    logger = MagicMock()
    _validate_records(SimpleNamespace(logger=logger), [{"id": 1}], "activity", schema)
    logger.debug.assert_called()


def test_silver_writer_dual_write_and_maintenance_preview(tmp_path: Path) -> None:
    policy = ContractRolloutPolicy(
        contract_ref="silver.activity",
        active_version="v1.0.0",
        mode="dual_write",
        read_order=("v1.0.0", "v2.0.0"),
        write_versions=("v1.0.0", "v2.0.0"),
    )
    host = SimpleNamespace(_contract_rollout_policy=policy)
    assert SilverWriter._should_dual_write(host) is True  # type: ignore[arg-type]
    assert (
        SilverWriter._should_dual_write(SimpleNamespace(_contract_rollout_policy=None))
        is False
    )  # type: ignore[arg-type]

    table_dir = tmp_path / "activity"
    table_dir.mkdir()
    (table_dir / "part.parquet").write_bytes(b"x")
    mixin = SilverWriterMaintenanceMixin()
    mixin.get_table_path = lambda _name: table_dir  # type: ignore[method-assign]
    preview = mixin.preview_cleanup("activity")
    assert preview["exists"] is True
    assert preview["file_count"] == 1

    mixin.get_table_path = lambda _name: tmp_path / "missing"  # type: ignore[method-assign]
    missing = mixin.preview_cleanup("missing")
    assert missing["exists"] is False
    assert missing["file_count"] == 0


def test_quarantine_filtered_and_unified_missing_tables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dt = SimpleNamespace(
        schema=lambda: SimpleNamespace(
            fields=[SimpleNamespace(name="pipeline"), SimpleNamespace(name="payload")]
        )
    )
    cols = _filtered_projection_columns(
        dt,  # type: ignore[arg-type]
        include_payload=True,
        include_payload_preview=False,
    )
    assert cols is not None and "payload" in cols

    with pytest.raises(ValueError, match="scoped pipeline"):
        get_filtered_record("path", None, payload_hash="abc", pipeline=None)

    def _missing(*_args: object, **_kwargs: object) -> None:
        raise DeltaTableNotFoundError("missing")

    monkeypatch.setattr(
        "bioetl.infrastructure.quarantine.filtered_reads.DeltaTable",
        _missing,
    )
    assert (
        get_filtered_record("path", None, payload_hash="abc", pipeline="chembl") is None
    )

    monkeypatch.setattr(
        "bioetl.infrastructure.quarantine.unified.DeltaTable",
        _missing,
    )
    adapter = UnifiedQuarantineAdapter.__new__(UnifiedQuarantineAdapter)
    adapter.base_path = "path"
    adapter.status_events_path = "events"
    assert adapter.get_record(payload_hash="abc", pipeline="chembl") is None
