from __future__ import annotations

import importlib
import sys
import typing
from datetime import date
from types import MappingProxyType, ModuleType

import pytest


pytestmark = pytest.mark.unit


def _get_origin_stub(_tp) -> None:
    return None


def _get_args_stub(tp: object) -> tuple[object, ...]:
    return getattr(tp, "__union_args__", ())


def _validation_disabled() -> bool:
    return False


def _validation_enabled() -> bool:
    return True


def _record_and_return_false(calls: list[str]) -> bool:
    calls.append("validated")
    return False


def _install_fake_pandera_modules(monkeypatch) -> tuple[ModuleType, type]:
    typing_inspect_module = ModuleType("typing_inspect")
    typing_inspect_module.get_origin = _get_origin_stub
    typing_inspect_module.get_args = _get_args_stub

    pandera_module = ModuleType("pandera")
    pandera_backends = ModuleType("pandera.backends")
    pandera_backends_pandas = ModuleType("pandera.backends.pandas")
    pandera_builtin_checks = ModuleType("pandera.backends.pandas.builtin_checks")
    pandera_api = ModuleType("pandera.api")
    pandera_function_dispatch = ModuleType("pandera.api.function_dispatch")

    class FakeDispatcher:
        def __init__(self) -> None:
            self._function_registry: dict[object, object] = {}

        def __call__(self, *args: object, **kwargs: object) -> object:
            return ("original", args, kwargs)

        def register(self, fn: object) -> None:
            self._function_registry[object()] = fn

    pandera_function_dispatch.Dispatcher = FakeDispatcher

    monkeypatch.setitem(sys.modules, "typing_inspect", typing_inspect_module)
    monkeypatch.setitem(sys.modules, "pandera", pandera_module)
    monkeypatch.setitem(sys.modules, "pandera.backends", pandera_backends)
    monkeypatch.setitem(sys.modules, "pandera.backends.pandas", pandera_backends_pandas)
    monkeypatch.setitem(
        sys.modules,
        "pandera.backends.pandas.builtin_checks",
        pandera_builtin_checks,
    )
    monkeypatch.setitem(sys.modules, "pandera.api", pandera_api)
    monkeypatch.setitem(
        sys.modules,
        "pandera.api.function_dispatch",
        pandera_function_dispatch,
    )

    return typing_inspect_module, FakeDispatcher


def _install_fixed_fake_pandera_modules(monkeypatch) -> tuple[ModuleType, type]:
    typing_inspect_module = ModuleType("typing_inspect")
    typing_inspect_module.get_origin = typing.get_origin
    typing_inspect_module.get_args = typing.get_args

    pandera_module = ModuleType("pandera")
    pandera_backends = ModuleType("pandera.backends")
    pandera_backends_pandas = ModuleType("pandera.backends.pandas")
    pandera_builtin_checks = ModuleType("pandera.backends.pandas.builtin_checks")
    pandera_api = ModuleType("pandera.api")
    pandera_function_dispatch = ModuleType("pandera.api.function_dispatch")

    class FixedDispatcher:
        def __init__(self) -> None:
            self._function_registry: dict[object, object] = {}

        def register(self, fn: object) -> None:
            data_type = typing.get_type_hints(fn).get("value")
            if (
                typing.get_origin(data_type) is typing.get_origin(int | str)
                and typing.get_args(data_type) == typing.get_args(int | str)
            ):
                self._function_registry[int] = fn
                self._function_registry[str] = fn
            elif data_type is typing.Any:
                self._function_registry[typing.Any] = fn
            else:
                raise TypeError(f"Unsupported probe annotation: {data_type!r}")

        def __call__(self, *args: object, **kwargs: object) -> object:
            value = args[0]
            fn = self._function_registry.get(type(value))
            if fn is None:
                fn = self._function_registry.get(typing.Any)
            if fn is None:
                raise KeyError(type(value))
            return fn(*args, **kwargs)

    pandera_function_dispatch.Dispatcher = FixedDispatcher

    monkeypatch.setitem(sys.modules, "typing_inspect", typing_inspect_module)
    monkeypatch.setitem(sys.modules, "pandera", pandera_module)
    monkeypatch.setitem(sys.modules, "pandera.backends", pandera_backends)
    monkeypatch.setitem(sys.modules, "pandera.backends.pandas", pandera_backends_pandas)
    monkeypatch.setitem(
        sys.modules,
        "pandera.backends.pandas.builtin_checks",
        pandera_builtin_checks,
    )
    monkeypatch.setitem(sys.modules, "pandera.api", pandera_api)
    monkeypatch.setitem(
        sys.modules,
        "pandera.api.function_dispatch",
        pandera_function_dispatch,
    )

    return typing_inspect_module, FixedDispatcher


def test_validate_supported_pandera_runtime_is_noop_when_not_required(
    monkeypatch,
) -> None:
    module = importlib.reload(
        importlib.import_module("bioetl.infrastructure.compat.pandera_compat")
    )
    monkeypatch.setattr(
        module,
        "_requires_pandera_runtime_validation",
        _validation_disabled,
    )
    monkeypatch.setattr(module, "_RUNTIME_VALIDATED", False)

    assert module.validate_supported_pandera_runtime() is False


def test_pandera_runtime_support_policy_declares_fail_fast_contract() -> None:
    module = importlib.reload(
        importlib.import_module("bioetl.infrastructure.compat.pandera_compat")
    )
    policy = module.PANDERA_RUNTIME_SUPPORT_POLICY

    assert isinstance(policy, MappingProxyType)
    assert policy["owner"] == "infrastructure-compat"
    assert date.fromisoformat(policy["review_date"]) >= date(2026, 9, 30)
    assert policy["python_min"] == "3.14"
    assert policy["failure_policy"] == "fail_fast_no_runtime_monkeypatch"
    assert "supported Python/Pandera matrix" in policy["upstream_exit_condition"]


def test_validate_supported_pandera_runtime_raises_on_unhealthy_matrix(
    monkeypatch,
) -> None:
    module = importlib.reload(
        importlib.import_module("bioetl.infrastructure.compat.pandera_compat")
    )
    monkeypatch.setattr(
        module,
        "_requires_pandera_runtime_validation",
        _validation_enabled,
    )
    monkeypatch.setattr(module, "_RUNTIME_VALIDATED", False)

    typing_inspect_module, fake_dispatcher_cls = _install_fake_pandera_modules(
        monkeypatch
    )
    original_get_origin = typing_inspect_module.get_origin
    original_dispatcher_call = fake_dispatcher_cls.__call__

    with pytest.raises(
        module.UnsupportedPanderaRuntimeError,
        match="Unsupported Pandera runtime",
    ):
        module.validate_supported_pandera_runtime()

    assert module._RUNTIME_VALIDATED is False
    assert typing_inspect_module.get_origin is original_get_origin
    assert fake_dispatcher_cls.__call__ is original_dispatcher_call


def test_validate_supported_pandera_runtime_accepts_healthy_upstream_runtime(
    monkeypatch,
) -> None:
    module = importlib.reload(
        importlib.import_module("bioetl.infrastructure.compat.pandera_compat")
    )
    monkeypatch.setattr(
        module,
        "_requires_pandera_runtime_validation",
        _validation_enabled,
    )
    monkeypatch.setattr(module, "_RUNTIME_VALIDATED", False)

    typing_inspect_module, fixed_dispatcher_cls = _install_fixed_fake_pandera_modules(
        monkeypatch
    )
    original_get_origin = typing_inspect_module.get_origin
    original_dispatcher_call = fixed_dispatcher_cls.__call__

    assert module.validate_supported_pandera_runtime() is False
    assert module._RUNTIME_VALIDATED is True
    assert typing_inspect_module.get_origin is original_get_origin
    assert fixed_dispatcher_cls.__call__ is original_dispatcher_call


def test_importing_bioetl_version_does_not_trigger_runtime_validation(
    monkeypatch,
) -> None:
    typing_inspect_module, fake_dispatcher_cls = _install_fake_pandera_modules(
        monkeypatch
    )
    original_get_origin = typing_inspect_module.get_origin
    original_dispatcher_call = fake_dispatcher_cls.__call__

    bioetl_module = importlib.reload(importlib.import_module("bioetl"))

    assert bioetl_module.__version__
    assert typing_inspect_module.get_origin is original_get_origin
    assert fake_dispatcher_cls.__call__ is original_dispatcher_call


def test_runtime_bootstrap_package_does_not_validate_on_import(monkeypatch) -> None:
    """Runtime facade must not validate on import; it delegates explicitly."""
    calls: list[str] = []

    def validate_and_record() -> bool:
        return _record_and_return_false(calls)

    monkeypatch.setattr(
        "bioetl.composition.bootstrap.runtime.pipeline.validate_supported_pandera_runtime",
        validate_and_record,
    )

    sys.modules.pop("bioetl.composition.bootstrap.runtime", None)
    runtime_bootstrap = importlib.import_module("bioetl.composition.bootstrap.runtime")

    assert calls == []
    assert runtime_bootstrap.apply_runtime_compatibility_patches() is False
    assert calls == ["validated"]
