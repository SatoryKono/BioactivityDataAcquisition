"""Stream A remaining INF 1–3 line leftovers (no gold_writer write_deltalake)."""

from __future__ import annotations

import errno
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pyarrow as pa
import pytest

from bioetl.domain.medallion import SilverWriteMode, WriteModePolicy
from bioetl.domain.workflow.foreign_key_reconciliation import ForeignKeyReconciliationRequest
from bioetl.infrastructure.control_plane._file_run_ledger_helpers import append_jsonl_payload
from bioetl.infrastructure.control_plane.file_contract_registry_store import (
    FileContractRegistryStore,
)
from bioetl.infrastructure.control_plane.file_lineage_store import FileLineageStore
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.quality.architecture_debt_task_support import (
    SymbolMetricLocation,
    build_symbol_index,
    measure_task,
)
from bioetl.infrastructure.storage.bronze.io_mixin import (
    BronzeWriterIOMixin,
    _publish_new_file_exclusive,
)
from bioetl.infrastructure.storage.delta.resilience import (
    AdaptiveRetryPolicy,
    SilverMergeResiliencePolicy,
)
from bioetl.infrastructure.storage.silver.delta_merge_helpers import (
    _MergeExecutionTimeoutError,
    _delta_table_has_parquet_data,
    _execute_merge_inline_with_timeout,
    _should_execute_merge_inline,
)
from bioetl.infrastructure.storage.silver.delta_request_models import _DeltaWriteRequest
from bioetl.infrastructure.storage.silver.merge_resilience_helpers import (
    _handle_commit_retry,
    _handle_merge_execution_error,
    _maybe_pre_evolve_on_duplicate_field_error,
)
from bioetl.infrastructure.storage.silver.metadata_mixin import SilverWriterMetadataMixin
from bioetl.infrastructure.storage.silver.metadata_write_models import (
    _SilverMetadataWriteRequest,
)
from bioetl.infrastructure.storage.silver.operations import metadata_write_operations as mwo
from bioetl.infrastructure.storage.silver.operations import validation_operations as vo
from bioetl.infrastructure.storage.silver.operations.validation_operations import (
    SilverValidationOperations,
)
from bioetl.infrastructure.storage.silver.runtime_helpers import (
    SilverWriterRuntimeServicesRequest,
    _build_validation_operations,
)
from bioetl.infrastructure.storage.silver.writer_metadata_facade import (
    SilverWriterMetadataFacade,
)
from bioetl.infrastructure.storage.silver.writer_runtime_invocation import (
    _write_merged_metadata_via_operations,
)
from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation_quarantine import (
    expire_gold_orphan_rows,
)
from bioetl.infrastructure.validation.pandera_validator import (
    PanderaGoldValidator,
    PanderaSilverValidator,
)

pytestmark = pytest.mark.unit


def _retrying_policy() -> SilverMergeResiliencePolicy:
    retry = AdaptiveRetryPolicy(
        enabled=True,
        max_retries=3,
        base_delay_seconds=0.01,
        max_delay_seconds=1.0,
        jitter_seconds=0.0,
        adaptive=False,
    )
    disabled = AdaptiveRetryPolicy(
        enabled=False,
        max_retries=0,
        base_delay_seconds=0.0,
        max_delay_seconds=0.0,
    )
    return SilverMergeResiliencePolicy(
        execution_timeout_seconds=1.0,
        commit_retry=retry,
        timeout_retry=disabled,
    )


def _delta_request(*, merge_schema: bool = True) -> _DeltaWriteRequest:
    return _DeltaWriteRequest(
        validated_mode=SilverWriteMode.MERGE,
        table_path="/tmp/silver-table",
        arrow_data=pa.table({"id": ["1"]}),
        primary_keys=["id"],
        partition_cols=None,
        merge_schema=merge_schema,
    )


def _validation_ops() -> SilverValidationOperations:
    return SilverValidationOperations(
        logger=MagicMock(),
        _write_policy=WriteModePolicy(),
        _metrics=MagicMock(),
        _silver_validator=MagicMock(),
        _get_table_schema=AsyncMock(return_value=None),
        _resolve_table_path=lambda name: f"/t/{name}",
        _prepare_arrow_data=lambda **_k: pa.table({"id": ["1"]}),
        _validate_write_mode=lambda mode: SilverWriteMode.APPEND,
        _deduplicate_by_primary_keys=lambda records, _keys: records,
        _to_policy_write_mode=lambda _mode: MagicMock(),
        _validate_key_nullability=lambda *_a, **_k: None,
    )


@pytest.mark.asyncio
async def test_merge_resilience_evolve_and_commit_delay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _delta_request()
    evolved = _delta_request(merge_schema=False)

    async def _evolve(**_kwargs: object) -> _DeltaWriteRequest:
        return evolved

    monkeypatch.setattr(
        "bioetl.infrastructure.storage.silver.merge_resilience_helpers._evolve_delta_schema_with_empty_append",
        _evolve,
    )
    maybe = await _maybe_pre_evolve_on_duplicate_field_error(
        exc=ValueError("Duplicate field name: id"),
        request=request,
        schema_pre_evolved=False,
        load_module=lambda: object(),
    )
    assert maybe == (evolved, True)

    next_request, next_evolved, retries = await _handle_merge_execution_error(
        exc=ValueError("Duplicate field name: id"),
        active_request=request,
        schema_pre_evolved=False,
        timeout_retry_count=0,
        policy=_retrying_policy(),
        load_module=lambda: object(),
        emit_final=lambda **_k: None,
        emit_retry=lambda **_k: None,
        logger=MagicMock(),
    )
    assert next_request is evolved
    assert next_evolved is True
    assert retries == 0

    slept: list[float] = []

    async def _sleep(delay: float) -> None:
        slept.append(delay)

    monkeypatch.setattr(
        "bioetl.infrastructure.storage.silver.merge_resilience_helpers.asyncio.sleep",
        _sleep,
    )
    nxt = await _handle_commit_retry(
        table_path="/t",
        policy=_retrying_policy(),
        retry_count=0,
        emit_final=lambda **_k: None,
        emit_retry=lambda **_k: None,
    )
    assert nxt == 1
    assert slept and slept[0] > 0.0


def test_delta_merge_log_skip_inline_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    table = tmp_path / "delta"
    (table / "_delta_log").mkdir(parents=True)
    (table / "_delta_log" / "000.json").write_text("{}", encoding="utf-8")
    assert _delta_table_has_parquet_data(str(table)) is False
    assert _should_execute_merge_inline(str(table)) is True

    clock = {"n": 0}

    def _now() -> float:
        clock["n"] += 1
        return 0.0 if clock["n"] == 1 else 10.0

    monkeypatch.setattr(time, "perf_counter", _now)
    with pytest.raises(_MergeExecutionTimeoutError):
        _execute_merge_inline_with_timeout(merge_callable=lambda: None, timeout_seconds=0.1)


def test_bronze_chunk_flush_and_eexist_link(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class _Host(BronzeWriterIOMixin):
        COMPRESSION_LEVEL = 1
        COMPRESSION_THREADS = 0
        COMPRESSION_CHUNK_SIZE = 4

        def _compressed_payload_matches(self, left: Path, right: Path) -> bool:
            del left, right
            return False

    host = _Host()
    target = tmp_path / "batch.jsonl.zst"
    count, size = host._write_atomic_stream([b"abcdef", b"gh"], target)
    assert count == 2
    assert size == 8
    assert target.exists()

    source = tmp_path / "src.bin"
    source.write_bytes(b"x")
    dest = tmp_path / "dest.bin"

    class _Eexist(OSError):
        """OSError with EEXIST that is not FileExistsError (CPython maps the latter)."""

        def __init__(self) -> None:
            super().__init__("exists")
            self.errno = errno.EEXIST

    def _eexist(_src: str, _dst: str) -> None:
        raise _Eexist()

    monkeypatch.setattr(
        "bioetl.infrastructure.storage.bronze.io_mixin.os.link",
        _eexist,
    )
    with pytest.raises(FileExistsError):
        _publish_new_file_exclusive(source, dest)


def test_debt_safe_text_none_and_complexity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "bioetl.infrastructure.quality.architecture_debt_task_support.iter_source_modules",
        lambda _root: [tmp_path / "gone.py"],
    )
    monkeypatch.setattr(
        "bioetl.infrastructure.quality.architecture_debt_task_support.safe_text",
        lambda _path: None,
    )
    assert build_symbol_index(tmp_path) == {}
    location = SymbolMetricLocation(
        name="fn",
        path=tmp_path / "mod.py",
        kind="function",
        lineno=1,
        end_lineno=4,
        size=4,
        complexity=6,
    )
    monkeypatch.setattr(
        "bioetl.infrastructure.quality.architecture_debt_task_support.select_symbol_location",
        lambda **_kwargs: (location, "src/mod.py", "fn", None),
    )
    _target, name, value, _note = measure_task(
        registry_name="function_complexity",
        key="fn",
        project_root=tmp_path,
        symbol_index={},
    )
    assert name == "fn"
    assert value == 6
    _target, _name, domain_value, _note = measure_task(
        registry_name="domain_complexity",
        key="fn",
        project_root=tmp_path,
        symbol_index={},
    )
    assert domain_value == 6


@pytest.mark.asyncio
async def test_silver_metadata_skip_and_missing_ops() -> None:
    class _Host(SilverWriterMetadataMixin):
        pass

    request = _SilverMetadataWriteRequest(
        table_path="/t",
        table_name="activity",
        records=[],
        primary_keys=["id"],
        mode=SilverWriteMode.APPEND,
    )
    await _Host()._write_silver_metadata(request)  # type: ignore[misc]
    await _Host()._write_silver_merged_metadata(  # type: ignore[misc]
        table_path="/t",
        table_name="activity",
        records=[],
        primary_keys=["id"],
    )

    facade = SilverWriterMetadataFacade()
    with pytest.raises(RuntimeError, match="required"):
        await facade._write_silver_metadata(request)
    with pytest.raises(RuntimeError, match="required"):
        await facade._write_silver_metadata_file(
            table_path="/t",
            metadata=MagicMock(),
            table_name="activity",
            provider_name="chembl",
            entity_name="activity",
        )

    await mwo.write_silver_merged_metadata_operation(
        SimpleNamespace(_should_skip_silver_metadata_write=lambda **_k: True),  # type: ignore[arg-type]
        table_path="/t",
        table_name="activity",
        records=[{"id": "1"}],
        primary_keys=["id"],
        execute_silver_metadata_write=AsyncMock(),
    )
    executed = AsyncMock()
    await mwo.write_silver_merged_metadata_operation(
        SimpleNamespace(_should_skip_silver_metadata_write=lambda **_k: False),  # type: ignore[arg-type]
        table_path="/t",
        table_name="activity",
        records=[{"id": "1"}],
        primary_keys=["id"],
        execute_silver_metadata_write=executed,
    )
    executed.assert_awaited()
    with pytest.raises(RuntimeError, match="required"):
        await _write_merged_metadata_via_operations(
            SimpleNamespace(_metadata=None),
            table_path="/t",
            table_name="activity",
            records=[{"id": "1"}],
            primary_keys=["id"],
        )


@pytest.mark.asyncio
async def test_validation_facade_wrappers_and_schema_wrapper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ops = _validation_ops()
    monkeypatch.setattr(vo, "_validate_records", lambda *_a, **_k: None)
    monkeypatch.setattr(vo, "_enforce_write_policy", lambda *_a, **_k: None)
    monkeypatch.setattr(vo, "_validate_silver_pandera", lambda *_a, **_k: None)
    monkeypatch.setattr(vo, "_detect_schema_drift", AsyncMock(return_value=None))
    monkeypatch.setattr(
        vo,
        "_finalize_silver_write_payload",
        AsyncMock(return_value=SimpleNamespace()),
    )
    ops._validate_records([], "activity", pa.schema([("id", pa.string())]))
    ops._enforce_write_policy(SilverWriteMode.APPEND, "activity")
    ops._validate_silver_pandera([], "activity")
    assert await ops._detect_schema_drift("activity", []) is None
    await ops._finalize_silver_write_payload(MagicMock())

    async def _schema(_base: object, table_name: str) -> pa.Schema:
        del table_name
        return pa.schema([("id", pa.string())])

    monkeypatch.setattr(
        "bioetl.infrastructure.storage.silver.support.get_table_schema",
        _schema,
    )
    built = _build_validation_operations(
        SilverWriterRuntimeServicesRequest(base_path=tmp_path, logger=NoOpLogger()),
        write_policy=WriteModePolicy(),
        silver_validator=MagicMock(),
    )
    assert built is not None
    schema = await built._get_table_schema("activity")
    assert schema is not None


def test_pandera_non_object_and_index_schema() -> None:
    import pandera.pandas as pa_schema

    schema = pa_schema.DataFrameSchema(
        {
            "n": pa_schema.Column("Int64", nullable=True),
            "flag": pa_schema.Column("boolean", nullable=True),
        }
    )
    validator = PanderaSilverValidator(schema=schema, strict=False)
    frame = pd.DataFrame(
        {
            "n": pd.array([1, pd.NA], dtype="Int64"),
            "flag": pd.array([True, pd.NA], dtype="boolean"),
        }
    )
    assert validator._normalize_nullable_integer_columns(frame) is not None
    assert validator._normalize_nullable_boolean_columns(frame) is not None
    indexed_schema = SimpleNamespace(
        columns={"n": object(), "idx": object()},
        index=SimpleNamespace(names=["idx"]),
        validate=lambda *_a, **_k: None,
    )
    indexed_validator = PanderaGoldValidator(schema=indexed_schema, strict=False)  # type: ignore[arg-type]
    result = indexed_validator._validate_with_schema(
        pd.DataFrame({"n": [1], "idx": ["a"], "extra": ["x"]})
    )
    assert result.valid is True


def test_ledger_nested_truncate_oserror(tmp_path: Path) -> None:
    os_module = SimpleNamespace(
        O_RDWR=os.O_RDWR,
        open=lambda *_a, **_k: 7,
        fstat=lambda _fd: SimpleNamespace(st_size=0),
        write=lambda *_a, payload: 2 if payload else (_ for _ in ()).throw(OSError("fail")),
        ftruncate=lambda *_a, **_k: (_ for _ in ()).throw(OSError("trunc")),
        close=lambda _fd: None,
    )
    writes = {"n": 0}

    def _write(_fd: int, payload: bytes) -> int:
        writes["n"] += 1
        if writes["n"] == 1:
            return 2
        raise OSError("rest")

    os_module.write = _write
    with pytest.raises(OSError, match="rest"):
        append_jsonl_payload(
            tmp_path / "out.jsonl",
            b"abcdef\n",
            open_flags=os.O_APPEND | os.O_CREAT | os.O_WRONLY,
            os_module=os_module,  # type: ignore[arg-type]
            flush_file_descriptor=lambda _fd: None,
        )


def test_registry_existing_artifact_and_lineage_without_stored_id(tmp_path: Path) -> None:
    store = FileContractRegistryStore(tmp_path / "reg.yaml")
    source = tmp_path / "src.yaml"
    source.write_text("ok", encoding="utf-8")
    artifact = tmp_path / "out.art"
    artifact.write_text("art", encoding="utf-8")
    result = store.validate_filesystem_consistency(
        SimpleNamespace(
            entries={
                "c.e": SimpleNamespace(
                    source_path=str(source),
                    published_artifacts=[str(artifact)],
                )
            }
        )  # type: ignore[arg-type]
    )
    assert result.valid is True
    lineage = FileLineageStore(tmp_path)
    fragment_path = lineage._fragment_path("frag-1")
    fragment_path.parent.mkdir(parents=True, exist_ok=True)
    fragment_path.write_text(
        json.dumps({"fragment_id": "frag-1", "nodes": [], "edges": []}),
        encoding="utf-8",
    )
    loaded = lineage._load_fragment("frag-1")
    assert loaded is not None
    assert loaded.fragment_id == "frag-1"


@pytest.mark.asyncio
async def test_expire_gold_empty_key_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    from bioetl.infrastructure.storage import (
        workflow_foreign_key_reconciliation_quarantine as quarantine,
    )

    monkeypatch.setattr(quarantine, "load_gold_writer_module", lambda: object())
    monkeypatch.setattr(
        quarantine,
        "_require_gold_writer",
        lambda _host: SimpleNamespace(
            _resolve_table_path=lambda name: f"/gold/{name}",
            _run_in_executor=AsyncMock(),
        ),
    )

    async def _cols(*_a: object, **_k: object) -> list[str]:
        return ["id", "_is_current", "_valid_to"]

    monkeypatch.setattr(quarantine, "_delta_table_column_names", _cols)
    monkeypatch.setattr(quarantine, "build_orphan_key_rows", lambda *_a, **_k: [])
    host = SimpleNamespace(
        gold_writer=object(),
        logger=MagicMock(),
        clock=SimpleNamespace(now=lambda: datetime(2024, 1, 1, tzinfo=UTC)),
    )
    request = ForeignKeyReconciliationRequest(
        source_table="src",
        reference_table="ref",
        source_key="parent_id",
        reference_key="id",
        primary_keys=("id",),
    )
    await expire_gold_orphan_rows(
        host,  # type: ignore[arg-type]
        request,
        orphan_rows=[
            {"id": "1", "parent_id": "missing", "_is_current": True, "_valid_to": None}
        ],
    )
