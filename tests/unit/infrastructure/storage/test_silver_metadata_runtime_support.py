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
"""Unit tests for Silver metadata runtime support helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pyarrow as pa
import pytest

from bioetl.domain.ports.noop import NoOpMetadataWriter
from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics
from bioetl.infrastructure.storage.silver.operations.metadata_runtime_support import (
    _normalize_records_for_dq_metrics,
    best_effort_log,
    compute_dq_metrics_from_arrow_data,
    persist_silver_metadata,
    resolve_finalization_dq_metrics,
    resolve_flat_structure,
    resolve_manifest_id,
    resolve_transform_steps,
    resolve_transform_version,
    resolve_version_after,
    should_skip_silver_metadata_write,
    write_silver_metadata_file,
)


class _MetadataRuntimeOps:
    """Test double exposing the runtime helper surface."""

    def __init__(self) -> None:
        self._host = None
        self._logger = MagicMock()
        self._metadata_coordinator = object()
        self._metadata_writer = MagicMock()
        self._flat_structure = False
        self._dq_calculator = MagicMock()
        self.compute_dq_metrics = AsyncMock(
            return_value=BatchDQMetrics(total_records=1, valid_records=1)
        )
        self._write_silver_metadata_file = AsyncMock()


@pytest.mark.unit
class TestSilverMetadataRuntimeSupport:
    """Behavioral coverage for pure runtime helper functions."""

    def test_resolve_runtime_flags_and_steps(self) -> None:
        host = SimpleNamespace(
            _flat_structure=True,
            _transform_version=7,
            _transform_steps=["normalize", "enrich"],
        )

        assert resolve_flat_structure(host) is True
        assert resolve_transform_version(host) == "7"
        assert resolve_transform_steps(host) == ("normalize", "enrich")
        assert resolve_transform_steps(SimpleNamespace(_transform_steps="bad")) == ()

    def test_best_effort_log_calls_supported_level_only(self) -> None:
        logger = MagicMock()

        best_effort_log(logger, "debug", "hello")
        best_effort_log(object(), "debug", "ignored")

        logger.debug.assert_called_once_with("hello")

    def test_resolve_manifest_id_prefers_record_then_host_then_coordinator(
        self,
    ) -> None:
        ops = _MetadataRuntimeOps()

        assert (
            resolve_manifest_id(ops, records=[{"_manifest_id": "record-manifest"}])
            == "record-manifest"
        )

        ops._host = SimpleNamespace(manifest_id="host-manifest")
        assert resolve_manifest_id(ops, records=[{}]) == "host-manifest"

        ops._host = None
        ops._metadata_coordinator = SimpleNamespace(
            run_context=SimpleNamespace(manifest_id="coordinator-manifest")
        )
        assert resolve_manifest_id(ops, records=[{}]) == "coordinator-manifest"

        ops._metadata_coordinator = None
        assert resolve_manifest_id(ops, records=[{}]) is None
        ops._logger.debug.assert_called_once()

    @pytest.mark.asyncio
    async def test_persist_silver_metadata_parses_provider_and_entity(self) -> None:
        ops = _MetadataRuntimeOps()
        metadata = MagicMock()

        result = await persist_silver_metadata(
            ops,
            metadata=metadata,
            table_name="chembl.activity",
            table_path="/tmp/silver/chembl/activity",
        )

        assert result is None
        ops._write_silver_metadata_file.assert_awaited_once_with(
            table_path="/tmp/silver/chembl/activity",
            metadata=metadata,
            table_name="chembl.activity",
            provider_name="chembl",
            entity_name="activity",
        )

    @pytest.mark.asyncio
    async def test_resolve_finalization_dq_metrics_normalizes_structured_values(
        self,
    ) -> None:
        ops = _MetadataRuntimeOps()

        await resolve_finalization_dq_metrics(
            ops,
            _table_name="chembl.activity",
            records=[{"payload": {"b": 2, "a": 1}, "tags": ["x", "y"]}],
            validation_errors=("missing field",),
        )

        arrow_data = ops.compute_dq_metrics.await_args.kwargs["arrow_data"]
        row = arrow_data.to_pylist()[0]
        assert row["payload"] == '{"a":1,"b":2}'
        assert row["tags"] == '["x","y"]'
        assert ops.compute_dq_metrics.await_args.kwargs["validation_errors"] == (
            "missing field",
        )

    @pytest.mark.asyncio
    async def test_resolve_version_after_uses_host_getter_or_defaults_zero(
        self,
    ) -> None:
        ops = _MetadataRuntimeOps()
        ops._host = SimpleNamespace(_get_delta_version=AsyncMock(return_value=9))

        assert await resolve_version_after(ops, "/tmp/silver/path") == 9
        assert (
            await resolve_version_after(_MetadataRuntimeOps(), "/tmp/silver/path") == 0
        )

    @pytest.mark.asyncio
    async def test_compute_dq_metrics_from_arrow_data_handles_missing_and_present_calculator(
        self,
    ) -> None:
        ops = _MetadataRuntimeOps()
        ops._dq_calculator = None

        empty_metrics = await compute_dq_metrics_from_arrow_data(
            ops,
            pa.table({"entity_id": ["CHEMBL1"]}),
        )

        assert empty_metrics.total_records == 0
        ops._logger.warning.assert_called_once()

        ops = _MetadataRuntimeOps()
        ops._dq_calculator.calculate.return_value = BatchDQMetrics(
            total_records=1,
            valid_records=1,
        )
        metrics = await compute_dq_metrics_from_arrow_data(
            ops,
            pa.table({"entity_id": ["CHEMBL1"]}),
            quarantined_count=2,
            validation_errors=("warn",),
        )

        assert metrics.total_records == 1
        dq_input = ops._dq_calculator.calculate.call_args.args[0]
        assert dq_input.existing_schema_fields == {"entity_id"}
        assert dq_input.quarantined_count == 2
        assert dq_input.validation_errors == ["warn"]

    async def test_compute_dq_metrics_from_empty_arrow_table_keeps_schema(
        self,
    ) -> None:
        ops = _MetadataRuntimeOps()
        ops._dq_calculator.calculate.return_value = BatchDQMetrics()
        empty_table = pa.table({"entity_id": pa.array([], type=pa.string())})

        await compute_dq_metrics_from_arrow_data(ops, empty_table)

        dq_input = ops._dq_calculator.calculate.call_args.args[0]
        assert dq_input.records == []
        assert dq_input.existing_schema_fields == {"entity_id"}

    def test_should_skip_silver_metadata_write_covers_all_guard_paths(self) -> None:
        ops = _MetadataRuntimeOps()
        assert should_skip_silver_metadata_write(ops, records=[]) is True

        ops._metadata_writer = NoOpMetadataWriter()
        assert (
            should_skip_silver_metadata_write(
                ops,
                records=[{"entity_id": "CHEMBL1"}],
            )
            is True
        )

        ops._metadata_writer = MagicMock()
        ops._metadata_coordinator = None
        with pytest.raises(
            RuntimeError,
            match="MetadataCoordinator with create_silver_metadata_bundle is required",
        ):
            should_skip_silver_metadata_write(
                ops,
                records=[{"entity_id": "CHEMBL1"}],
            )

        ops._metadata_coordinator = object()
        assert (
            should_skip_silver_metadata_write(
                ops,
                records=[{"entity_id": "CHEMBL1"}],
            )
            is False
        )

    @pytest.mark.asyncio
    async def test_write_silver_metadata_file_handles_multiple_writer_signatures(
        self,
    ) -> None:
        ops = _MetadataRuntimeOps()
        metadata = MagicMock()

        ops._metadata_writer = None
        await write_silver_metadata_file(
            ops,
            table_path="/tmp/silver/chembl/activity",
            metadata=metadata,
            table_name="chembl.activity",
            provider_name="chembl",
            entity_name="activity",
        )
        ops._logger.info.assert_called_once()

        ops = _MetadataRuntimeOps()
        ops._metadata_writer.write_silver_metadata = AsyncMock()
        await write_silver_metadata_file(
            ops,
            table_path="/tmp/silver/chembl/activity",
            metadata=metadata,
            table_name="chembl.activity",
            provider_name="chembl",
            entity_name="activity",
        )
        ops._metadata_writer.write_silver_metadata.assert_awaited_once_with(
            base_path="/tmp/silver/chembl/activity",
            metadata=metadata,
            table_name="chembl.activity",
            flat_structure=False,
            provider="chembl",
            entity="activity",
        )

        class _LegacyWriter:
            def __init__(self) -> None:
                self.calls: list[tuple[object, ...]] = []

            async def write_silver_metadata(
                self,
                path: str,
                metadata_arg: object,
                *,
                table_name: str | None = None,
                flat_structure: bool = False,
                provider: str | None = None,
                entity: str | None = None,
            ) -> None:
                self.calls.append(
                    (
                        (path, metadata_arg),
                        {
                            "table_name": table_name,
                            "flat_structure": flat_structure,
                            "provider": provider,
                            "entity": entity,
                        },
                    )
                )

        ops = _MetadataRuntimeOps()
        ops._metadata_writer = _LegacyWriter()
        await write_silver_metadata_file(
            ops,
            table_path="/tmp/silver/chembl/activity",
            metadata=metadata,
            table_name="chembl.activity",
            provider_name="chembl",
            entity_name="activity",
        )
        args, kwargs = ops._metadata_writer.calls[0]
        assert args == ("/tmp/silver/chembl/activity", metadata)
        assert kwargs["provider"] == "chembl"

    def test_normalize_records_for_dq_metrics_keeps_scalars_and_serializes_nested(
        self,
    ) -> None:
        normalized = _normalize_records_for_dq_metrics(
            [{"entity_id": "CHEMBL1", "payload": {"b": 2, "a": 1}}]
        )

        assert normalized[0]["entity_id"] == "CHEMBL1"
        assert normalized[0]["payload"] == '{"a":1,"b":2}'
