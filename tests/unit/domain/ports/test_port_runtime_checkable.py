"""Tests for @runtime_checkable compliance of ALL domain port protocols.

Verifies that every port protocol is runtime_checkable and that concrete
implementations (stubs) satisfy isinstance checks — per ARCH-003 and TYPE-004.
"""

from __future__ import annotations

import pytest

from bioetl.domain.ports import (
    IDMappingPort,
    LockPort,
    MemoryMonitorPort,
    MetadataWriterPort,
    MetadataCoordinatorPort,
    GoldValidatorPort,
    SilverValidatorPort,
    ContractPolicyProtocol,
    BronzeStoragePort,
    BronzeDQConfigPort,
    GoldDQConfigPort,
    GoldStoragePort,
    SilverDQConfigPort,
    MergedStoragePort,
    BronzeDQAnalyzerPort,
    DQReportWriterPort,
    GoldDQAnalyzerPort,
    SilverDQAnalyzerPort,
    FallbackPolicyPort,
    QuarantinePort,
    AdrServicePort,
    AuditPort,
    BatchIdGeneratorPort,
    CheckpointPort,
    ClockPort,
    DomainConfigMapperPort,
    PipelineConfigLoaderPort,
    ExecutionObservabilityPort,
    ExecutionMetricsReadablePort,
    ExecutionMetricsRunnerPort,
    SettingsLoaderPort,
    PipelineSettingsPort,
    PipelineYamlConfigPort,
    SettingsPort,
    DataNormalizationPort,
    DataSourcePort,
    FilterableDataSourcePort,
    DeltaReaderPort,
    InputFilterPort,
    HealthCheckPort,
    HealthMonitorPort,
    HealthStatePort,
    DQMonitorPort,
    LoggerPort,
    MetricsPort,
    ExportCatalogPort,
    ExportWriterPort,
    TracingPort,
    PiiHasherPort,
    PipelineRegistryPort,
    RegistryAccessorPort,
    CircuitBreakerPort,
    RateLimiterPort,
    MetricsExtractorPort,
    PipelineDebugPort,
    RunnablePort,
    RunnerFactoryPort,
    JsonEncoderPort,
    ShutdownPort,
    SilverStoragePort,
    StorageLifecyclePort,
    StorageMaintenancePort,
)

ALL_PORT_PROTOCOLS = [
    AdrServicePort,
    AuditPort,
    BatchIdGeneratorPort,
    CheckpointPort,
    ClockPort,
    ContractPolicyProtocol,
    DataNormalizationPort,
    DataSourcePort,
    DeltaReaderPort,
    DomainConfigMapperPort,
    DQMonitorPort,
    DQReportWriterPort,
    ExportCatalogPort,
    ExportWriterPort,
    FallbackPolicyPort,
    FilterableDataSourcePort,
    GoldDQAnalyzerPort,
    GoldDQConfigPort,
    GoldValidatorPort,
    HealthCheckPort,
    HealthMonitorPort,
    HealthStatePort,
    IDMappingPort,
    InputFilterPort,
    JsonEncoderPort,
    LockPort,
    LoggerPort,
    MemoryMonitorPort,
    MetadataCoordinatorPort,
    MetadataWriterPort,
    ExecutionObservabilityPort,
    ExecutionMetricsReadablePort,
    ExecutionMetricsRunnerPort,
    MetricsExtractorPort,
    MetricsPort,
    PiiHasherPort,
    PipelineConfigLoaderPort,
    PipelineDebugPort,
    PipelineRegistryPort,
    PipelineSettingsPort,
    PipelineYamlConfigPort,
    QuarantinePort,
    RateLimiterPort,
    CircuitBreakerPort,
    RegistryAccessorPort,
    RunnablePort,
    RunnerFactoryPort,
    SettingsLoaderPort,
    SettingsPort,
    ShutdownPort,
    SilverDQAnalyzerPort,
    SilverDQConfigPort,
    SilverValidatorPort,
    BronzeStoragePort,
    SilverStoragePort,
    GoldStoragePort,
    MergedStoragePort,
    StorageLifecyclePort,
    StorageMaintenancePort,
    TracingPort,
    BronzeDQAnalyzerPort,
    BronzeDQConfigPort,
]


@pytest.mark.unit
class TestPortRuntimeCheckable:
    """Verify all port protocols are @runtime_checkable."""

    @pytest.mark.parametrize(
        "protocol_cls",
        ALL_PORT_PROTOCOLS,
        ids=lambda cls: cls.__name__,
    )
    def test_port_runtime_checkable__is_runtime_checkable__0b67223e(self, protocol_cls: type) -> None:
        """Each protocol MUST be @runtime_checkable per TYPE-004."""
        assert hasattr(protocol_cls, "__protocol_attrs__") or hasattr(
            protocol_cls, "_is_runtime_protocol"
        ), f"{protocol_cls.__name__} is not a Protocol"

        # Verify isinstance check doesn't raise (it won't match object, but
        # the call itself must not throw TypeError)
        result = isinstance(object(), protocol_cls)
        assert result is False


@pytest.mark.unit
class TestPortFacadeImports:
    """Verify all ports are importable from the facade package."""

    def test_all_ports_importable_from_facade(self) -> None:
        """ARCH-008: Ports MUST be importable from bioetl.domain.ports."""
        from bioetl.domain import ports

        expected_names = [
            "AdrServicePort",
            "AuditPort",
            "BatchIdGeneratorPort",
            "CheckpointPort",
            "ClockPort",
            "ContractPolicyProtocol",
            "DataNormalizationPort",
            "DataSourcePort",
            "DeltaReaderPort",
            "DomainConfigMapperPort",
            "DQMonitorPort",
            "DQReportWriterPort",
            "ExecutionObservabilityPort",
            "ExportCatalogPort",
            "ExportWriterPort",
            "ExecutionMetricsReadablePort",
            "ExecutionMetricsRunnerPort",
            "FallbackPolicyPort",
            "FilterableDataSourcePort",
            "GoldDQAnalyzerPort",
            "GoldDQConfigPort",
            "GoldValidatorPort",
            "HealthCheckPort",
            "HealthMonitorPort",
            "HealthStatePort",
            "IDMappingPort",
            "InputFilterPort",
            "JsonEncoderPort",
            "LockPort",
            "LoggerPort",
            "MemoryMonitorPort",
            "MetadataCoordinatorPort",
            "MetadataWriterPort",
            "MetricsExtractorPort",
            "MetricsPort",
            "PiiHasherPort",
            "PipelineConfigLoaderPort",
            "PipelineDebugPort",
            "PipelineRegistryPort",
            "PipelineSettingsPort",
            "PipelineYamlConfigPort",
            "QuarantinePort",
            "RateLimiterPort",
            "CircuitBreakerPort",
            "RegistryAccessorPort",
            "RunnablePort",
            "RunnerFactoryPort",
            "SettingsLoaderPort",
            "SettingsPort",
            "ShutdownPort",
            "SilverDQAnalyzerPort",
            "SilverDQConfigPort",
            "SilverValidatorPort",
            "BronzeStoragePort",
            "SilverStoragePort",
            "GoldStoragePort",
            "MergedStoragePort",
            "StorageLifecyclePort",
            "StorageMaintenancePort",
            "TracingPort",
            "BronzeDQAnalyzerPort",
            "BronzeDQConfigPort",
        ]
        for name in expected_names:
            assert hasattr(ports, name), f"{name} not exported from bioetl.domain.ports"

    def test_facade_all_contains_all_ports(self) -> None:
        """The __all__ of the ports package must include all port protocols."""
        from bioetl.domain.ports import __all__ as ports_all

        port_names = {cls.__name__ for cls in ALL_PORT_PROTOCOLS}
        missing = port_names - set(ports_all)
        assert not missing, f"Missing from __all__: {missing}"
