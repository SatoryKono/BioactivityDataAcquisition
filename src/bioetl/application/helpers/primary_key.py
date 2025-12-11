"""
Unified primary key resolution for BioETL pipelines.

This module provides a single source of truth for resolving entity primary keys
from pipeline configuration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.configs import PipelineConfig


def resolve_primary_key(
    config: PipelineConfig,
    *,
    fallback: str | None = None,
) -> str:
    """
    Resolve the primary key for an entity based on pipeline configuration.

    Resolution order:
    1. config.identity.primary_key[0] (first element of primary key list)
    2. f"{entity_name}_id" (convention-based fallback)
    3. fallback parameter (if provided)
    4. ValueError (if no resolution possible)

    Args:
        config: Pipeline configuration object.
        fallback: Optional fallback value if primary key cannot be determined.

    Returns:
        The resolved primary key field name.

    Raises:
        ValueError: If primary key cannot be resolved and no fallback provided.

    Examples:
        >>> primary_key = resolve_primary_key(config)
        >>> primary_key = resolve_primary_key(config, fallback="id")
    """
    primary_key: str | None = None
    try:
        primary_keys = getattr(config, "identity").primary_key
    except Exception:
        primary_keys = getattr(config, "primary_key", None)
    if primary_keys:
        if isinstance(primary_keys, list):
            if len(primary_keys) > 0 and primary_keys[0]:
                primary_key = primary_keys[0]
        elif isinstance(primary_keys, str) and primary_keys:
            primary_key = primary_keys

    if not primary_key:
        try:
            entity_name = getattr(config, "entity_name")
        except Exception:
            entity_name = getattr(config, "entity", None)
        if not entity_name:
            raise ValueError("Missing entity name in config")
        primary_key = f"{entity_name}_id"

    if not primary_key and fallback is not None:
        primary_key = fallback

    if not primary_key:
        try:
            entity_name = getattr(config, "entity_name")
        except Exception:
            entity_name = getattr(config, "entity", "unknown")
        raise ValueError(
            (
                "Could not resolve primary key for entity "
                f"'{entity_name}'. Please set 'primary_key' in config."
            )
        )

    return primary_key


def resolve_primary_key_with_filter(
    config: PipelineConfig,
    *,
    fallback: str | None = None,
) -> tuple[str, str]:
    """
    Resolve primary key and its corresponding API filter key.

    This is a convenience wrapper that returns both the primary key
    and the filter key (primary_key + "__in") used for API batch queries.

    Args:
        config: Pipeline configuration object.
        fallback: Optional fallback value if primary key cannot be determined.

    Returns:
        Tuple of (primary_key, filter_key) where filter_key is "{primary_key}__in".

    Raises:
        ValueError: If primary key cannot be resolved and no fallback provided.

    Examples:
        >>> primary_key, filter_key = resolve_primary_key_with_filter(config)
        >>> # primary_key = "activity_id", filter_key = "activity_id__in"
    """
    primary_key = resolve_primary_key(config, fallback=fallback)
    return primary_key, f"{primary_key}__in"
