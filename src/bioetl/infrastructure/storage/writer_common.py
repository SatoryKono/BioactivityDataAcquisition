"""Common functionality for Silver and Gold writers to reduce code duplication."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, TypeVar, cast

from bioetl.infrastructure.storage.versioned_table_resolver import resolve_write_targets

T = TypeVar("T")


def validate_write_versions(write_versions: Sequence[str]) -> None:
    """Validate that write_versions is not empty to prevent zip() errors.

    Args:
        write_versions: Sequence of contract versions for writing

    Raises:
        ValueError: If write_versions is empty
    """
    if not write_versions:
        raise ValueError(
            "Contract rollout policy must specify at least one write version"
        )


def get_write_targets(table_name: str, write_versions: Sequence[str]) -> list[str]:
    """Resolve physical write targets for versioned tables.

    Args:
        table_name: Logical table name
        write_versions: Sequence of contract versions

    Returns:
        List of physical table names for each version
    """
    return resolve_write_targets(table_name, write_versions)


def iterate_write_targets(
    write_versions: Sequence[str],
    write_targets: Sequence[str],
) -> list[tuple[str, str]]:
    """Safely iterate over write versions and their corresponding targets.

    Args:
        write_versions: Sequence of contract versions
        write_targets: Sequence of physical table names

    Returns:
        List of (version, target) tuples

    Raises:
        ValueError: If lengths don't match (shouldn't happen with proper usage)
    """
    if len(write_versions) != len(write_targets):
        raise ValueError(
            f"Write versions and targets length mismatch: "
            f"{len(write_versions)} versions vs {len(write_targets)} targets"
        )
    return list(zip(write_versions, write_targets, strict=True))
