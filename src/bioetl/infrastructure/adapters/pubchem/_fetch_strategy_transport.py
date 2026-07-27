"""Transport bag resolution for PubChem fetch strategies facade."""

from __future__ import annotations

__all__ = ["resolve_transport_bag"]

_TRANSPORT_KEYS = ("logger", "rate_limiter", "circuit_breaker", "run_in_executor")


def resolve_transport_bag(
    transport: dict[str, object] | None,
    legacy: dict[str, object],
) -> dict[str, object]:
    """Merge transport dict with transitional kwargs; reject unknown keys."""
    resolved = dict(transport or {})
    for key in _TRANSPORT_KEYS:
        value = legacy.pop(key, None)
        if value is not None:
            resolved[key] = value
    if legacy:
        raise TypeError(
            "PubChemFetchStrategies() got unexpected keyword argument(s): "
            + ", ".join(sorted(str(k) for k in legacy))
        )
    return resolved
