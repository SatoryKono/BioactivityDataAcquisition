"""BioETL: Bioactivity data acquisition and processing pipeline."""

from __future__ import annotations

from importlib import import_module
from types import ModuleType

__version__ = "6.1.0"

# Project-wide monkeypatch for Pandera compatibility with Python 3.14.
# Pandera uses typing_inspect.get_origin which returns None for A | B unions on Python 3.10+.
# This prevents pandas-specific checks from being registered correctly.
try:
    import typing

    import typing_inspect  # type: ignore[import-untyped]

    # Fix typing_inspect.get_origin BEFORE importing pandera backends
    _orig_get_origin = typing_inspect.get_origin

    def _get_origin_with_union_fix(
        tp: typing.Any,  # Any: multipledispatch requires erased types
    ) -> typing.Any:  # Any: multipledispatch requires erased types
        origin = _orig_get_origin(tp)
        if origin is None:
            # Fallback to typing.get_origin for Python 3.10+ unions (A | B)
            return typing.get_origin(tp)
        return origin

    typing_inspect.get_origin = _get_origin_with_union_fix

    # Ensure pandas-specific check implementations are registered.
    import pandera.backends.pandas.builtin_checks  # noqa: F401
    from pandera.api.function_dispatch import Dispatcher

    _orig_dispatcher_call = Dispatcher.__call__

    def _find_fn_by_subclass_or_union(
        registry: dict[
            typing.Any, typing.Any  # Any: multipledispatch requires erased types
        ],  # Any: multipledispatch requires erased types
        input_data_type: type,
    ) -> typing.Any:  # Any: multipledispatch requires erased types
        """Search registry for a function matching input_data_type via subclass or union args.

        Returns:
            Registered function if a matching type or union member is found, None otherwise.
        """
        for registered_type, registered_fn in registry.items():
            if (
                registered_type
                is typing.Any  # Any: multipledispatch requires erased types
            ):  # Any: multipledispatch requires erased types
                continue
            if isinstance(registered_type, type) and issubclass(
                input_data_type, registered_type
            ):
                return registered_fn
            union_args = typing_inspect.get_args(registered_type)
            if union_args and any(
                isinstance(arg, type) and issubclass(input_data_type, arg)
                for arg in union_args
            ):
                return registered_fn
        return None

    def _dispatcher_call_with_any_fallback(
        self: typing.Any,  # Any: multipledispatch requires erased types
        *args: typing.Any,  # Any: multipledispatch requires erased types
        **kwargs: typing.Any,  # Any: multipledispatch requires erased types
    ) -> typing.Any:  # Any: multipledispatch requires erased types
        input_data_type = type(args[0])
        fn = self._function_registry.get(input_data_type)

        # Python 3.14 can leave Union-annotated registrations as single keys
        # (e.g., pandas.Series | pandas.DataFrame) in Pandera's registry.
        if fn is None:
            fn = _find_fn_by_subclass_or_union(self._function_registry, input_data_type)

        if (
            fn is None
            and typing.Any  # Any: multipledispatch requires erased types
            in self._function_registry  # Any: multipledispatch requires erased types
        ):  # Any: multipledispatch requires erased types
            fn = self._function_registry[
                typing.Any  # Any: multipledispatch requires erased types
            ]  # Any: multipledispatch requires erased types
        if fn is None:
            return _orig_dispatcher_call(self, *args, **kwargs)  # type: ignore[no-untyped-call]
        return fn(*args, **kwargs)

    Dispatcher.__call__ = _dispatcher_call_with_any_fallback  # type: ignore[method-assign]
except (ImportError, AttributeError, TypeError, ValueError, RuntimeError):
    # Fail silently to avoid breaking the entire project if Pandera/Pandas are not present
    pass

_PACKAGE_EXPORTS: dict[str, str] = {
    "application": "bioetl.application",
    "composition": "bioetl.composition",
    "domain": "bioetl.domain",
    "infrastructure": "bioetl.infrastructure",
    "interfaces": "bioetl.interfaces",
}

__all__ = ["__version__", *_PACKAGE_EXPORTS]


def __getattr__(name: str) -> ModuleType:
    """Lazily expose top-level package namespaces for patch/import stability."""
    try:
        module_name = _PACKAGE_EXPORTS[name]
    except KeyError as exc:  # pragma: no cover - standard attribute path
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc

    module = import_module(module_name)
    globals()[name] = module
    return module


def __dir__() -> list[str]:
    """Return stable top-level exports for shell/help introspection."""
    return sorted(set(globals()) | set(__all__))
