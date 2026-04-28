"""Internal converters for domain configuration objects.

Provides type conversion utilities used by config dataclasses during
__post_init__ for backward compatibility with string-based configuration.
"""

from __future__ import annotations

from bioetl.domain.medallion import GoldWriteMode, LoadingStrategy, SilverWriteMode

__all__ = [
    "convert_write_mode",
    "freeze_sequences",
    "resolve_loading_strategy",
]


def convert_write_mode[_WM: (SilverWriteMode, GoldWriteMode)](
    mode: _WM | str,
    enum_cls: type[_WM],
) -> _WM:
    """Convert a string or enum value to the target write-mode enum.

    Generic replacement for the former ``_convert_silver_write_mode``
    and ``_convert_gold_write_mode`` helpers.

    Args:
        mode: Write mode value (string or enum instance).
        enum_cls: Target enum class (SilverWriteMode or GoldWriteMode).

    Returns:
        Resolved enum value.
    """
    if isinstance(mode, enum_cls):
        return mode
    return enum_cls.from_string(mode)


def resolve_loading_strategy(
    loading_strategy: LoadingStrategy | str | None,
) -> LoadingStrategy | None:
    """Resolve loading_strategy from explicit value.

    Converts string values to enum, passes through enum values and None.

    Args:
        loading_strategy: Explicit strategy value, string, or None

    Returns:
        Resolved LoadingStrategy enum value or None
    """
    if loading_strategy is None:
        return None
    if isinstance(loading_strategy, LoadingStrategy):
        return loading_strategy
    return LoadingStrategy.from_string(loading_strategy)


def freeze_sequences(instance: object, fields: tuple[str, ...]) -> None:
    """Convert list fields to tuples on a frozen dataclass instance.

    Must be called inside ``__post_init__`` of frozen dataclasses.
    Uses ``object.__setattr__`` to bypass the frozen guard.

    Args:
        instance: The frozen dataclass instance being initialised.
        fields: Attribute names whose values should be coerced to tuples.
    """
    for attr in fields:
        val = getattr(instance, attr)
        if isinstance(val, list):
            object.__setattr__(instance, attr, tuple(val))
