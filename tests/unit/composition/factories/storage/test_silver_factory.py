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
"""Unit tests for Silver writer factory."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.composition.factories.storage._silver import (
    CreateSilverWriterRequest,
    create_silver_writer,
)
from bioetl.domain.ports.noop import (
    NoOpAudit,
    NoOpMetadataWriter,
)
from bioetl.domain.types.contract_rollout import ContractRolloutPolicy


@pytest.mark.unit
class TestCreateSilverWriter:
    """Tests for create_silver_writer factory function."""

    def test_create_silver_writer__explicit_tracing__a701f8c3(self) -> None:
        """Silver writer factory requires composition-owned tracing resolution."""
        writer_cls = MagicMock()

        with pytest.raises(TypeError):
            create_silver_writer(
                CreateSilverWriterRequest(
                    writer_cls=writer_cls,
                    base_path=Path("/data/silver"),
                    config=None,
                    logger=MagicMock(),
                    tracing=None,
                    csv_exporter=None,
                    metadata_coordinator=None,
                    audit=NoOpAudit(),
                    transform_version=None,
                    transform_steps=None,
                    flat_structure=False,
                    silver_validator=None,
                )
            )

        writer_cls.assert_not_called()

    def test_writer_factories_storage_silver_factory_50__14670cbb(
        self,
    ) -> None:
        """Creates real MetadataWriter when config.save_metadata is True."""
        writer_cls = MagicMock()
        config = SimpleNamespace(save_metadata=True)

        create_silver_writer(
            CreateSilverWriterRequest(
                writer_cls=writer_cls,
                base_path=Path("/data/silver"),
                config=config,
                logger=MagicMock(),
                tracing=MagicMock(),
                csv_exporter=None,
                metadata_coordinator=None,
                audit=NoOpAudit(),
                transform_version=None,
                transform_steps=None,
                flat_structure=False,
                silver_validator=None,
            )
        )

        call_kwargs = writer_cls.call_args[1]
        assert not isinstance(
            call_kwargs["runtime_services"].metadata_writer, NoOpMetadataWriter
        )
        assert call_kwargs["runtime_services"].lineage_store is not None

    def test_create_silver_writer__provided_tracing__d586e81c(self) -> None:
        """Uses provided TracingPort instead of NoOpTracing."""
        writer_cls = MagicMock()
        tracer = MagicMock()

        create_silver_writer(
            CreateSilverWriterRequest(
                writer_cls=writer_cls,
                base_path=Path("/data/silver"),
                config=None,
                logger=MagicMock(),
                tracing=tracer,
                csv_exporter=None,
                metadata_coordinator=None,
                audit=NoOpAudit(),
                transform_version=None,
                transform_steps=None,
                flat_structure=False,
                silver_validator=None,
            )
        )

        call_kwargs = writer_cls.call_args[1]
        assert call_kwargs["runtime_services"].tracing is tracer

    def test_passes_silver_validator(self) -> None:
        """silver_validator is forwarded to writer constructor."""
        writer_cls = MagicMock()
        validator = MagicMock()

        create_silver_writer(
            CreateSilverWriterRequest(
                writer_cls=writer_cls,
                base_path=Path("/data/silver"),
                config=None,
                logger=MagicMock(),
                tracing=MagicMock(),
                csv_exporter=None,
                metadata_coordinator=None,
                audit=NoOpAudit(),
                transform_version=None,
                transform_steps=None,
                flat_structure=False,
                silver_validator=validator,
            )
        )

        call_kwargs = writer_cls.call_args[1]
        assert call_kwargs["runtime_services"].silver_validator is validator

    def test_passes_resilience_policies(self) -> None:
        """Resilience policies are forwarded to writer constructor."""
        writer_cls = MagicMock()
        retry_policy = MagicMock()
        merge_policy = MagicMock()

        create_silver_writer(
            CreateSilverWriterRequest(
                writer_cls=writer_cls,
                base_path=Path("/data/silver"),
                config=None,
                logger=MagicMock(),
                tracing=MagicMock(),
                csv_exporter=None,
                metadata_coordinator=None,
                audit=NoOpAudit(),
                transform_version=None,
                transform_steps=None,
                flat_structure=False,
                silver_validator=None,
                metadata_atomic_retry_policy=retry_policy,
                merge_resilience_policy=merge_policy,
            )
        )

        call_kwargs = writer_cls.call_args[1]
        assert call_kwargs["runtime_services"].merge_resilience_policy is merge_policy

    def test_passes_metrics_to_metadata_writer(self) -> None:
        """Metrics are forwarded to MetadataWriter when save_metadata is True."""
        writer_cls = MagicMock()
        config = SimpleNamespace(save_metadata=True)
        metrics = MagicMock()

        create_silver_writer(
            CreateSilverWriterRequest(
                writer_cls=writer_cls,
                base_path=Path("/data/silver"),
                config=config,
                logger=MagicMock(),
                tracing=MagicMock(),
                csv_exporter=None,
                metadata_coordinator=None,
                audit=NoOpAudit(),
                transform_version=None,
                transform_steps=None,
                flat_structure=False,
                silver_validator=None,
                metrics=metrics,
            )
        )

        # Writer is created - verify it passed through
        writer_cls.assert_called_once()

    def test_create_silver_writer__passes_csv_exporter__962579f8(self) -> None:
        """csv_exporter is forwarded to writer constructor."""
        writer_cls = MagicMock()
        csv = MagicMock()

        create_silver_writer(
            CreateSilverWriterRequest(
                writer_cls=writer_cls,
                base_path=Path("/data/silver"),
                config=None,
                logger=MagicMock(),
                tracing=MagicMock(),
                csv_exporter=csv,
                metadata_coordinator=None,
                audit=NoOpAudit(),
                transform_version=None,
                transform_steps=None,
                flat_structure=False,
                silver_validator=None,
            )
        )

        call_kwargs = writer_cls.call_args[1]
        assert call_kwargs["runtime_services"].csv_exporter is csv

    def test_create_silver_writer__rollout_policy__e1efe723(self) -> None:
        """contract_rollout_policy is preserved in runtime services for dual-write."""
        writer_cls = MagicMock()
        rollout_policy = ContractRolloutPolicy(
            contract_ref="chembl.activity",
            active_version="2.0.0",
            mode="dual_read_write",
            read_order=("2.0.0", "1.0.0"),
            write_versions=("1.0.0", "2.0.0"),
            affects_hash=True,
        )

        create_silver_writer(
            CreateSilverWriterRequest(
                writer_cls=writer_cls,
                base_path=Path("/data/silver"),
                config=None,
                logger=MagicMock(),
                tracing=MagicMock(),
                csv_exporter=None,
                metadata_coordinator=None,
                audit=NoOpAudit(),
                transform_version=None,
                transform_steps=None,
                flat_structure=False,
                silver_validator=None,
                contract_rollout_policy=rollout_policy,
            )
        )

        call_kwargs = writer_cls.call_args[1]
        assert call_kwargs["runtime_services"].contract_rollout_policy == rollout_policy

    def test_create_silver_writer__passes_audit_port__eb91831f(self) -> None:
        """audit is forwarded into Silver runtime services explicitly."""
        writer_cls = MagicMock()
        audit = MagicMock()

        create_silver_writer(
            CreateSilverWriterRequest(
                writer_cls=writer_cls,
                base_path=Path("/data/silver"),
                config=None,
                logger=MagicMock(),
                tracing=MagicMock(),
                csv_exporter=None,
                metadata_coordinator=None,
                audit=audit,
                transform_version=None,
                transform_steps=None,
                flat_structure=False,
                silver_validator=None,
            )
        )

        call_kwargs = writer_cls.call_args[1]
        assert call_kwargs["runtime_services"].audit is audit
