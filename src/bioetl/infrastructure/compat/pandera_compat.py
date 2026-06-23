"""Explicit Pandera runtime support validation for Python 3.14 bootstrap."""

from __future__ import annotations

import sys
import typing
from collections.abc import Mapping
from types import MappingProxyType

_RUNTIME_VALIDATED = False
_PANDERA_RUNTIME_VALIDATION_PYTHON_MIN = (3, 14)
PANDERA_RUNTIME_SUPPORT_POLICY: Mapping[str, str] = MappingProxyType(
    {
        "owner": "infrastructure-compat",
        "review_date": "2026-09-30",
        "python_min": "3.14",
        "failure_policy": "fail_fast_no_runtime_monkeypatch",
        "upstream_exit_condition": (
            "Remove this validation shim after the supported Python/Pandera "
            "matrix proves Pandera dispatcher typing works on Python 3.14+ "
            "without fallback monkeypatching."
        ),
    }
)


class UnsupportedPanderaRuntimeError(RuntimeError):
    """Raised when the supported Python/Pandera matrix still needs patching."""


def _requires_pandera_runtime_validation() -> bool:
    """Return whether the current interpreter needs Pandera runtime validation."""
    return sys.version_info >= _PANDERA_RUNTIME_VALIDATION_PYTHON_MIN


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


def _dispatcher_probe_union_handler(value: int | str) -> object:
    """Return probe input unchanged so dispatcher sanity checks stay deterministic."""
    return value


def _dispatcher_probe_any_handler(
    value: typing.Any,  # Any: Pandera dispatcher catch-all probe requires typing.Any.
) -> object:
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
        if registry.get(typing.Any) is not _dispatcher_probe_any_handler:  # Any: Pandera catch-all key.
            return True
        if dispatcher(1) != 1 or dispatcher("union") != "union":
            return True
        if _find_any_fallback(registry) is None:
            return True
        return dispatcher(1.5) != 1.5
    except (AttributeError, KeyError, TypeError, ValueError, RuntimeError):
        return True


def _unsupported_runtime_message(
    *,
    origin_needs_patch: bool,
    dispatcher_needs_patch: bool,
) -> str:
    reasons: list[str] = []
    if origin_needs_patch:
        reasons.append("typing_inspect.get_origin lacks Python 3.14 union support")
    if dispatcher_needs_patch:
        reasons.append(
            "Pandera Dispatcher still requires union/catch-all fallback patching"
        )
    reason_text = "; ".join(reasons) if reasons else "unsupported Pandera runtime"
    return (
        "Unsupported Pandera runtime for Python 3.14+ detected: "
        f"{reason_text}. "
        "BioETL no longer applies runtime monkeypatches for this matrix; "
        "upgrade to a supported Pandera/typing_inspect combination before "
        "bootstrapping pipelines."
    )


def validate_supported_pandera_runtime() -> bool:
    """Validate Python 3.14+ Pandera runtime support without monkeypatching."""
    global _RUNTIME_VALIDATED

    if _RUNTIME_VALIDATED or not _requires_pandera_runtime_validation():
        return False

    try:
        import pandera.backends.pandas.builtin_checks  # noqa: F401
        import typing_inspect  # type: ignore[import-untyped]
        from pandera.api.function_dispatch import Dispatcher
    except (ImportError, AttributeError, TypeError, ValueError, RuntimeError):
        return False

    origin_needs_patch = _typing_inspect_origin_needs_patch(typing_inspect)
    dispatcher_needs_patch = _pandera_dispatcher_needs_patch(Dispatcher)
    if origin_needs_patch or dispatcher_needs_patch:
        raise UnsupportedPanderaRuntimeError(
            _unsupported_runtime_message(
                origin_needs_patch=origin_needs_patch,
                dispatcher_needs_patch=dispatcher_needs_patch,
            )
        )

    _RUNTIME_VALIDATED = True
    return False


__all__ = [
    "PANDERA_RUNTIME_SUPPORT_POLICY",
    "UnsupportedPanderaRuntimeError",
    "validate_supported_pandera_runtime",
]
