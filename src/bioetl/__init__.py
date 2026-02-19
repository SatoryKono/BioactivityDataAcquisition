"""BioETL: Bioactivity data acquisition and processing pipeline."""

from __future__ import annotations

__version__ = "6.0.0"

# Project-wide monkeypatch for Pandera compatibility with Python 3.14.
# Pandera uses typing_inspect.get_origin which returns None for A | B unions on Python 3.10+.
# This prevents pandas-specific checks from being registered correctly.
try:
    import typing
    from typing import Any

    import typing_inspect  # type: ignore[import-untyped, import-not-found]

    # Fix typing_inspect.get_origin BEFORE importing pandera backends
    _orig_get_origin = typing_inspect.get_origin  # type: ignore[import-untyped]

    def _get_origin_with_union_fix(tp: typing.Any) -> typing.Any:
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

    def _find_matching_function(self: Any, input_data_type: type) -> typing.Any | None:  # type: ignore[misc]
        """Find matching function in registry supporting Union types."""
        # Check explicit match first (O(1))
        fn = self._function_registry.get(input_data_type)
        if fn is not None:
            return fn

        # Scan registry for compatible types (O(N))
        # Python 3.14 can leave Union-annotated registrations as single keys
        # (e.g., pandas.Series | pandas.DataFrame) in Pandera's registry.
        for registered_type, registered_fn in self._function_registry.items():
            if registered_type is typing.Any:
                continue

            # Check direct subclass relationship
            if isinstance(registered_type, type) and issubclass(
                input_data_type, registered_type
            ):
                return registered_fn

            # Check Union arguments (e.g. Series | DataFrame)
            union_args = typing_inspect.get_args(registered_type)  # type: ignore[import-untyped]
            if union_args and any(
                isinstance(arg, type) and issubclass(input_data_type, arg)
                for arg in union_args
            ):
                return registered_fn

        return None

    def _dispatcher_call_with_any_fallback(
        self: Any, *args: Any, **kwargs: Any
    ) -> typing.Any:  # type: ignore[misc]
        input_data_type = type(args[0])
        fn = _find_matching_function(self, input_data_type)

        if fn is None and typing.Any in self._function_registry:
            fn = self._function_registry[typing.Any]

        if fn is None:
            return _orig_dispatcher_call(self, *args, **kwargs)
        return fn(*args, **kwargs)  # type: ignore[no-any-return]

    Dispatcher.__call__ = _dispatcher_call_with_any_fallback  # type: ignore[method-assign]
except Exception:
    # Fail silently to avoid breaking the entire project if Pandera/Pandas are not present
    pass
