"""Centralized deprecation management for domain layer.

This module provides a unified registry of deprecated names and utilities
for emitting consistent deprecation warnings across the domain layer.

Removal Schedule
----------------
All deprecated aliases listed here are scheduled for removal in v3.0.

Usage in Modules
----------------
Modules should import and use this registry for __getattr__ implementations::

    from bioetl.domain._deprecations import (
        DEPRECATED_ALIASES,
        emit_deprecation_warning,
        resolve_deprecated_type,
    )

    def __getattr__(name: str) -> Any:
        if name in DEPRECATED_ALIASES:
            emit_deprecation_warning(name)
            return resolve_deprecated_type(name)
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

Checking for Usage
------------------
Use ``scripts/check_deprecations.py`` to scan the codebase for usage of
deprecated imports and generate a migration report.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, NamedTuple
import warnings

if TYPE_CHECKING:
    pass

# =============================================================================
# Constants
# =============================================================================

REMOVAL_VERSION: str = "3.0"
"""Version in which deprecated aliases will be removed."""


# =============================================================================
# Deprecated Alias Registry
# =============================================================================


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


# Central registry mapping deprecated names to their metadata.
# Format: old_name -> DeprecatedAlias(new_name, new_module, category, message)
DEPRECATED_ALIASES: dict[str, DeprecatedAlias] = {
    # -------------------------------------------------------------------------
    # Type Aliases (deprecated in domain/types.py, domain/ports/)
    # -------------------------------------------------------------------------
    "RawRecordDict": DeprecatedAlias(
        new_name="Mapping[str, Any]",
        new_module="typing",
        category="type_alias",
        message="RawRecordDict is deprecated. Use Mapping[str, Any] directly.",
    ),
    "RawRecordBatch": DeprecatedAlias(
        new_name="RecordBatch",
        new_module="bioetl.domain.data",
        category="type_alias",
        message=(
            "RawRecordBatch is deprecated. " "Use RecordBatch from bioetl.domain.data."
        ),
    ),
    "RawRecordList": DeprecatedAlias(
        new_name="RecordBatch",
        new_module="bioetl.domain.data",
        category="type_alias",
        message=(
            "RawRecordList is deprecated. " "Use RecordBatch from bioetl.domain.data."
        ),
    ),
    "RawPayload": DeprecatedAlias(
        new_name="ApiPayload",
        new_module="bioetl.domain.types",
        category="type_alias",
        message="RawPayload is deprecated. Use ApiPayload instead.",
    ),
    "RawRecord": DeprecatedAlias(
        new_name="Mapping[str, Any]",
        new_module="typing",
        category="type_alias",
        message="RawRecord is deprecated. Use Mapping[str, Any] or Record protocol.",
    ),
    # RecordBatch re-export from types.py (moved to data.py)
    "RecordBatch": DeprecatedAlias(
        new_name="RecordBatch",
        new_module="bioetl.domain.data",
        category="type_alias",
        message=(
            "RecordBatch has moved to bioetl.domain.data. "
            "Import from there: from bioetl.domain.data import RecordBatch"
        ),
    ),
    # -------------------------------------------------------------------------
    # Class Aliases (deprecated in domain/record_source.py)
    # -------------------------------------------------------------------------
    "SourceRecord": DeprecatedAlias(
        new_name="SourceRecordModel",
        new_module="bioetl.domain.record_source",
        category="class_alias",
        message="SourceRecord is deprecated, use SourceRecordModel instead.",
    ),
    "RecordSource": DeprecatedAlias(
        new_name="RecordSourceABC",
        new_module="bioetl.domain.record_source",
        category="class_alias",
        message="RecordSource is deprecated. Use RecordSourceABC directly.",
    ),
}


# =============================================================================
# Utility Functions
# =============================================================================


def emit_deprecation_warning(
    old_name: str,
    *,
    new_name: str | None = None,
    removal_version: str = REMOVAL_VERSION,
    stacklevel: int = 3,
) -> None:
    """Emit a deprecation warning for a deprecated name.

    Looks up the deprecated name in DEPRECATED_ALIASES to construct the
    warning message. Falls back to a generic message if not found.

    Args:
        old_name: The deprecated name being accessed.
        new_name: Override for the replacement name (uses registry if None).
        removal_version: Version when the name will be removed.
        stacklevel: Stack level for the warning (default 3 for __getattr__).

    Example:
        >>> emit_deprecation_warning("RawRecordDict")
        # Emits: DeprecationWarning: RawRecordDict is deprecated...
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

    full_message = (
        f"{message} "
        f"Will be removed in v{removal_version}. "
        f"See migration guide in bioetl.domain.types module docstring."
    )

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

    Example:
        >>> resolve_deprecated_type("RawRecordBatch")
        <class 'bioetl.domain.data.RecordBatch'>
    """
    if name not in DEPRECATED_ALIASES:
        raise AttributeError(f"Unknown deprecated alias: {name!r}")

    alias = DEPRECATED_ALIASES[name]

    # Handle type aliases that map to built-in types
    if alias.new_name == "Mapping[str, Any]":
        return dict[str, Any]

    # Handle ApiPayload
    if name == "RawPayload" or alias.new_name == "ApiPayload":
        from bioetl.domain.types import ApiPayload

        return ApiPayload

    # Handle RecordBatch variants
    if alias.new_name == "RecordBatch":
        from bioetl.domain.data import RecordBatch

        return RecordBatch

    # Handle SourceRecordModel
    if alias.new_name == "SourceRecordModel":
        from bioetl.domain.record_source import SourceRecordModel

        return SourceRecordModel

    # Handle RecordSourceABC
    if alias.new_name == "RecordSourceABC":
        from bioetl.domain.record_source import RecordSourceABC

        return RecordSourceABC

    # Fallback for unknown types
    raise AttributeError(f"Cannot resolve deprecated alias: {name!r}")


def get_deprecated_names_for_module(module_name: str) -> set[str]:
    """Get deprecated names that should be handled by a specific module.

    Args:
        module_name: The module path (e.g., 'bioetl.domain.types').

    Returns:
        Set of deprecated names that are originally from or re-exported by this module.
    """
    module_to_names: dict[str, set[str]] = {
        "bioetl.domain.types": {
            "RecordBatch",
            "RawRecordDict",
            "RawRecordBatch",
            "RawRecordList",
            "RawPayload",
        },
        "bioetl.domain.ports.extraction": {
            "RawRecord",
            "RawRecordDict",
            "RawRecordBatch",
        },
        "bioetl.domain.ports": {
            "RawRecord",
            "RawRecordDict",
            "RawRecordBatch",
            "RawRecordList",
            "RawPayload",
        },
        "bioetl.domain.record_source": {
            "SourceRecord",
            "RecordSource",
        },
    }
    return module_to_names.get(module_name, set())


def make_module_getattr(
    module_name: str,
    *,
    additional_names: dict[str, DeprecatedAlias] | None = None,
) -> Any:
    """Create a __getattr__ function for a module with deprecated names.

    Factory function that generates a properly configured __getattr__
    for modules with deprecated exports.

    Args:
        module_name: Full module path (e.g., 'bioetl.domain.types').
        additional_names: Additional deprecated names specific to this module.

    Returns:
        A __getattr__ function suitable for module-level deprecation handling.

    Example:
        >>> # In bioetl/domain/types.py
        >>> from bioetl.domain._deprecations import make_module_getattr
        >>> __getattr__ = make_module_getattr("bioetl.domain.types")
    """
    allowed_names = get_deprecated_names_for_module(module_name)
    if additional_names:
        allowed_names = allowed_names | set(additional_names.keys())

    def __getattr__(name: str) -> Any:
        if name in allowed_names:
            emit_deprecation_warning(name, stacklevel=3)
            return resolve_deprecated_type(name)
        raise AttributeError(f"module {module_name!r} has no attribute {name!r}")

    return __getattr__


# =============================================================================
# Introspection Utilities
# =============================================================================


def list_deprecated_aliases(
    *,
    category: str | None = None,
    include_removed: bool = False,
) -> list[tuple[str, DeprecatedAlias]]:
    """List all deprecated aliases, optionally filtered by category.

    Args:
        category: Filter by category ('type_alias', 'class_alias', 'function').
        include_removed: Include aliases that have already been removed.

    Returns:
        List of (old_name, DeprecatedAlias) tuples.
    """
    result = []
    for name, alias in DEPRECATED_ALIASES.items():
        if category and alias.category != category:
            continue
        result.append((name, alias))
    return sorted(result, key=lambda x: (x[1].category, x[0]))


def generate_migration_table() -> str:
    """Generate a markdown table of deprecated aliases for documentation.

    Returns:
        Markdown-formatted table of deprecations.
    """
    lines = [
        "| Deprecated Name | Replacement | Module | Category | Removal |",
        "|-----------------|-------------|--------|----------|---------|",
    ]

    for name, alias in sorted(DEPRECATED_ALIASES.items()):
        lines.append(
            f"| `{name}` | `{alias.new_name}` | `{alias.new_module}` | "
            f"{alias.category} | v{REMOVAL_VERSION} |"
        )

    return "\n".join(lines)


__all__ = [
    # Constants
    "REMOVAL_VERSION",
    "DEPRECATED_ALIASES",
    # Types
    "DeprecatedAlias",
    # Core functions
    "emit_deprecation_warning",
    "resolve_deprecated_type",
    "get_deprecated_names_for_module",
    "make_module_getattr",
    # Introspection
    "list_deprecated_aliases",
    "generate_migration_table",
]
