"""Explicit Pandera compatibility seam for Python 3.14 runtime bootstrap."""

from __future__ import annotations

import sys
import typing

_PATCH_APPLIED = False


def _requires_pandera_typing_compat() -> bool:
    """Return whether the current interpreter needs the Pandera typing patch."""
    return sys.version_info >= (3, 14)


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

    setattr(dispatcher_cls, "__call__", _dispatcher_call_with_any_fallback)


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

    _patch_typing_inspect_get_origin(typing_inspect)
    _patch_dispatcher_call(Dispatcher, typing_inspect)
    _PATCH_APPLIED = True
    return True


__all__ = ["apply_pandera_typing_compat_if_needed"]
