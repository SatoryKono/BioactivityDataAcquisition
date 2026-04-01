"""Unit tests for Gold writer factory."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.composition.factories.storage._gold import create_gold_writer
from bioetl.domain.ports.noop import (
    NoOpMetadataWriter,
    NoOpTracing,
)
from bioetl.domain.types.contract_rollout import ContractRolloutPolicy


@pytest.mark.unit
class TestCreateGoldWriter:
    """Tests for create_gold_writer factory function."""

    def test_creates_writer_with_defaults(self) -> None:
        """Creates GoldWriter with NoOp defaults when config is None."""
        writer_cls = MagicMock()
        expected = MagicMock()
        writer_cls.return_value = expected

        result = create_gold_writer(
            writer_cls=writer_cls,
            base_path=Path("/data/gold"),
            config=None,
            logger=MagicMock(),
            tracing=None,
            csv_exporter=None,
            metadata_coordinator=None,
            transform_version=None,
            transform_steps=None,
            flat_structure=False,
        )

        assert result is expected
        call_kwargs = writer_cls.call_args[1]
        runtime_services = call_kwargs["runtime_services"]
        assert isinstance(runtime_services.tracing, NoOpTracing)
        assert isinstance(runtime_services.metadata_writer, NoOpMetadataWriter)

    def test_uses_config_save_metadata(self) -> None:
        """Creates real MetadataWriter when config.save_metadata is True."""
        writer_cls = MagicMock()
        config = SimpleNamespace(save_metadata=True)

        create_gold_writer(
            writer_cls=writer_cls,
            base_path=Path("/data/gold"),
            config=config,
            logger=MagicMock(),
            tracing=None,
            csv_exporter=None,
            metadata_coordinator=None,
            transform_version=None,
            transform_steps=None,
            flat_structure=False,
        )

        call_kwargs = writer_cls.call_args[1]
        assert not isinstance(
            call_kwargs["runtime_services"].metadata_writer, NoOpMetadataWriter
        )
        assert call_kwargs["runtime_services"].lineage_store is not None

    def test_uses_provided_tracing(self) -> None:
        """Uses provided TracingPort instead of NoOpTracing."""
        writer_cls = MagicMock()
        tracer = MagicMock()

        create_gold_writer(
            writer_cls=writer_cls,
            base_path=Path("/data/gold"),
            config=None,
            logger=MagicMock(),
            tracing=tracer,
            csv_exporter=None,
            metadata_coordinator=None,
            transform_version=None,
            transform_steps=None,
            flat_structure=False,
        )

        call_kwargs = writer_cls.call_args[1]
        assert call_kwargs["runtime_services"].tracing is tracer

    def test_passes_csv_exporter(self) -> None:
        """csv_exporter is forwarded to writer constructor."""
        writer_cls = MagicMock()
        csv = MagicMock()

        create_gold_writer(
            writer_cls=writer_cls,
            base_path=Path("/data/gold"),
            config=None,
            logger=MagicMock(),
            tracing=None,
            csv_exporter=csv,
            metadata_coordinator=None,
            transform_version=None,
            transform_steps=None,
            flat_structure=False,
        )

        call_kwargs = writer_cls.call_args[1]
        assert call_kwargs["runtime_services"].csv_exporter is csv

    def test_passes_transform_metadata(self) -> None:
        """transform_version and transform_steps are forwarded."""
        writer_cls = MagicMock()

        create_gold_writer(
            writer_cls=writer_cls,
            base_path=Path("/data/gold"),
            config=None,
            logger=MagicMock(),
            tracing=None,
            csv_exporter=None,
            metadata_coordinator=None,
            transform_version="1.2.0",
            transform_steps=("step_a", "step_b"),
            flat_structure=True,
        )

        call_kwargs = writer_cls.call_args[1]
        assert call_kwargs["transform_version"] == "1.2.0"
        assert call_kwargs["transform_steps"] == ("step_a", "step_b")
        assert call_kwargs["flat_structure"] is True

    def test_passes_contract_rollout_policy(self) -> None:
        """contract_rollout_policy is preserved in runtime services for dual-write."""
        writer_cls = MagicMock()
        rollout_policy = ContractRolloutPolicy(
            contract_ref="pubmed/publication",
            active_version="2.0.0",
            mode="dual_write",
            read_order=("2.0.0", "1.0.0"),
            write_versions=("1.0.0", "2.0.0"),
        )

        create_gold_writer(
            writer_cls=writer_cls,
            base_path=Path("/data/gold"),
            config=None,
            logger=MagicMock(),
            tracing=None,
            csv_exporter=None,
            metadata_coordinator=None,
            transform_version=None,
            transform_steps=None,
            flat_structure=False,
            contract_rollout_policy=rollout_policy,
        )

        call_kwargs = writer_cls.call_args[1]
        assert (
            call_kwargs["runtime_services"].contract_rollout_policy == rollout_policy
        )
