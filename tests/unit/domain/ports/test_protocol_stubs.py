"""Coverage tests for Protocol stub method bodies in domain ports.

These tests intentionally invoke protocol methods/properties directly on a dummy
instance so the ellipsis (`...`) stubs are executed and validated as callable.
"""

from __future__ import annotations

import inspect
import types
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, get_args, get_origin

import pytest

from bioetl.domain.ports.checkpoint import CheckpointPort
from bioetl.domain.ports.data_normalization import DataNormalizationPort
from bioetl.domain.ports.data_source import DataSourcePort, FilterableDataSourcePort
from bioetl.domain.ports.dq_config import (
    BronzeDQConfigPort,
    GoldDQConfigPort,
    SilverDQConfigPort,
)
from bioetl.domain.ports.dq_report import (
    BronzeDQAnalyzerPort,
    DQReportWriterPort,
    GoldDQAnalyzerPort,
    SilverDQAnalyzerPort,
)
from bioetl.domain.ports.health_check import (
    HealthCheckPort,
    HealthMonitorPort,
    HealthStatePort,
)
from bioetl.domain.ports.idmapping import IDMappingPort
from bioetl.domain.ports.locking import LockPort
from bioetl.domain.ports.memory import MemoryMonitorPort
from bioetl.domain.ports.observability import (
    DQMonitorPort,
    LoggerPort,
    MetricsPort,
    TracingPort,
)
from bioetl.domain.ports.quarantine import QuarantinePort
from bioetl.domain.ports.resilience import CircuitBreakerPort, RateLimiterPort
from bioetl.domain.ports.runner import (
    MetricsExtractorPort,
    RunnablePort,
    RunnerFactoryPort,
)
from bioetl.domain.ports.storage import StoragePort

PROTOCOL_CLASSES = [
    DataNormalizationPort,
    TracingPort,
    MetricsPort,
    LoggerPort,
    DQMonitorPort,
    StoragePort,
    QuarantinePort,
    LockPort,
    CheckpointPort,
    DataSourcePort,
    FilterableDataSourcePort,
    BronzeDQConfigPort,
    SilverDQConfigPort,
    GoldDQConfigPort,
    RateLimiterPort,
    CircuitBreakerPort,
    IDMappingPort,
    RunnablePort,
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

    if "path" in lower_name:
        return Path(".")
    if lower_name in {"records", "record", "primary_keys", "columns", "partition_cols"}:
        return []
    if lower_name in {"filters", "fallback_mapping", "labels", "scd_config"}:
        return {}
    if lower_name in {"date", "ingestion_ts", "timestamp", "start_time"}:
        return datetime.now(UTC)
    if lower_name in {"limit", "offset", "count", "rate", "capacity", "max_workers"}:
        return 1
    if (
        "enabled" in lower_name
        or lower_name.startswith("is_")
        or "dry_run" in lower_name
    ):
        return False

    origin = get_origin(annotation)
    if origin in (list, tuple, set, frozenset):
        return []
    if origin is dict:
        return {}
    if origin is types.UnionType:
        union_args = [arg for arg in get_args(annotation) if arg is not type(None)]
        return _dummy_value(name, union_args[0]) if union_args else None
    if origin is not None:
        if str(origin).endswith("Literal"):
            literal_args = get_args(annotation)
            return literal_args[0] if literal_args else "x"
        union_args = [arg for arg in get_args(annotation) if arg is not type(None)]
        if union_args:
            return _dummy_value(name, union_args[0])

    if annotation in (int,):
        return 1
    if annotation in (float,):
        return 1.0
    if annotation in (bool,):
        return False
    if annotation in (bytes,):
        return b"x"
    if annotation in (str,):
        return "x"

    return "x"


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
