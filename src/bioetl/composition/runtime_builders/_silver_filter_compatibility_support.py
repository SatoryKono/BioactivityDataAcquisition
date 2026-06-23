"""Silver filter compatibility helpers for runtime builders."""

from __future__ import annotations

from bioetl.infrastructure.config.silver_filter_migration import (
    build_silver_filter_compatibility_snapshot,
    resolve_silver_filter_compatibility_mode,
)


def current_silver_filter_compatibility_mode() -> str:
    """Return the active Silver filter compatibility mode."""
    return resolve_silver_filter_compatibility_mode()


def current_silver_filter_compatibility_snapshot() -> dict[str, object]:
    """Return the active Silver filter compatibility snapshot."""
    return build_silver_filter_compatibility_snapshot()


def add_silver_filter_compatibility_defaults(payload: dict[str, object]) -> None:
    """Add Silver compatibility defaults to a mutable runtime payload."""
    payload.setdefault(
        "silver_filter_compatibility_mode",
        current_silver_filter_compatibility_mode(),
    )
    payload.setdefault(
        "silver_filter_compatibility",
        current_silver_filter_compatibility_snapshot(),
    )


__all__ = [
    "add_silver_filter_compatibility_defaults",
    "current_silver_filter_compatibility_mode",
    "current_silver_filter_compatibility_snapshot",
]
