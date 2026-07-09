"""Real infrastructure adapter conformance checks for domain ports."""

from __future__ import annotations

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
from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
from bioetl.infrastructure.observability.logging import StructlogLogger
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.observability.unified_logger import UnifiedLogger
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.gold_writer import GoldWriter
from bioetl.infrastructure.storage.silver_writer import SilverWriter

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
    PortAdapterCase(BronzeStoragePort, BronzeWriter),
    PortAdapterCase(SilverStoragePort, SilverWriter),
    PortAdapterCase(GoldStoragePort, GoldWriter),
    PortAdapterCase(LoggerPort, NoOpLogger),
    PortAdapterCase(LoggerPort, UnifiedLogger),
    PortAdapterCase(LoggerPort, StructlogLogger),
    PortAdapterCase(CircuitBreakerPort, CircuitBreakerGuard),
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
    assert hasattr(case.adapter_cls, method_name), (
        f"{case.id} is missing method {method_name!r}"
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


def _storage_adapter_instances(tmp_path: Path) -> tuple[object, ...]:
    logger = NoOpLogger()
    metrics = NoOpMetrics(warn_on_use=False)
    return (
        BronzeWriter(tmp_path / "bronze", logger, metrics),
        SilverWriter(tmp_path / "silver", logger),
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
