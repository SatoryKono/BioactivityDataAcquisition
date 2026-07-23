"""Unit tests for Bronze writer factory."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.composition.factories.storage._bronze import create_bronze_writer
from bioetl.domain.ports.noop import (
    NoOpAudit,
    NoOpMetadataWriter,
    NoOpTracing,
)


@pytest.mark.unit
class TestCreateBronzeWriter:
    """Tests for create_bronze_writer factory function."""

    def test_creates_writer_with_defaults(self) -> None:
        """Creates BronzeWriter with default flags when config is None."""
        writer_cls = MagicMock()
        expected = MagicMock()
        writer_cls.return_value = expected

        result = create_bronze_writer(
            writer_cls=writer_cls,
            base_path=Path("/data/bronze"),
            config=None,
            logger=MagicMock(),
            metrics=MagicMock(),
            tracing=NoOpTracing(),
            metadata_coordinator=None,
            audit=NoOpAudit(),
            flat_structure=False,
        )

        assert result is expected
        call_kwargs = writer_cls.call_args[1]
        assert call_kwargs["json_export"] == (False, None)
        runtime_services = call_kwargs["runtime_services"]
        assert runtime_services.save_metadata is False
        assert isinstance(runtime_services.tracing, NoOpTracing)
        assert isinstance(runtime_services.audit, NoOpAudit)
        assert isinstance(runtime_services.metadata_writer, NoOpMetadataWriter)

    def test_uses_config_flags(self) -> None:
        """Reads save_json and save_metadata from config."""
        writer_cls = MagicMock()
        config = SimpleNamespace(save_json=True, save_metadata=True)
        coordinator = MagicMock()

        create_bronze_writer(
            writer_cls=writer_cls,
            base_path=Path("/data/bronze"),
            config=config,
            logger=MagicMock(),
            metrics=MagicMock(),
            tracing=NoOpTracing(),
            metadata_coordinator=coordinator,
            audit=NoOpAudit(),
            flat_structure=False,
        )

        call_kwargs = writer_cls.call_args[1]
        assert call_kwargs["json_export"] == (True, None)
        assert call_kwargs["runtime_services"].save_metadata is True
        assert call_kwargs["runtime_services"].lineage_store is not None

    def test_uses_provided_tracing(self) -> None:
        """Uses provided TracingPort instead of NoOpTracing."""
        writer_cls = MagicMock()
        tracer = MagicMock()

        create_bronze_writer(
            writer_cls=writer_cls,
            base_path=Path("/data/bronze"),
            config=None,
            logger=MagicMock(),
            metrics=MagicMock(),
            tracing=tracer,
            metadata_coordinator=None,
            audit=NoOpAudit(),
            flat_structure=False,
        )

        call_kwargs = writer_cls.call_args[1]
        assert call_kwargs["runtime_services"].tracing is tracer

    def test_creates_metadata_writer_when_save_metadata(self) -> None:
        """Creates real MetadataWriter when save_metadata is True."""
        writer_cls = MagicMock()
        config = SimpleNamespace(save_json=False, save_metadata=True)
        coordinator = MagicMock()

        create_bronze_writer(
            writer_cls=writer_cls,
            base_path=Path("/data/bronze"),
            config=config,
            logger=MagicMock(),
            metrics=MagicMock(),
            tracing=NoOpTracing(),
            metadata_coordinator=coordinator,
            audit=NoOpAudit(),
            flat_structure=False,
        )

        call_kwargs = writer_cls.call_args[1]
        assert not isinstance(
            call_kwargs["runtime_services"].metadata_writer, NoOpMetadataWriter
        )

    def test_raises_when_save_metadata_enabled_without_coordinator(self) -> None:
        """save_metadata wiring must fail closed without a coordinator."""
        writer_cls = MagicMock()
        config = SimpleNamespace(save_json=False, save_metadata=True)

        with pytest.raises(
            RuntimeError,
            match="Bronze metadata publication requires MetadataCoordinator",
        ):
            create_bronze_writer(
                writer_cls=writer_cls,
                base_path=Path("/data/bronze"),
                config=config,
                logger=MagicMock(),
                metrics=MagicMock(),
                tracing=NoOpTracing(),
                metadata_coordinator=None,
                audit=NoOpAudit(),
                flat_structure=False,
            )

    def test_passes_flat_structure(self) -> None:
        """flat_structure flag is forwarded to writer constructor."""
        writer_cls = MagicMock()

        create_bronze_writer(
            writer_cls=writer_cls,
            base_path=Path("/data/bronze"),
            config=None,
            logger=MagicMock(),
            metrics=MagicMock(),
            tracing=NoOpTracing(),
            metadata_coordinator=None,
            audit=NoOpAudit(),
            flat_structure=True,
        )

        call_kwargs = writer_cls.call_args[1]
        assert call_kwargs["flat_structure"] is True

    def test_passes_metadata_coordinator(self) -> None:
        """metadata_coordinator is forwarded to writer constructor."""
        writer_cls = MagicMock()
        coordinator = MagicMock()

        create_bronze_writer(
            writer_cls=writer_cls,
            base_path=Path("/data/bronze"),
            config=None,
            logger=MagicMock(),
            metrics=MagicMock(),
            tracing=NoOpTracing(),
            metadata_coordinator=coordinator,
            audit=NoOpAudit(),
            flat_structure=False,
        )

        call_kwargs = writer_cls.call_args[1]
        assert call_kwargs["runtime_services"].metadata_coordinator is coordinator

    def test_passes_audit_port(self) -> None:
        """audit is forwarded into runtime services explicitly."""
        writer_cls = MagicMock()
        audit = MagicMock()

        create_bronze_writer(
            writer_cls=writer_cls,
            base_path=Path("/data/bronze"),
            config=None,
            logger=MagicMock(),
            metrics=MagicMock(),
            tracing=NoOpTracing(),
            metadata_coordinator=None,
            audit=audit,
            flat_structure=False,
        )

        call_kwargs = writer_cls.call_args[1]
        assert call_kwargs["runtime_services"].audit is audit
