"""Stream B INF: leftover Gold I/O branches without write_deltalake."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.domain.medallion import GoldWriteMode
from bioetl.domain.ports.noop._memory_metadata import NoOpMetadataWriter
from bioetl.domain.types import ScdConfig
from bioetl.infrastructure.storage.gold import io_delta_mixins as mixins
from bioetl.infrastructure.storage.gold import io_delta_runtime as runtime
from bioetl.infrastructure.storage.gold import io_execution as io_exec
from bioetl.infrastructure.storage.gold import io_mixin as io_mix
from bioetl.infrastructure.storage.gold import pipeline_helpers as pipe
from bioetl.infrastructure.storage.gold import writer_implementation as impl
from bioetl.infrastructure.storage.gold.io_preparation import (
    _GoldMergedWriteRequest,
    _PreparedGoldMergedWrite,
)
from bioetl.infrastructure.storage.gold.metadata_mixin import GoldWriterMetadataMixin
from bioetl.infrastructure.storage.gold.pipeline_helpers import (
    GoldWriteDispatchContext,
    GoldWritePostwriteContext,
    GoldWriteRequest,
    PreparedGoldWriteContext,
)
from bioetl.infrastructure.storage.gold.read_cleanup_mixin import (
    GoldWriterReadCleanupMixin,
)
from bioetl.infrastructure.storage.gold.validation_mixin import (
    GoldWriterValidationMixin,
)
from bioetl.infrastructure.storage.gold_writer import GoldWriter, _normalize_scd_config
from bioetl.infrastructure.storage.writer_common import (
    get_write_targets,
    iterate_write_targets,
    validate_write_versions,
)

pytestmark = pytest.mark.unit


class _MergedHost(io_mix._GoldWriterMergedDispatchMixin):
    def __init__(self) -> None:
        self.logger = MagicMock()
        self.csv_exporter = None
        self._write_scd2 = AsyncMock()
        self._write_simple = AsyncMock()

    def _resolve_table_path(self, table_name: str) -> str:
        return f"/gold/{table_name}"

    async def _validate_records_against_schema(self, *_a: object, **_k: object) -> None:
        return None

    def _validate_schema_strict(self, *_a: object, **_k: object) -> None:
        return None


class _SchemaFailHost(GoldWriterValidationMixin):
    async def _run_in_executor(self, func: object, *args: object) -> object:
        del args
        return func()  # type: ignore[operator]


def _request(**overrides: object) -> GoldWriteRequest:
    payload: dict[str, object] = {
        "table_name": "chembl/activity",
        "records": [{"id": 1}],
        "schema": MagicMock(),
        "mode": "overwrite",
    }
    payload.update(overrides)
    return GoldWriteRequest(**payload)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_write_gold_merged_delta_and_csv_sidecar_use_fakes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    writes: list[tuple[object, object]] = []

    class _Module:
        @staticmethod
        def write_deltalake(
            table_path: object, arrow_table: object, **_k: object
        ) -> None:
            writes.append((table_path, arrow_table))

    monkeypatch.setattr(io_exec, "_load_gold_writer_module", lambda: _Module)
    host = SimpleNamespace(
        csv_exporter=SimpleNamespace(export=AsyncMock()),
        _run_in_executor=AsyncMock(side_effect=lambda func, *a: func(*a)),
        _write_gold_merged_metadata=AsyncMock(),
    )
    prepared = _PreparedGoldMergedWrite(
        request=_GoldMergedWriteRequest(
            table_name="chembl/activity",
            records=[{"id": 1}],
            primary_keys=["id"],
            schema=MagicMock(),
            completed_at=None,
            run_id="r1",
            sources_used=None,
        ),
        table_path="/gold/activity",
        arrow_table=MagicMock(),
    )
    await io_exec._write_gold_merged_delta(host, prepared)  # type: ignore[arg-type]
    await io_exec._export_gold_merged_csv(host, prepared)  # type: ignore[arg-type]
    await io_exec._write_gold_merged_sidecar(host, prepared)  # type: ignore[arg-type]
    assert writes == [("/gold/activity", prepared.arrow_table)]
    host.csv_exporter.export.assert_awaited_once()
    host._write_gold_merged_metadata.assert_awaited_once()


@pytest.mark.asyncio
async def test_execute_gold_merged_write_success_and_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _GoldMergedWriteRequest(
        table_name="chembl/activity",
        records=[{"id": 1}],
        primary_keys=["id"],
        schema=MagicMock(),
        completed_at=None,
        run_id="r1",
        sources_used=None,
    )
    prepared = SimpleNamespace()
    monkeypatch.setattr(
        "bioetl.infrastructure.storage.gold.io_preparation._prepare_gold_merged_write",
        AsyncMock(return_value=prepared),
    )
    monkeypatch.setattr(
        "bioetl.infrastructure.storage.gold.io_preparation._log_prepared_gold_merged_write",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(io_exec, "_complete_gold_merged_write", AsyncMock())
    await io_exec._execute_gold_merged_write(SimpleNamespace(), request)  # type: ignore[arg-type]
    io_exec._complete_gold_merged_write.assert_awaited_once()  # type: ignore[attr-defined]

    monkeypatch.setattr(
        "bioetl.infrastructure.storage.gold.io_preparation._prepare_gold_merged_write",
        AsyncMock(side_effect=ValueError("schema")),
    )
    with pytest.raises(ValueError, match="schema"):
        await io_exec._execute_gold_merged_write(SimpleNamespace(), request)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_merged_write_empty_records_and_missing_schema() -> None:
    host = _MergedHost()
    await host.write_gold_merged("chembl/activity", [])
    host.logger.warning.assert_called_once()
    with pytest.raises(ValueError, match="strict schema"):
        await host.write_gold_merged("chembl/activity", [{"id": 1}], schema=None)


@pytest.mark.asyncio
async def test_write_gold_merged_dispatches_execute(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host = _MergedHost()
    executed: list[object] = []

    async def _execute(writer: object, request: object) -> None:
        executed.append((writer, request.table_name))  # type: ignore[union-attr]

    monkeypatch.setattr(
        "bioetl.infrastructure.storage.gold.io_execution._execute_gold_merged_write",
        _execute,
    )
    await host.write_gold_merged(
        "chembl/activity", [{"id": 1}], schema=MagicMock()
    )
    assert executed and executed[0][1] == "chembl/activity"


@pytest.mark.asyncio
async def test_complete_gold_merged_write_runs_three_stages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stages: list[str] = []

    async def _delta(*_a: object, **_k: object) -> None:
        stages.append("delta")

    async def _csv(*_a: object, **_k: object) -> None:
        stages.append("csv")

    async def _sidecar(*_a: object, **_k: object) -> None:
        stages.append("sidecar")

    monkeypatch.setattr(io_exec, "_write_gold_merged_delta", _delta)
    monkeypatch.setattr(io_exec, "_export_gold_merged_csv", _csv)
    monkeypatch.setattr(io_exec, "_write_gold_merged_sidecar", _sidecar)
    await io_exec._complete_gold_merged_write(SimpleNamespace(), SimpleNamespace())  # type: ignore[arg-type]
    assert stages == ["delta", "csv", "sidecar"]


@pytest.mark.asyncio
async def test_dispatch_write_routes_scd2_and_simple(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host = _MergedHost()
    scd = ScdConfig(business_key="id")
    monkeypatch.setattr(
        io_mix,
        "_load_gold_writer_module",
        lambda: SimpleNamespace(_normalize_scd_config=lambda cfg, _keys: cfg),
    )
    prepared = PreparedGoldWriteContext(
        table_name="activity",
        table_path="/gold/activity",
        validated_mode=GoldWriteMode.SCD2,
    )
    request = _request(
        mode="scd2",
        scd_config=scd,
        ingestion_ts=datetime(2026, 1, 1, tzinfo=UTC),
        primary_keys=["id"],
    )
    await host._dispatch_write(
        GoldWriteDispatchContext(prepared=prepared, request=request)
    )
    host._write_scd2.assert_awaited_once()

    prepared_simple = PreparedGoldWriteContext(
        table_name="activity",
        table_path="/gold/activity",
        validated_mode=GoldWriteMode.OVERWRITE,
    )
    await host._dispatch_write(
        GoldWriteDispatchContext(prepared=prepared_simple, request=_request())
    )
    host._write_simple.assert_awaited_once()


@pytest.mark.asyncio
async def test_scd2_write_and_merge_use_mocked_delta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executed: list[object] = []

    async def _execute(host: object, module: object, prepared: object) -> None:
        del host
        executed.append((module, prepared))

    monkeypatch.setattr(mixins, "_prepare_scd2_gold_write", lambda **_k: "prepared")
    monkeypatch.setattr(mixins, "_load_gold_writer_module", lambda: "module")
    monkeypatch.setattr(mixins, "_execute_prepared_scd2_gold_write", _execute)
    host = mixins._GoldWriterScd2MergeMixin()
    await host._write_scd2(
        "/gold/t",
        [{"id": 1, "content_hash": "a"}],
        ScdConfig(business_key="id"),
        None,
        datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert executed == [("module", "prepared")]

    import pyarrow as pa

    host._to_arrow_table = lambda *_a, **_k: pa.table(  # type: ignore[method-assign]
        {"id": [1], "content_hash": ["abc"]}
    )

    async def _run(func: object, *_a: object) -> object:
        return func()  # type: ignore[operator]

    host._run_in_executor = _run  # type: ignore[method-assign]
    merge = MagicMock()
    merge.when_matched_update.return_value = merge
    merge.when_not_matched_insert_all.return_value = merge
    dt = SimpleNamespace(merge=MagicMock(return_value=merge))
    await host._merge_scd2(
        dt,
        [{"id": 1}],
        "id",
        ScdConfig(business_key="id"),
        datetime(2026, 1, 1, tzinfo=UTC),
    )
    dt.merge.assert_called_once()
    merge.execute.assert_called_once()
    assert host._build_content_changed_predicate().startswith("source.content_hash")


@pytest.mark.asyncio
async def test_execute_prepared_scd2_delegates_to_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[str] = []

    async def _retry(*_a: object, **_k: object) -> None:
        seen.append("retry")

    monkeypatch.setattr(runtime, "_run_gold_write_with_retry", _retry)
    await runtime._execute_prepared_scd2_gold_write(
        SimpleNamespace(),  # type: ignore[arg-type]
        SimpleNamespace(),  # type: ignore[arg-type]
        SimpleNamespace(  # type: ignore[arg-type]
            table_path="p",
            records=[],
            business_key="id",
            scd_config=ScdConfig(business_key="id"),
            ingestion_ts=datetime(2026, 1, 1, tzinfo=UTC),
            partition_cols=None,
            column_order=None,
        ),
    )
    assert seen == ["retry"]


@pytest.mark.asyncio
async def test_single_target_validation_failure_and_dual_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Writer:
        logger = MagicMock()
        _contract_rollout_policy = SimpleNamespace(
            write_versions=["1.0.0", "1.1.0"],
            active_version="1.1.0",
        )

        async def _prepare_write_gold(self, **_k: object) -> object:
            raise ValueError("invalid schema")

        async def _dispatch_write(self, *_a: object, **_k: object) -> None:
            return None

        async def _post_write_gold(self, *_a: object, **_k: object) -> None:
            return None

        async def _write_single_target(self, *, request: GoldWriteRequest) -> None:
            if "1_1_0" in request.table_name:
                raise ValueError("second target failed")

    with pytest.raises(ValueError, match="invalid schema"):
        await impl._write_single_target_impl(_Writer(), request=_request())  # type: ignore[arg-type]

    monkeypatch.setattr(
        impl, "_project_records_for_gold_schema", lambda records, schema: records
    )
    policy = SimpleNamespace(for_version=lambda _v: MagicMock(strict=True))
    with pytest.raises(ValueError, match="second target failed"):
        await impl._write_dual_targets_impl(
            _Writer(),  # type: ignore[arg-type]
            request=_request(),
            schema_policy=policy,  # type: ignore[arg-type]
        )
    _Writer.logger.error.assert_called()
    missing = SimpleNamespace(for_version=lambda _v: None)
    with pytest.raises(ValueError, match="No Gold schema"):
        await impl._write_dual_targets_impl(
            _Writer(),  # type: ignore[arg-type]
            request=_request(),
            schema_policy=missing,  # type: ignore[arg-type]
        )


@pytest.mark.asyncio
async def test_pipeline_helpers_normalize_audit_and_writer_common() -> None:
    scd = ScdConfig(business_key="id")
    assert pipe.normalize_scd_config(scd, ["id"]) is scd
    host = SimpleNamespace(
        _audit=object(),
        _log_gold_audit=AsyncMock(),
        _write_gold_metadata=AsyncMock(),
    )
    context = GoldWritePostwriteContext(
        prepared=PreparedGoldWriteContext(
            table_name="activity",
            table_path="/gold/activity",
            validated_mode=GoldWriteMode.OVERWRITE,
        ),
        records=[{"id": 1}],
        ingestion_ts=None,
        run_id=None,
        scd_config=None,
        silver_refs=None,
        schema=MagicMock(),
    )
    await pipe.post_write_gold(host, context)  # type: ignore[arg-type]
    host._log_gold_audit.assert_awaited_once()
    validate_write_versions(["1.0.0"])
    targets = get_write_targets("activity", ["1.0.0"])
    assert iterate_write_targets(["1.0.0"], targets) == [("1.0.0", targets[0])]


@pytest.mark.asyncio
async def test_validation_schema_error_and_read_cleanup_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import pandera.errors

    class _Schema:
        strict = True

        def validate(self, _df: object, lazy: bool = False) -> None:
            del lazy
            raise pandera.errors.SchemaError("schema", "data", "required field missing")

    host = _SchemaFailHost()
    with pytest.raises(Exception, match="Schema validation failed|required"):
        await host._validate_records_against_schema([{"id": 1}], _Schema())

    class _ReadHost(GoldWriterReadCleanupMixin):
        def _resolve_table_path(self, table_name: str) -> str:
            return f"/gold/{table_name}"

        async def _run_in_executor(self, func: object, *args: object) -> object:
            del func, args
            from deltalake.exceptions import TableNotFoundError

            raise TableNotFoundError("missing")

    monkeypatch.setattr(
        "bioetl.infrastructure.storage.gold.read_cleanup_mixin._load_gold_writer_module",
        lambda: SimpleNamespace(DeltaTable=lambda *_a, **_k: object()),
    )
    with pytest.raises(FileNotFoundError, match="Gold table not found"):
        await _ReadHost().read_gold("activity")


@pytest.mark.asyncio
async def test_metadata_noop_and_gold_writer_dual_write_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Meta(GoldWriterMetadataMixin):
        def __init__(self) -> None:
            self._metadata_writer = NoOpMetadataWriter()

    await _Meta()._write_gold_merged_metadata(
        table_path="/gold/t", table_name="t", records=[{"id": 1}]
    )
    assert _normalize_scd_config(
        ScdConfig(business_key="id"), ["id"]
    ).business_keys == ("id",)
    writer = GoldWriter.__new__(GoldWriter)
    writer._contract_rollout_policy = None  # type: ignore[attr-defined]
    assert writer._should_dual_write() is False
    writer._contract_rollout_policy = SimpleNamespace(  # type: ignore[attr-defined]
        mode="dual_write", write_versions=["1.0.0", "1.1.0"]
    )
    assert writer._should_dual_write() is True

    impl_calls: list[str] = []

    async def _impl(host: object, *, request: object, schema_policy: object) -> None:
        del host, request, schema_policy
        impl_calls.append("impl")

    monkeypatch.setattr(
        "bioetl.infrastructure.storage.gold_writer._write_dual_targets_impl",
        _impl,
    )
    await GoldWriter._write_dual_targets(
        writer, request=_request(), schema_policy=MagicMock()
    )
    assert impl_calls == ["impl"]

    from bioetl.domain.types.gold_schema_policy import GoldSchemaPolicyByVersion
    from bioetl.domain.types.gold_schema_policy import GoldSchemaVersionPolicy

    schema = GoldSchemaPolicyByVersion(
        active_version="1.1.0",
        policies=(
            GoldSchemaVersionPolicy(version="1.0.0", schema=MagicMock()),
            GoldSchemaVersionPolicy(version="1.1.0", schema=MagicMock()),
        ),
    )
    writer._tracing = None  # type: ignore[attr-defined]
    writer._write_dual_targets = AsyncMock()  # type: ignore[method-assign]
    writer._write_single_target = AsyncMock()  # type: ignore[method-assign]
    writer._set_write_span_attributes = lambda *_a, **_k: None  # type: ignore[method-assign]
    await GoldWriter.write_gold(writer, "chembl/activity", [{"id": 1}], schema)
    writer._write_dual_targets.assert_awaited_once()  # type: ignore[attr-defined]
    writer._write_single_target.assert_not_awaited()  # type: ignore[attr-defined]


def test_delta_table_constructs_via_lazy_import(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bioetl.infrastructure.storage import gold_writer as gw

    constructed: list[object] = []

    class _DeltaTable:
        def __init__(self, *args: object, **kwargs: object) -> None:
            constructed.append((args, kwargs))

    monkeypatch.setattr(gw, "normalize_delta_filesystem_path", lambda path: str(path))
    monkeypatch.setattr("deltalake.DeltaTable", _DeltaTable)
    table = gw.delta_table("/gold/activity", version=1, without_files=True)
    assert isinstance(table, _DeltaTable)
    assert constructed
