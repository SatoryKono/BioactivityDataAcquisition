"""Unit tests for Silver writer runtime support helpers."""

from __future__ import annotations

from dataclasses import dataclass, replace
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bioetl.domain.types.contract_rollout import ContractRolloutPolicy
from bioetl.infrastructure.storage.silver.runtime_helpers import (
    SilverWriterRuntimeServices,
    SilverWriterRuntimeServicesRequest,
)
from bioetl.infrastructure.storage.silver.writer_runtime_support import (
    _assign_runtime_services,
    _project_records_for_contract_version,
    _resolve_runtime_services_for_writer,
    _rewire_runtime_services,
    _write_dual_targets,
)


@dataclass(frozen=True)
class _ReplaceableMerged:
    _write_silver_merged_metadata: object


@dataclass(frozen=True)
class _ReplaceableValidation:
    _get_table_schema: object


@dataclass(frozen=True)
class _ReplaceableMetadata:
    _host: object | None


class _Writer:
    """Duck-typed writer for runtime support helpers."""

    def __init__(self) -> None:
        self.logger = MagicMock()
        self._pipeline_name = "chembl_activity"
        self._tracing = None
        self._contract_rollout_policy = None
        self._write_silver_merged_metadata = AsyncMock()
        self._get_table_schema = AsyncMock()
        self._execute_silver_write_pipeline = AsyncMock()
        self._write_single_target = AsyncMock()


@dataclass(frozen=True)
class _Invocation:
    """Minimal invocation dataclass compatible with dataclasses.replace."""

    table_name: str
    records: list[dict[str, object]]


def _services() -> SilverWriterRuntimeServices:
    return SilverWriterRuntimeServices(
        csv_exporter=MagicMock(),
        tracing=MagicMock(),
        write_policy=MagicMock(),
        metrics=MagicMock(),
        audit=MagicMock(),
        silver_validator=MagicMock(),
        metadata_writer=MagicMock(),
        metadata_coordinator=MagicMock(),
        lineage_store=MagicMock(),
        dq_calculator=MagicMock(),
        merge_resilience_policy=MagicMock(),
        contract_rollout_policy=MagicMock(),
        maintenance_operations=MagicMock(),
        metadata_operations=MagicMock(),
        validation_operations=MagicMock(),
        delta_operations=MagicMock(),
        arrow_operations=MagicMock(),
        merged_operations=MagicMock(),
        postwrite_operations=MagicMock(),
    )


def _request() -> SilverWriterRuntimeServicesRequest:
    return SilverWriterRuntimeServicesRequest(
        csv_exporter=MagicMock(),
        tracing=MagicMock(),
        write_policy=MagicMock(),
        metrics=MagicMock(),
        audit=MagicMock(),
        logger=MagicMock(),
        silver_validator=MagicMock(),
        metadata_writer=MagicMock(),
        metadata_coordinator=MagicMock(),
        lineage_store=MagicMock(),
        dq_calculator=MagicMock(),
        merge_resilience_policy=MagicMock(),
        contract_rollout_policy=MagicMock(spec=ContractRolloutPolicy),
        base_path="/tmp/silver",
        pipeline_name="chembl_activity",
        delta_module_loader=MagicMock(),
    )


@pytest.mark.unit
class TestSilverWriterRuntimeSupport:
    """Coverage tests for runtime support construction and dual-write behavior."""

    def test_resolve_runtime_services_returns_existing_or_builds_from_request(
        self,
    ) -> None:
        writer = _Writer()
        services = _services()
        request = _request()

        assert (
            _resolve_runtime_services_for_writer(
                writer=writer,
                base_path="/tmp/silver",
                runtime_services=services,
                runtime_request=request,
            )
            is services
        )

        with patch(
            "bioetl.infrastructure.storage.silver.writer_runtime_support.build_silver_writer_runtime_services",
            return_value=services,
        ) as build_services:
            resolved = _resolve_runtime_services_for_writer(
                writer=writer,
                base_path="/tmp/silver",
                runtime_services=None,
                runtime_request=request,
            )

        assert resolved is services
        build_request = build_services.call_args.args[0]
        assert build_request.logger is writer.logger
        assert build_request.pipeline_name == "chembl_activity"

    def test_assign_and_rewire_runtime_services(self) -> None:
        writer = _Writer()
        services = _services()
        services = replace(
            services,
            merged_operations=_ReplaceableMerged(_write_silver_merged_metadata=None),
            validation_operations=_ReplaceableValidation(_get_table_schema=None),
            metadata_operations=_ReplaceableMetadata(_host=None),
            postwrite_operations=None,
        )

        _assign_runtime_services(writer, services)
        assert writer._metrics is services.metrics
        assert writer._merged == services.merged_operations
        assert writer._postwrite is None

        _rewire_runtime_services(writer)
        assert (
            writer._merged._write_silver_merged_metadata
            == writer._write_silver_merged_metadata
        )
        assert writer._validation._get_table_schema == writer._get_table_schema
        assert writer._metadata._host is writer
        assert writer._postwrite is not None

    def test_project_records_for_contract_version_overrides_content_hash(self) -> None:
        projected = _project_records_for_contract_version(
            [
                {
                    "entity_id": "CHEMBL1",
                    "content_hash": "active",
                    "_content_hashes_by_version": {"v1": "legacy", "v2": "active-v2"},
                }
            ],
            contract_version="v1",
        )

        assert projected == [{"entity_id": "CHEMBL1", "content_hash": "legacy"}]

    @pytest.mark.asyncio
    async def test_write_dual_targets_returns_active_result_and_logs_failures(
        self,
    ) -> None:
        writer = _Writer()
        writer._contract_rollout_policy = SimpleNamespace(
            active_version="v2",
            write_versions=("v1", "v2"),
        )
        writer._write_single_target = AsyncMock(side_effect=["legacy", "active"])

        with (
            patch(
                "bioetl.infrastructure.storage.silver.writer_runtime_support.validate_write_versions"
            ),
            patch(
                "bioetl.infrastructure.storage.silver.writer_runtime_support.get_write_targets",
                return_value={"v1": "chembl.activity__v1", "v2": "chembl.activity"},
            ),
            patch(
                "bioetl.infrastructure.storage.silver.writer_runtime_support.iterate_write_targets",
                return_value=(("v1", "chembl.activity__v1"), ("v2", "chembl.activity")),
            ),
        ):
            result = await _write_dual_targets(
                writer,
                invocation=_Invocation(
                    table_name="chembl.activity",
                    records=[
                        {
                            "entity_id": "CHEMBL1",
                            "_content_hashes_by_version": {"v2": "new"},
                        }
                    ],
                ),
            )

        assert result == "active"
        assert writer._write_single_target.await_count == 2

        writer._write_single_target = AsyncMock(side_effect=RuntimeError("boom"))
        with (
            patch(
                "bioetl.infrastructure.storage.silver.writer_runtime_support.validate_write_versions"
            ),
            patch(
                "bioetl.infrastructure.storage.silver.writer_runtime_support.get_write_targets",
                return_value={"v1": "chembl.activity__v1"},
            ),
            patch(
                "bioetl.infrastructure.storage.silver.writer_runtime_support.iterate_write_targets",
                return_value=(("v1", "chembl.activity__v1"),),
            ),
            pytest.raises(RuntimeError, match="boom"),
        ):
            await _write_dual_targets(
                writer,
                invocation=_Invocation(
                    table_name="chembl.activity",
                    records=[{"entity_id": "CHEMBL1"}],
                ),
            )

        writer.logger.error.assert_called_once()
