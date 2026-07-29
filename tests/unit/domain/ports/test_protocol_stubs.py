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
"""Coverage tests for Protocol stub method bodies in domain ports.

These tests intentionally invoke protocol methods/properties directly on a dummy
instance so the ellipsis (`...`) stubs are executed and validated as callable.
"""

from __future__ import annotations

import inspect
import types
from pathlib import Path
from typing import Any, get_args, get_origin

import pytest

from bioetl.domain.ports import (
    BronzeStoragePort,
    BronzeDQAnalyzerPort,
    BronzeDQConfigPort,
    CheckpointPort,
    CircuitBreakerPort,
    ClockPort,
    DQMonitorPort,
    DQReportWriterPort,
    DataNormalizationPort,
    DataSourcePort,
    ExecutionObservabilityPort,
    ExecutionMetricsReadablePort,
    ExecutionMetricsRunnerPort,
    ExportCatalogPort,
    ExportWriterPort,
    FallbackPolicyPort,
    FilterableDataSourcePort,
    GoldDQAnalyzerPort,
    GoldDQConfigPort,
    GoldStoragePort,
    HealthCheckPort,
    HealthMonitorPort,
    HealthStatePort,
    IDMappingPort,
    LockPort,
    LoggerPort,
    MemoryMonitorPort,
    MergedStoragePort,
    MetricsExtractorPort,
    MetricsPort,
    QuarantinePort,
    RateLimiterPort,
    RunnablePort,
    RunnerFactoryPort,
    SilverDQAnalyzerPort,
    SilverDQConfigPort,
    SilverStoragePort,
    StorageLifecyclePort,
    StorageMaintenancePort,
    TracingPort,
)
from tests.helpers.clock import FIXED_TEST_TIME

PROTOCOL_CLASSES = [
    DataNormalizationPort,
    TracingPort,
    MetricsPort,
    LoggerPort,
    DQMonitorPort,
    BronzeStoragePort,
    SilverStoragePort,
    GoldStoragePort,
    MergedStoragePort,
    StorageLifecyclePort,
    StorageMaintenancePort,
    ExportCatalogPort,
    ExportWriterPort,
    QuarantinePort,
    LockPort,
    CheckpointPort,
    ClockPort,
    DataSourcePort,
    FilterableDataSourcePort,
    FallbackPolicyPort,
    BronzeDQConfigPort,
    SilverDQConfigPort,
    GoldDQConfigPort,
    RateLimiterPort,
    CircuitBreakerPort,
    IDMappingPort,
    RunnablePort,
    ExecutionObservabilityPort,
    ExecutionMetricsReadablePort,
    ExecutionMetricsRunnerPort,
    RunnerFactoryPort,
    MetricsExtractorPort,
    HealthCheckPort,
    HealthStatePort,
    HealthMonitorPort,
    BronzeDQAnalyzerPort,
    SilverDQAnalyzerPort,
    GoldDQAnalyzerPort,
    DQReportWriterPort,
    MemoryMonitorPort,
]


def _dummy_value(name: str, annotation: Any) -> Any:
    """Provide generic arguments for protocol method invocation."""
    lower_name = name.lower()
    by_name = _dummy_value_for_name(lower_name)
    if by_name is not None:
        return by_name
    return _dummy_value_for_annotation(name, annotation)


def _dummy_value_for_name(lower_name: str) -> Any | None:
    name_defaults: tuple[tuple[bool, Any], ...] = (
        ("path" in lower_name, Path(".")),
        (
            lower_name
            in {"records", "record", "primary_keys", "columns", "partition_cols"},
            [],
        ),
        (lower_name in {"filters", "fallback_mapping", "labels", "scd_config"}, {}),
        (
            lower_name in {"date", "ingestion_ts", "timestamp", "start_time"},
            FIXED_TEST_TIME,
        ),
        (
            lower_name
            in {"limit", "offset", "count", "rate", "capacity", "max_workers"},
            1,
        ),
        (
            "enabled" in lower_name
            or lower_name.startswith("is_")
            or "dry_run" in lower_name,
            False,
        ),
    )
    for predicate, value in name_defaults:
        if predicate:
            return value
    return None


def _dummy_value_for_annotation(name: str, annotation: Any) -> Any:
    origin = get_origin(annotation)
    if origin in (list, tuple, set, frozenset):
        return []
    if origin is dict:
        return {}
    if origin is types.UnionType:
        return _dummy_value_from_union(name, annotation)
    if origin is not None:
        if str(origin).endswith("Literal"):
            literal_args = get_args(annotation)
            return literal_args[0] if literal_args else "x"
        union_args = [arg for arg in get_args(annotation) if arg is not type(None)]
        if union_args:
            return _dummy_value(name, union_args[0])
    return _dummy_scalar_value(annotation)


def _dummy_value_from_union(name: str, annotation: Any) -> Any:
    union_args = [arg for arg in get_args(annotation) if arg is not type(None)]
    return _dummy_value(name, union_args[0]) if union_args else None


def _dummy_scalar_value(annotation: Any) -> Any:
    scalar_defaults = {
        int: 1,
        float: 1.0,
        bool: False,
        bytes: b"x",
        str: "x",
    }
    return scalar_defaults.get(annotation, "x")


def _build_required_arguments(method: Any) -> tuple[list[Any], dict[str, Any]]:
    """Build positional/keyword args for required parameters except self/cls."""
    signature = inspect.signature(method)
    args: list[Any] = []
    kwargs: dict[str, Any] = {}

    for idx, (name, param) in enumerate(signature.parameters.items()):
        if idx == 0 and name in {"self", "cls"}:
            continue
        if param.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue
        if param.default is not inspect.Parameter.empty:
            continue

        value = _dummy_value(name, param.annotation)
        if param.kind is inspect.Parameter.KEYWORD_ONLY:
            kwargs[name] = value
        else:
            args.append(value)

    return args, kwargs


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("protocol_cls", PROTOCOL_CLASSES, ids=lambda cls: cls.__name__)
async def test_protocol_stubs_are_callable(protocol_cls: type[Any]) -> None:
    """Directly invoke protocol stub bodies to ensure callable contracts."""
    dummy = object()

    for name, member in protocol_cls.__dict__.items():
        if name.startswith("__"):
            continue

        if isinstance(member, property):
            if member.fget is not None:
                member.fget(dummy)
            continue

        if inspect.isfunction(member):
            args, kwargs = _build_required_arguments(member)
            result = member(dummy, *args, **kwargs)
            if inspect.isawaitable(result):
                await result
