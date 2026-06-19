"""Explicit Pandera compatibility seam for Python 3.14 runtime bootstrap."""

from __future__ import annotations

import sys
import typing
from collections.abc import Mapping
from types import MappingProxyType

_PATCH_APPLIED = False
_PANDERA_TYPING_COMPAT_PYTHON_MIN = (3, 14)
PANDERA_TYPING_COMPAT_SUNSET_POLICY: Mapping[str, str] = MappingProxyType(
    {
        "owner": "infrastructure-compat",
        "review_date": "2026-09-30",
        "python_min": "3.14",
        "upstream_exit_condition": (
            "Remove this shim after the supported Python/Pandera matrix proves "
            "Pandera dispatcher typing works on Python 3.14+ without the "
            "typing_inspect.get_origin and Dispatcher.__call__ patches."
        ),
    }
)


def _requires_pandera_typing_compat() -> bool:
    """Return whether the current interpreter needs the Pandera typing patch."""
    return sys.version_info >= _PANDERA_TYPING_COMPAT_PYTHON_MIN


def _patch_typing_inspect_get_origin(
    typing_inspect_module: typing.Any,  # Any: imported module is runtime-defined
) -> None:
    """Patch typing_inspect.get_origin to honor Python 3.10+ union syntax."""
    original_get_origin = typing_inspect_module.get_origin

    def _get_origin_with_union_fix(
        tp: typing.Any,  # Any: multipledispatch requires erased types
    ) -> typing.Any:  # Any: multipledispatch requires erased types
        origin = original_get_origin(tp)
        if origin is None:
            return typing.get_origin(tp)
        return origin

    typing_inspect_module.get_origin = _get_origin_with_union_fix


def _typing_inspect_origin_needs_patch(
    typing_inspect_module: typing.Any,  # Any: imported module is runtime-defined
) -> bool:
    """Return whether typing_inspect still misses ``types.UnionType`` origins."""
    try:
        return typing_inspect_module.get_origin(int | str) is None and (
            typing.get_origin(int | str) is not None
        )
    except (AttributeError, TypeError, ValueError):
        return True


def _find_fn_by_subclass_or_union(
    registry: dict[
        typing.Any,  # Any: multipledispatch requires erased types
        typing.Any,  # Any: multipledispatch requires erased types
    ],
    input_data_type: type,
    typing_inspect_module: typing.Any,  # Any: imported module is runtime-defined
) -> typing.Any:  # Any: multipledispatch requires erased types
    """Search a dispatcher registry via subclass or union members."""
    for registered_type, registered_fn in registry.items():
        if (
            registered_type
            is typing.Any  # Any: dispatcher registry may explicitly register a catch-all Any fallback.
        ):
            continue
        if isinstance(registered_type, type) and issubclass(
            input_data_type, registered_type
        ):
            return registered_fn
        union_args = typing_inspect_module.get_args(registered_type)
        if union_args and any(
            isinstance(arg, type) and issubclass(input_data_type, arg)
            for arg in union_args
        ):
            return registered_fn
    return None


def _find_any_fallback(
    registry: dict[
        typing.Any,  # Any: multipledispatch requires erased types
        typing.Any,  # Any: multipledispatch requires erased types
    ],
) -> typing.Any:  # Any: multipledispatch requires erased types
    """Return the Any-registered dispatcher function when present."""
    if (
        typing.Any  # Any: compat layer must probe the dispatcher catch-all registration key.
        in registry  # Any: multipledispatch stores the catch-all fallback under typing.Any.
    ):
        return registry[
            typing.Any  # Any: compat lookup must preserve the catch-all dispatcher fallback.
        ]
    return None


def _patch_dispatcher_call(
    dispatcher_cls: type,
    typing_inspect_module: typing.Any,  # Any: imported module is runtime-defined
) -> None:
    """Patch Pandera dispatcher lookup to support subclass and union fallback."""
    original_dispatcher_call = dispatcher_cls.__call__

    def _resolve_registered_dispatch_fn(
        registry: dict[
            typing.Any, typing.Any  # Any: multipledispatch requires erased types
        ],  # Any: multipledispatch requires erased types
        input_data_type: type,
    ) -> typing.Any:  # Any: multipledispatch requires erased types
        fn = registry.get(input_data_type)
        if fn is not None:
            return fn
        union_match = _find_fn_by_subclass_or_union(
            registry,
            input_data_type,
            typing_inspect_module,
        )
        if union_match is not None:
            return union_match
        return _find_any_fallback(registry)

    def _dispatcher_call_with_any_fallback(
        self: typing.Any,  # Any: multipledispatch requires erased types
        *args: typing.Any,  # Any: multipledispatch requires erased types
        **kwargs: typing.Any,  # Any: multipledispatch requires erased types
    ) -> typing.Any:  # Any: multipledispatch requires erased types
        input_data_type = type(args[0])
        fn = _resolve_registered_dispatch_fn(self._function_registry, input_data_type)
        if fn is None:
            return original_dispatcher_call(self, *args, **kwargs)
        return fn(*args, **kwargs)

    dispatcher_cls.__call__ = _dispatcher_call_with_any_fallback  # type: ignore[method-assign]


def _dispatcher_probe_union_handler(value: int | str) -> object:
    """Return probe input unchanged so dispatcher sanity checks stay deterministic."""
    return value


def _dispatcher_probe_any_handler(
    value: typing.Any,
) -> object:  # Any: typing.Any is used for Pandera dispatcher type system compatibility
    """Return probe input unchanged so fallback dispatch can be verified."""
    return value


def _pandera_dispatcher_needs_patch(dispatcher_cls: type) -> bool:
    """Return whether Pandera's dispatcher still needs union/Any fallback patching."""
    try:
        dispatcher = dispatcher_cls()
        dispatcher.register(_dispatcher_probe_union_handler)
        dispatcher.register(_dispatcher_probe_any_handler)
        registry = dispatcher._function_registry
        if not isinstance(registry, dict):
            return True
        if registry.get(int) is not _dispatcher_probe_union_handler:
            return True
        if registry.get(str) is not _dispatcher_probe_union_handler:
            return True
        # Any: typing.Any is used for Pandera dispatcher type system compatibility
        if registry.get(typing.Any) is not _dispatcher_probe_any_handler:
            return True
        return not (
            dispatcher(1) == 1
            and dispatcher("union") == "union"
            and dispatcher(1.5) == 1.5
        )
    except (AttributeError, KeyError, TypeError, ValueError, RuntimeError):
        return True


def apply_pandera_typing_compat_if_needed() -> bool:
    """Apply the Python 3.14 Pandera typing compat patch once when required."""
    global _PATCH_APPLIED

    if _PATCH_APPLIED or not _requires_pandera_typing_compat():
        return False

    try:
        import pandera.backends.pandas.builtin_checks  # noqa: F401
        import typing_inspect  # type: ignore[import-untyped]
        from pandera.api.function_dispatch import Dispatcher
    except (ImportError, AttributeError, TypeError, ValueError, RuntimeError):
        return False

    origin_needs_patch = _typing_inspect_origin_needs_patch(typing_inspect)
    dispatcher_needs_patch = _pandera_dispatcher_needs_patch(Dispatcher)
    if not origin_needs_patch and not dispatcher_needs_patch:
        return False

    if origin_needs_patch:
        _patch_typing_inspect_get_origin(typing_inspect)
    if dispatcher_needs_patch:
        _patch_dispatcher_call(Dispatcher, typing_inspect)
    _PATCH_APPLIED = True
    return True


__all__ = [
    "PANDERA_TYPING_COMPAT_SUNSET_POLICY",
    "apply_pandera_typing_compat_if_needed",
]
