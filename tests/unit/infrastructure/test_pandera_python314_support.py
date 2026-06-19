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


def _compat_disabled() -> bool:
    return False


def _compat_enabled() -> bool:
    return True


def _record_and_return_false(calls: list[str]) -> bool:
    calls.append("applied")
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


def test_apply_pandera_typing_compat_is_noop_when_not_required(
    monkeypatch,
) -> None:
    module = importlib.reload(
        importlib.import_module("bioetl.infrastructure.compat.pandera_compat")
    )
    monkeypatch.setattr(module, "_requires_pandera_typing_compat", _compat_disabled)
    monkeypatch.setattr(module, "_PATCH_APPLIED", False)

    assert module.apply_pandera_typing_compat_if_needed() is False


def test_pandera_typing_compat_declares_sunset_policy() -> None:
    module = importlib.reload(
        importlib.import_module("bioetl.infrastructure.compat.pandera_compat")
    )
    policy = module.PANDERA_TYPING_COMPAT_SUNSET_POLICY

    assert isinstance(policy, MappingProxyType)
    assert policy["owner"] == "infrastructure-compat"
    assert date.fromisoformat(policy["review_date"]) >= date(2026, 9, 30)
    assert policy["python_min"] == "3.14"
    assert "supported Python/Pandera matrix" in policy["upstream_exit_condition"]
    assert "Dispatcher.__call__" in policy["upstream_exit_condition"]


def test_apply_pandera_typing_compat_patches_dispatcher_when_forced(
    monkeypatch,
) -> None:
    module = importlib.reload(
        importlib.import_module("bioetl.infrastructure.compat.pandera_compat")
    )
    monkeypatch.setattr(module, "_requires_pandera_typing_compat", _compat_enabled)
    monkeypatch.setattr(module, "_PATCH_APPLIED", False)

    typing_inspect_module, fake_dispatcher_cls = _install_fake_pandera_modules(
        monkeypatch
    )
    original_get_origin = typing_inspect_module.get_origin
    original_dispatcher_call = fake_dispatcher_cls.__call__

    assert module.apply_pandera_typing_compat_if_needed() is True
    assert module.apply_pandera_typing_compat_if_needed() is False
    assert typing_inspect_module.get_origin is not original_get_origin
    assert fake_dispatcher_cls.__call__ is not original_dispatcher_call
    assert typing_inspect_module.get_origin(int | str) == typing.get_origin(int | str)

    class FakeUnionType:
        __union_args__ = (int,)

    dispatcher = fake_dispatcher_cls()
    dispatcher._function_registry = {
        FakeUnionType: _format_union_value,
    }
    assert dispatcher(1) == "union:1"


def test_apply_pandera_typing_compat_skips_healthy_upstream_runtime(
    monkeypatch,
) -> None:
    module = importlib.reload(
        importlib.import_module("bioetl.infrastructure.compat.pandera_compat")
    )
    monkeypatch.setattr(module, "_requires_pandera_typing_compat", _compat_enabled)
    monkeypatch.setattr(module, "_PATCH_APPLIED", False)

    typing_inspect_module, fixed_dispatcher_cls = _install_fixed_fake_pandera_modules(
        monkeypatch
    )
    original_get_origin = typing_inspect_module.get_origin
    original_dispatcher_call = fixed_dispatcher_cls.__call__

    assert module.apply_pandera_typing_compat_if_needed() is False
    assert module._PATCH_APPLIED is False
    assert typing_inspect_module.get_origin is original_get_origin
    assert fixed_dispatcher_cls.__call__ is original_dispatcher_call


def test_importing_bioetl_version_does_not_trigger_compat(monkeypatch) -> None:
    typing_inspect_module, fake_dispatcher_cls = _install_fake_pandera_modules(
        monkeypatch
    )
    original_get_origin = typing_inspect_module.get_origin
    original_dispatcher_call = fake_dispatcher_cls.__call__

    bioetl_module = importlib.reload(importlib.import_module("bioetl"))

    assert bioetl_module.__version__
    assert typing_inspect_module.get_origin is original_get_origin
    assert fake_dispatcher_cls.__call__ is original_dispatcher_call


def test_runtime_bootstrap_package_applies_compat_on_import(monkeypatch) -> None:
    """Runtime facade must not patch on import; it delegates via owner module."""
    calls: list[str] = []

    def apply_compat_and_record() -> bool:
        return _record_and_return_false(calls)

    # Patch the owner module binding: it imports the helper once at
    # module load, so patching pandera_compat alone is not enough when the
    # owner module was already imported earlier in the pytest session.
    monkeypatch.setattr(
        "bioetl.composition.bootstrap.runtime.pipeline.apply_pandera_typing_compat_if_needed",
        apply_compat_and_record,
    )

    sys.modules.pop("bioetl.composition.bootstrap.runtime", None)
    runtime_bootstrap = importlib.import_module("bioetl.composition.bootstrap.runtime")

    assert calls == []

    assert runtime_bootstrap.apply_runtime_compatibility_patches() is False
    assert calls == ["applied"]


def _format_union_value(value: object) -> str:
    return f"union:{value}"
