from __future__ import annotations

import importlib
import sys
import typing
from types import ModuleType


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


def test_apply_pandera_typing_compat_is_noop_when_not_required(
    monkeypatch,
) -> None:
    module = importlib.reload(
        importlib.import_module("bioetl.infrastructure.compat.pandera_compat")
    )
    monkeypatch.setattr(module, "_requires_pandera_typing_compat", _compat_disabled)
    monkeypatch.setattr(module, "_PATCH_APPLIED", False)

    assert module.apply_pandera_typing_compat_if_needed() is False


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


def test_bootstrap_lazy_exports_apply_compat_before_import(monkeypatch) -> None:
    compat_module = importlib.reload(
        importlib.import_module("bioetl.infrastructure.compat.pandera_compat")
    )
    bootstrap_module = importlib.reload(
        importlib.import_module("bioetl.composition.bootstrap")
    )

    calls: list[str] = []

    def apply_compat_and_record() -> bool:
        return _record_and_return_false(calls)

    monkeypatch.setattr(
        compat_module,
        "apply_pandera_typing_compat_if_needed",
        apply_compat_and_record,
    )

    assert bootstrap_module.load_pipeline_config
    assert calls == ["applied"]


def _format_union_value(value: object) -> str:
    return f"union:{value}"
