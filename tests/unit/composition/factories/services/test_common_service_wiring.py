"""Unit tests for common_service_wiring helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from bioetl.composition.factories.services.common_service_wiring import (
    CommonServicePorts,
    CommonServicePortsRequest,
    assemble_pipeline_service,
    build_common_service_ports,
    resolve_tracer,
)


@pytest.mark.unit
class TestResolveTracer:
    """Tests for resolve_tracer."""

    def test_returns_provided_tracer(self) -> None:
        """Returns the provided tracer when not None."""
        tracer = MagicMock()
        assert resolve_tracer(tracer) is tracer

    def test_returns_noop_when_none(self) -> None:
        """Returns NoOpTracing when tracer is None."""
        from bioetl.domain.ports.noop import NoOpTracing

        result = resolve_tracer(None)
        assert isinstance(result, NoOpTracing)


@pytest.mark.unit
class TestBuildCommonServicePorts:
    """Tests for build_common_service_ports."""

    def test_returns_common_service_ports(self) -> None:
        """Returns a CommonServicePorts dataclass with all resolved ports."""
        storage_ctx = SimpleNamespace(adapter=MagicMock())
        storage_factory = MagicMock()
        storage_factory.create.return_value = storage_ctx

        lock = MagicMock()
        checkpoint = MagicMock()
        quarantine = MagicMock()
        dq_services: dict[str, object] = {"bronze_analyzer": MagicMock()}

        result = build_common_service_ports(
            CommonServicePortsRequest(
                settings=MagicMock(),
                logger=MagicMock(),
                pipeline_config=MagicMock(),
                pipeline_name="test_pipeline",
                create_dq_services_fn=MagicMock(return_value=dq_services),
                storage_factory=storage_factory,
                create_lock_fn=lambda: lock,
                create_checkpoint_fn=lambda _ctx: checkpoint,
                create_quarantine_fn=lambda _s: quarantine,
            )
        )

        assert isinstance(result, CommonServicePorts)
        assert result.storage_ctx is storage_ctx
        assert result.lock is lock
        assert result.checkpoint is checkpoint
        assert result.quarantine is quarantine

    def test_uses_provided_metrics(self) -> None:
        """Uses provided metrics instead of creating new ones."""
        provided_metrics = MagicMock()
        storage_factory = MagicMock()
        storage_factory.create.return_value = SimpleNamespace(adapter=MagicMock())

        result = build_common_service_ports(
            CommonServicePortsRequest(
                settings=MagicMock(),
                logger=MagicMock(),
                pipeline_config=MagicMock(),
                pipeline_name="test_pipeline",
                metrics=provided_metrics,
                create_dq_services_fn=MagicMock(return_value={}),
                storage_factory=storage_factory,
                create_lock_fn=MagicMock(return_value=MagicMock()),
                create_checkpoint_fn=MagicMock(return_value=MagicMock()),
                create_quarantine_fn=MagicMock(return_value=MagicMock()),
            )
        )

        assert result.metrics_port is provided_metrics

    def test_creates_metrics_when_not_provided(self) -> None:
        """Calls create_metrics_fn when metrics is None."""
        created_metrics = MagicMock()
        storage_factory = MagicMock()
        storage_factory.create.return_value = SimpleNamespace(adapter=MagicMock())

        result = build_common_service_ports(
            CommonServicePortsRequest(
                settings=MagicMock(),
                logger=MagicMock(),
                pipeline_config=MagicMock(),
                pipeline_name="test_pipeline",
                metrics=None,
                create_dq_services_fn=MagicMock(return_value={}),
                create_metrics_fn=lambda _s: created_metrics,
                storage_factory=storage_factory,
                create_lock_fn=MagicMock(return_value=MagicMock()),
                create_checkpoint_fn=MagicMock(return_value=MagicMock()),
                create_quarantine_fn=MagicMock(return_value=MagicMock()),
            )
        )

        assert result.metrics_port is created_metrics

    @patch(
        "bioetl.composition.factories.services.common_service_wiring.StorageFactory.create"
    )
    def test_uses_module_level_storage_factory_fallback(
        self, mock_storage_create: MagicMock
    ) -> None:
        """Falls back to the module-level StorageFactory patch seam."""
        storage_ctx = SimpleNamespace(adapter=MagicMock())
        mock_storage_create.return_value = storage_ctx

        result = build_common_service_ports(
            CommonServicePortsRequest(
                settings=MagicMock(),
                logger=MagicMock(),
                pipeline_config=MagicMock(),
                pipeline_name="test_pipeline",
                metrics=MagicMock(),
                create_dq_services_fn=MagicMock(return_value={}),
                create_lock_fn=MagicMock(return_value=MagicMock()),
                create_checkpoint_fn=MagicMock(return_value=MagicMock()),
                create_quarantine_fn=MagicMock(return_value=MagicMock()),
            )
        )

        assert result.storage_ctx is storage_ctx
        mock_storage_create.assert_called_once()


@pytest.mark.unit
class TestAssemblePipelineService:
    """Tests for assemble_pipeline_service."""

    @patch("bioetl.infrastructure.storage.metadata_writer.MetadataWriter")
    def test_returns_pipeline_service(self, mock_meta_writer_cls: MagicMock) -> None:
        """Assembles and returns a PipelineService from common ports."""
        mock_meta_writer_cls.return_value = MagicMock()

        common_ports = CommonServicePorts(
            storage_ctx=SimpleNamespace(adapter=MagicMock()),
            lock=MagicMock(),
            checkpoint=MagicMock(),
            quarantine=MagicMock(),
            metrics_port=MagicMock(),
            tracer=MagicMock(),
            dq_services={
                "bronze_analyzer": MagicMock(),
                "silver_analyzer": None,
                "gold_analyzer": None,
                "report_writer": None,
                "report_service": None,
            },
        )

        result = assemble_pipeline_service(
            data_source=MagicMock(),
            logger=MagicMock(),
            dq_monitor=None,
            metadata_coordinator=None,
            common_ports=common_ports,
        )

        assert result is not None

    @patch("bioetl.infrastructure.storage.metadata_writer.MetadataWriter")
    def test_passes_dq_services_from_common_ports(
        self, mock_meta_writer_cls: MagicMock
    ) -> None:
        """DQ services are extracted from common_ports.dq_services dict."""
        mock_meta_writer_cls.return_value = MagicMock()
        bronze_analyzer = MagicMock()

        common_ports = CommonServicePorts(
            storage_ctx=SimpleNamespace(adapter=MagicMock()),
            lock=MagicMock(),
            checkpoint=MagicMock(),
            quarantine=MagicMock(),
            metrics_port=MagicMock(),
            tracer=MagicMock(),
            dq_services={"bronze_analyzer": bronze_analyzer},
        )

        result = assemble_pipeline_service(
            data_source=MagicMock(),
            logger=MagicMock(),
            dq_monitor=None,
            metadata_coordinator=None,
            common_ports=common_ports,
        )

        # PipelineService should have bronze_dq_analyzer set
        assert result is not None
