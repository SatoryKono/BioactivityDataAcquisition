# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Real infrastructure adapter conformance checks for domain ports."""

from __future__ import annotations

from bioetl.infrastructure.storage.silver.runtime_helpers import (
    SilverWriterRuntimeServicesRequest,
)

from tests.helpers.clock import fixed_test_clock

import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import structlog

from bioetl.domain.ports import (
    BronzeStoragePort,
    CircuitBreakerPort,
    GoldStoragePort,
    LoggerPort,
    SilverStoragePort,
)
from bioetl.domain.ports.noop import NoOpMetadataWriter, NoOpMetrics
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
from bioetl.infrastructure.observability.logging import StructlogLogger
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.observability.unified_logger import UnifiedLogger
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.gold_writer import GoldWriter
from bioetl.infrastructure.storage.silver_writer import SilverWriter
from bioetl.infrastructure.storage.delta_reader import DeltaReader
from bioetl.application.services.lineage.metadata_coordinator import MetadataCoordinator
from bioetl.composition.bootstrap.runtime.assay_replay_capture import RequestReader
from bioetl.domain.ports.adr import AdrServicePort
from bioetl.domain.ports.config.publication_vocabulary_port import (
    PublicationVocabularyPort,
)
from bioetl.domain.ports.control_plane.artifact_byte_comparison import (
    ArtifactByteComparisonPort,
)
from bioetl.domain.ports.control_plane.lineage import LineageStorePort
from bioetl.domain.ports.control_plane.run_ledger import RunLedgerPort
from bioetl.domain.ports.control_plane.run_manifest import RunManifestPort
from bioetl.domain.ports.control_plane.workflow_execution_state import (
    WorkflowExecutionStatePort,
)
from bioetl.domain.ports.control_plane.workflow_ledger import WorkflowLedgerPort
from bioetl.domain.ports.control_plane.workflow_manifest import WorkflowManifestPort
from bioetl.domain.ports.data_source import DataSourcePort
from bioetl.domain.ports.delta_reader import DeltaReaderPort
from bioetl.domain.ports.export import ExportCatalogPort
from bioetl.domain.ports.export import ExportWriterPort
from bioetl.domain.ports.metadata.coordinator import MetadataCoordinatorPort
from bioetl.domain.ports.observability.metrics import MetricsPort
from bioetl.domain.ports.protein_classification import ProteinClassificationPort
from bioetl.domain.ports.runtime.locking import LockPort
from bioetl.domain.ports.stage_accounting import StageAccountingPort
from bioetl.domain.ports.workflow_foreign_key_reconciliation import (
    ForeignKeyReconciliationPort,
)
from bioetl.domain.ports.workflow_row_reconciliation import RowReconciliationPort
from bioetl.domain.run_reports.accounting import StageAccountingAccumulator
from bioetl.infrastructure.adapters.base import BaseHttpAdapter
from bioetl.infrastructure.adapters.chembl.protein_classification_graph import (
    ChEMBLProteinClassificationGraph,
)
from bioetl.infrastructure.adapters.sync_base import BaseSyncAdapter
from bioetl.infrastructure.adr.fs_adr_service import FilesystemAdrCatalog
from bioetl.infrastructure.config.publication_controlled_vocabulary_loader import (
    PublicationControlledVocabularyLoader,
)
from bioetl.infrastructure.control_plane.artifact_byte_comparison import (
    FileArtifactByteComparisonAdapter,
)
from bioetl.infrastructure.control_plane.file_lineage_store import FileLineageStore
from bioetl.infrastructure.control_plane.file_run_ledger_store import FileRunLedgerStore
from bioetl.infrastructure.control_plane.file_run_manifest_store import (
    FileRunManifestStore,
)
from bioetl.infrastructure.control_plane.file_workflow_execution_state_store import (
    FileWorkflowExecutionStateStore,
)
from bioetl.infrastructure.control_plane.file_workflow_ledger_store import (
    FileWorkflowLedgerStore,
)
from bioetl.infrastructure.control_plane.file_workflow_manifest_store import (
    FileWorkflowManifestStore,
)
from bioetl.infrastructure.export.export_catalog_adapter import ExportCatalogAdapter
from bioetl.infrastructure.export.export_writer_adapter import ExportWriterAdapter
from bioetl.infrastructure.locking.memory_lock import MemoryLock
from bioetl.infrastructure.observability.prometheus_metrics import PrometheusMetrics
from bioetl.infrastructure.storage.composite_replay_inputs import (
    CompositeReplayInputReader,
)
from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation import (
    SilverForeignKeyReconciliationAdapter,
)
from bioetl.infrastructure.storage.workflow_row_reconciliation import (
    StorageRowReconciliationAdapter,
)

from bioetl.domain.ports.audit import AuditPort
from bioetl.domain.ports.control_plane.effective_config_artifact import (
    EffectiveConfigArtifactStorePort,
)
from bioetl.domain.ports.export import DebugExportPort
from bioetl.domain.ports.idmapping import IDMappingSourceReaderPort
from bioetl.domain.ports.metadata.writer import MetadataWriterPort
from bioetl.domain.ports.observability.metrics import (
    HealthMetricsExpositionPort,
    MetricsPublisherPort,
    MetricsServerPort,
)
from bioetl.domain.ports.quality.dq_report import DQReportWriterPort
from bioetl.domain.ports.runtime.checkpoint import CheckpointPort
from bioetl.domain.ports.runtime.composite_checkpoint import CompositeCheckpointPort
from bioetl.domain.ports.storage.run_report_store import RunReportStorePort
from bioetl.infrastructure.adapters.crossref import CrossRefAdapter
from bioetl.infrastructure.adapters.input.idmapping_csv_reader_adapter import (
    IDMappingCsvReaderAdapter,
)
from bioetl.infrastructure.adapters.pubchem import PubChemAdapter
from bioetl.infrastructure.audit.file_audit import FileAuditAdapter
from bioetl.infrastructure.checkpoint.local_checkpoint import LocalCheckpointAdapter
from bioetl.infrastructure.control_plane.file_effective_config_artifact_store import (
    FileEffectiveConfigArtifactStore,
)
from bioetl.infrastructure.export.debug_export_adapter import DebugExportAdapter
from bioetl.infrastructure.export.dq_report_writer import DQReportWriter
from bioetl.infrastructure.observability.health_metrics_exposition import (
    HealthMetricsExpositionAdapter,
)
from bioetl.infrastructure.observability.metrics_publisher_adapter import (
    MetricsPublisherAdapter,
)
from bioetl.infrastructure.observability.metrics_server_adapter import (
    MetricsServerAdapter,
)
from bioetl.infrastructure.storage.metadata_writer import MetadataWriter
from bioetl.infrastructure.storage.run_report_store_adapter import (
    FileRunReportStoreAdapter,
)
from bioetl.infrastructure.storage.support.checkpoint_writer import (
    FileCompositeCheckpointWriter,
)

pytestmark = pytest.mark.architecture


@dataclass(frozen=True)
class PortAdapterCase:
    """Pair one domain port with one concrete infrastructure adapter."""

    port_cls: type[Any]
    adapter_cls: type[Any]

    @property
    def id(self) -> str:
        return f"{self.adapter_cls.__name__}->{self.port_cls.__name__}"


PORT_ADAPTER_CASES = (
    PortAdapterCase(AdrServicePort, FilesystemAdrCatalog),
    PortAdapterCase(ArtifactByteComparisonPort, FileArtifactByteComparisonAdapter),
    PortAdapterCase(BronzeStoragePort, BronzeWriter),
    PortAdapterCase(CircuitBreakerPort, CircuitBreakerGuard),
    PortAdapterCase(DeltaReaderPort, DeltaReader),
    PortAdapterCase(DeltaReaderPort, CompositeReplayInputReader),
    PortAdapterCase(DeltaReaderPort, RequestReader),
    PortAdapterCase(ExportCatalogPort, ExportCatalogAdapter),
    PortAdapterCase(ExportWriterPort, ExportWriterAdapter),
    PortAdapterCase(
        ForeignKeyReconciliationPort, SilverForeignKeyReconciliationAdapter
    ),
    PortAdapterCase(GoldStoragePort, GoldWriter),
    PortAdapterCase(LineageStorePort, FileLineageStore),
    PortAdapterCase(LockPort, MemoryLock),
    PortAdapterCase(LoggerPort, NoOpLogger),
    PortAdapterCase(LoggerPort, StructlogLogger),
    PortAdapterCase(LoggerPort, UnifiedLogger),
    PortAdapterCase(MetadataCoordinatorPort, MetadataCoordinator),
    PortAdapterCase(MetricsPort, PrometheusMetrics),
    PortAdapterCase(ProteinClassificationPort, ChEMBLProteinClassificationGraph),
    PortAdapterCase(PublicationVocabularyPort, PublicationControlledVocabularyLoader),
    PortAdapterCase(RowReconciliationPort, StorageRowReconciliationAdapter),
    PortAdapterCase(RunLedgerPort, FileRunLedgerStore),
    PortAdapterCase(RunManifestPort, FileRunManifestStore),
    PortAdapterCase(SilverStoragePort, SilverWriter),
    PortAdapterCase(StageAccountingPort, StageAccountingAccumulator),
    PortAdapterCase(WorkflowExecutionStatePort, FileWorkflowExecutionStateStore),
    PortAdapterCase(WorkflowLedgerPort, FileWorkflowLedgerStore),
    PortAdapterCase(WorkflowManifestPort, FileWorkflowManifestStore    PortAdapterCase(AuditPort, FileAuditAdapter),
    PortAdapterCase(CheckpointPort, LocalCheckpointAdapter),
    PortAdapterCase(CompositeCheckpointPort, FileCompositeCheckpointWriter),
    PortAdapterCase(DataSourcePort, CrossRefAdapter),
    PortAdapterCase(DataSourcePort, PubChemAdapter),
    PortAdapterCase(DebugExportPort, DebugExportAdapter),
    PortAdapterCase(DQReportWriterPort, DQReportWriter),
    PortAdapterCase(EffectiveConfigArtifactStorePort, FileEffectiveConfigArtifactStore),
    PortAdapterCase(HealthMetricsExpositionPort, HealthMetricsExpositionAdapter),
    PortAdapterCase(IDMappingSourceReaderPort, IDMappingCsvReaderAdapter),
    PortAdapterCase(MetadataWriterPort, NoOpMetadataWriter),
    PortAdapterCase(MetadataWriterPort, MetadataWriter),
    PortAdapterCase(MetricsPort, NoOpMetrics),
    PortAdapterCase(MetricsPublisherPort, MetricsPublisherAdapter),
    PortAdapterCase(MetricsServerPort, MetricsServerAdapter),
    PortAdapterCase(RunReportStorePort, FileRunReportStoreAdapter),
),
)


def _iter_protocol_methods(port_cls: type[Any]) -> list[tuple[str, Any]]:
    """Return public method stubs declared directly by a Protocol port."""
    return [
        (name, member)
        for name, member in port_cls.__dict__.items()
        if not name.startswith("_") and inspect.isfunction(member)
    ]


def _drop_receiver(signature: inspect.Signature) -> list[inspect.Parameter]:
    params = list(signature.parameters.values())
    if params and params[0].name in {"self", "cls"}:
        return params[1:]
    return params


def _has_varargs(params: list[inspect.Parameter]) -> bool:
    return any(param.kind is inspect.Parameter.VAR_POSITIONAL for param in params)


def _has_varkw(params: list[inspect.Parameter]) -> bool:
    return any(param.kind is inspect.Parameter.VAR_KEYWORD for param in params)


def _named_params(
    params: list[inspect.Parameter],
) -> dict[str, inspect.Parameter]:
    return {
        param.name: param
        for param in params
        if param.kind
        in {
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        }
    }


def _assert_param_kind_compatible(
    *,
    port_param: inspect.Parameter,
    adapter_param: inspect.Parameter,
    case: PortAdapterCase,
    method_name: str,
) -> None:
    if port_param.kind is inspect.Parameter.KEYWORD_ONLY:
        assert adapter_param.kind in {
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        }, (
            f"{case.id}.{method_name} cannot accept keyword-only port parameter "
            f"{port_param.name!r}: adapter kind is {adapter_param.kind}"
        )
        return
    assert adapter_param.kind in {
        inspect.Parameter.POSITIONAL_ONLY,
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
    }, (
        f"{case.id}.{method_name} cannot accept positional port parameter "
        f"{port_param.name!r}: adapter kind is {adapter_param.kind}"
    )


def _assert_port_param_is_supported(
    *,
    port_param: inspect.Parameter,
    adapter_params_by_name: dict[str, inspect.Parameter],
    adapter_has_varargs: bool,
    adapter_has_varkw: bool,
    case: PortAdapterCase,
    method_name: str,
) -> None:
    if port_param.kind is inspect.Parameter.VAR_POSITIONAL:
        assert adapter_has_varargs, f"{case.id}.{method_name} is missing *args"
        return
    if port_param.kind is inspect.Parameter.VAR_KEYWORD:
        assert adapter_has_varkw, f"{case.id}.{method_name} is missing **kwargs"
        return

    adapter_param = adapter_params_by_name.get(port_param.name)
    if adapter_param is None:
        assert adapter_has_varkw, (
            f"{case.id}.{method_name} is missing port parameter {port_param.name!r}"
        )
        return

    _assert_param_kind_compatible(
        port_param=port_param,
        adapter_param=adapter_param,
        case=case,
        method_name=method_name,
    )


def _is_required(param: inspect.Parameter) -> bool:
    return param.default is inspect.Parameter.empty and param.kind in {
        inspect.Parameter.POSITIONAL_ONLY,
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
        inspect.Parameter.KEYWORD_ONLY,
    }


def _assert_no_required_adapter_param_outside_port(
    *,
    port_params: list[inspect.Parameter],
    adapter_params: list[inspect.Parameter],
    case: PortAdapterCase,
    method_name: str,
) -> None:
    port_names = {param.name for param in _named_params(port_params).values()}
    port_accepts_varargs = _has_varargs(port_params)
    port_accepts_varkw = _has_varkw(port_params)

    unexpected_required: list[str] = []
    for param in adapter_params:
        if not _is_required(param) or param.name in port_names:
            continue
        if (
            param.kind is inspect.Parameter.POSITIONAL_ONLY and port_accepts_varargs
        ) or (param.kind is inspect.Parameter.KEYWORD_ONLY and port_accepts_varkw):
            continue
        unexpected_required.append(param.name)

    assert not unexpected_required, (
        f"{case.id}.{method_name} adds required parameters outside the port: "
        f"{unexpected_required}"
    )


def _assert_method_conforms(
    *,
    case: PortAdapterCase,
    method_name: str,
    port_method: Any,
) -> None:
    method_owner = next(
        (cls for cls in case.adapter_cls.__mro__ if method_name in cls.__dict__),
        None,
    )
    assert method_owner is not None, f"{case.id} is missing method {method_name!r}"
    assert method_owner is not case.port_cls, (
        f"{case.id}.{method_name} is inherited only from the port protocol"
    )
    adapter_method = getattr(case.adapter_cls, method_name)
    assert inspect.iscoroutinefunction(adapter_method) is inspect.iscoroutinefunction(
        port_method
    ), f"{case.id}.{method_name} async/sync shape differs from the port"

    port_params = _drop_receiver(inspect.signature(port_method))
    adapter_params = _drop_receiver(inspect.signature(adapter_method))
    adapter_params_by_name = _named_params(adapter_params)
    adapter_has_varargs = _has_varargs(adapter_params)
    adapter_has_varkw = _has_varkw(adapter_params)

    for port_param in port_params:
        _assert_port_param_is_supported(
            port_param=port_param,
            adapter_params_by_name=adapter_params_by_name,
            adapter_has_varargs=adapter_has_varargs,
            adapter_has_varkw=adapter_has_varkw,
            case=case,
            method_name=method_name,
        )

    _assert_no_required_adapter_param_outside_port(
        port_params=port_params,
        adapter_params=adapter_params,
        case=case,
        method_name=method_name,
    )


@pytest.mark.parametrize(
    "case",
    PORT_ADAPTER_CASES,
    ids=lambda case: case.id,
)
def test_infrastructure_adapter_signatures_conform_to_ports(
    case: PortAdapterCase,
) -> None:
    """Concrete adapters must keep method signatures compatible with ports."""
    for method_name, port_method in _iter_protocol_methods(case.port_cls):
        _assert_method_conforms(
            case=case,
            method_name=method_name,
            port_method=port_method,
        )


@pytest.mark.parametrize(
    "adapter_cls",
    [BaseHttpAdapter, BaseSyncAdapter],
    ids=lambda cls: cls.__name__,
)
def test_protocol_stub_is_not_accepted_as_adapter_implementation(
    adapter_cls: type[Any],
) -> None:
    """Base adapters cannot pass by inheriting the protocol's stub method."""
    case = PortAdapterCase(DataSourcePort, adapter_cls)
    with pytest.raises(AssertionError, match="inherited only from the port protocol"):
        _assert_method_conforms(
            case=case,
            method_name="fetch",
            port_method=DataSourcePort.fetch,
        )


def _storage_adapter_instances(tmp_path: Path) -> tuple[object, ...]:
    """Build storage adapter instances for structural protocol checks."""
    logger = NoOpLogger()
    metrics = NoOpMetrics(warn_on_use=False)
    return (
        BronzeWriter(tmp_path / "bronze", logger, metrics),
        SilverWriter(
            tmp_path / "silver",
            logger,
            runtime_request=SilverWriterRuntimeServicesRequest(
                clock=fixed_test_clock()
            ),
        ),
        GoldWriter(tmp_path / "gold", logger),
    )


def test_runtime_checkable_storage_ports_accept_real_adapters(tmp_path: Path) -> None:
    """Runtime-checkable storage ports must accept the concrete writer adapters."""
    bronze, silver, gold = _storage_adapter_instances(tmp_path)

    assert isinstance(bronze, BronzeStoragePort)
    assert isinstance(silver, SilverStoragePort)
    assert isinstance(gold, GoldStoragePort)


def test_runtime_checkable_observability_ports_accept_real_adapters() -> None:
    """Runtime-checkable observability/resilience ports must accept real adapters."""
    assert isinstance(NoOpLogger(), LoggerPort)
    assert isinstance(UnifiedLogger("chembl_activity", "run-123"), LoggerPort)
    assert isinstance(StructlogLogger(structlog.get_logger("bioetl.test")), LoggerPort)
    assert isinstance(CircuitBreakerGuard(provider="chembl"), CircuitBreakerPort)


_ADAPTER_CONSTRUCTOR_SUFFIXES = (
    "Adapter",
    "Writer",
    "Reader",
    "Store",
    "Catalog",
    "Guard",
    "Logger",
    "Metrics",
    "Graph",
    "Loader",
    "Lock",
    "Coordinator",
    "Accumulator",
)

# Discovered constructors that are intentionally outside PORT_ADAPTER_CASES:
# stdlib noise (DictReader/Lock/RLock) plus composition helpers that are not
# port-matrix adapters. Keep sorted; never put FutureAdapter-style new ports here.
_DISCOVERED_BINDING_EXCLUSIONS = frozenset(
    {
        "BatchWriter",
        "ChemblPolicyRegistryLoader",
        "DictReader",
        "FileArchiveStore",
        "FileControlPlaneArtifactLifecycleStore",
        "FileHistoricalReplayClosureStore",
        "FileHistoricalReplayUniverseStore",
        "FileProviderHealthEvidenceStore",
        "FileSystemEnumLoader",
        "FileWorkflowTransformArtifactStore",
        "LazyFactoryCatalog",
        "Lock",
        "ProteinClassTargetTypeMappingLoader",
        "ProviderStore",
        "PublicationTypeClassificationLoader",
        "RLock",
        "UnifiedQuarantineAdapter",
    }
)


def _instantiated_adapter_names(py_files: list[Path]) -> set[str]:
    """Find adapter-like constructors without consulting the conformance matrix."""
    import ast

    names: set[str] = set()
    for py_file in py_files:
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name):
                name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                name = node.func.attr
            else:
                continue
            if name.endswith(_ADAPTER_CONSTRUCTOR_SUFFIXES):
                names.add(name)
    return names


def test_production_adapter_discovery_does_not_depend_on_matrix(
    tmp_path: Path,
) -> None:
    """New conventional adapter names are discovered before matrix registration."""
    composition = tmp_path / "composition.py"
    composition.write_text(
        "class FutureAdapter:\n    pass\n\nFutureAdapter()\n",
        encoding="utf-8",
    )
    assert _instantiated_adapter_names([composition]) == {"FutureAdapter"}


def test_discovered_binding_exclusions_stay_disjoint_from_matrix() -> None:
    """Exclusions must not hide constructors already tracked by the matrix."""
    tracked = {case.adapter_cls.__name__ for case in PORT_ADAPTER_CASES}
    overlap = tracked & _DISCOVERED_BINDING_EXCLUSIONS
    assert not overlap, f"Matrix adapters listed as discovery exclusions: {overlap}"


def test_missing_production_binding_detected() -> None:
    """Production bindings must be tracked in PORT_ADAPTER_CASES or excluded."""
    composition_dir = (
        Path(__file__).resolve().parents[2] / "src" / "bioetl" / "composition"
    )
    assert composition_dir.is_dir(), (
        f"Composition directory is missing: {composition_dir}"
    )

    def raise_walk_error(error: OSError) -> None:
        raise error

    py_files = sorted(
        directory / filename
        for directory, _, filenames in composition_dir.walk(on_error=raise_walk_error)
        for filename in filenames
        if filename.endswith(".py")
    )
    assert py_files, f"No production composition modules found under {composition_dir}"

    instantiated_adapters = _instantiated_adapter_names(py_files)
    tracked_adapters = {case.adapter_cls.__name__ for case in PORT_ADAPTER_CASES}
    missing = instantiated_adapters - tracked_adapters - _DISCOVERED_BINDING_EXCLUSIONS
    assert not missing, (
        f"Production bindings missing from conformance matrix: {missing}"
    )
