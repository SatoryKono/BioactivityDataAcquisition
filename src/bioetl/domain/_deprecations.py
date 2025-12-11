"""Centralized deprecation management for domain layer.

This module provides utilities for emitting consistent deprecation warnings
across the domain layer.

Note: All deprecated aliases from v2.x have been removed in v3.0.
This module is kept for any future deprecation management needs.
"""

from __future__ import annotations

import warnings
from typing import Any, NamedTuple

__all__ = [
    "REMOVAL_VERSION",
    "DEPRECATED_ALIASES",
    "DeprecatedAlias",
    "emit_deprecation_warning",
]

REMOVAL_VERSION: str = "4.0"
"""Version in which future deprecated aliases will be removed."""


class DeprecatedAlias(NamedTuple):
    """Metadata for a deprecated name.

    Attributes:
        new_name: The recommended replacement name.
        new_module: The module where the replacement is defined.
        category: Type of deprecation (type_alias, class_alias, function).
        message: Optional custom deprecation message.
    """

    new_name: str
    new_module: str
    category: str = "type_alias"
    message: str | None = None


# Empty registry - all v2.x deprecated aliases have been removed in v3.0
DEPRECATED_ALIASES: dict[str, DeprecatedAlias] = {}


def emit_deprecation_warning(
    old_name: str,
    *,
    new_name: str | None = None,
    removal_version: str = REMOVAL_VERSION,
    stacklevel: int = 3,
) -> None:
    """Emit a deprecation warning for a deprecated name.

    Args:
        old_name: The deprecated name being accessed.
        new_name: Override for the replacement name.
        removal_version: Version when the name will be removed.
        stacklevel: Stack level for the warning (default 3 for __getattr__).
    """
    if old_name in DEPRECATED_ALIASES:
        alias = DEPRECATED_ALIASES[old_name]
        message = (
            alias.message or f"{old_name} is deprecated, use {alias.new_name} instead."
        )
    else:
        message = f"{old_name} is deprecated"
        if new_name:
            message += f", use {new_name} instead"

    full_message = f"{message} Will be removed in v{removal_version}."
    warnings.warn(full_message, DeprecationWarning, stacklevel=stacklevel)


def resolve_deprecated_type(name: str) -> Any:
    """Resolve a deprecated type alias name to its actual type.

    Returns the appropriate type/class for backward compatibility
    when a deprecated name is accessed via __getattr__.

    Args:
        name: The deprecated name to resolve.

    Returns:
        The resolved type, class, or raises AttributeError if unknown.

    Raises:
        AttributeError: If the name is not a known deprecated alias.
    """
    if name not in DEPRECATED_ALIASES:
        raise AttributeError(f"Unknown deprecated alias: {name!r}")

    # All v2.x aliases have been removed - this is kept for future use
    raise AttributeError(f"Cannot resolve deprecated alias: {name!r}")


def get_deprecated_names_for_module(module_name: str) -> set[str]:
    """Get deprecated names that should be handled by a specific module.

    Args:
        module_name: The module path (e.g., 'bioetl.domain.types').

    Returns:
        Set of deprecated names that are originally from or re-exported by this module.
    """
    # All v2.x module mappings have been removed
    return set()
