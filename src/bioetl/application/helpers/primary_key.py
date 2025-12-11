"""
Unified primary key resolution for BioETL pipelines.

This module provides a single source of truth for resolving entity primary keys
from pipeline configuration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.configs import PipelineConfig


def _get_primary_keys_from_config(config: PipelineConfig) -> list[str] | str | None:
    """Extract primary keys from config, handling both identity.primary_key and primary_key."""
    try:
        return getattr(config, "identity").primary_key
    except Exception:
        return getattr(config, "primary_key", None)


def _get_entity_name_from_config(config: PipelineConfig) -> str | None:
    """Extract entity name from config, handling both entity_name and entity."""
    try:
        return getattr(config, "entity_name")
    except Exception:
        return getattr(config, "entity", None)


def _extract_first_primary_key(primary_keys: list[str] | str | None) -> str | None:
    """Extract first primary key from list or string."""
    if not primary_keys:
        return None
    if isinstance(primary_keys, list):
        return primary_keys[0] if primary_keys and primary_keys[0] else None
    return primary_keys if isinstance(primary_keys, str) else None


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
        >>> pk = resolve_primary_key(config)
        >>> pk = resolve_primary_key(config, fallback="id")
    """
    # Try to get primary key from config
    primary_keys = _get_primary_keys_from_config(config)
    pk = _extract_first_primary_key(primary_keys)

    # Fallback to convention-based naming
    if not pk:
        entity_name = _get_entity_name_from_config(config)
        if not entity_name:
            raise ValueError("Missing entity name in config")
        pk = f"{entity_name}_id"

    # Use provided fallback
    if not pk and fallback is not None:
        pk = fallback

    # Final validation
    if not pk:
        entity_name = _get_entity_name_from_config(config) or "unknown"
        raise ValueError(
            f"Could not resolve primary key for entity '{entity_name}'. "
            "Please set 'primary_key' in config."
        )

    return pk


def resolve_primary_key_with_filter(
    config: PipelineConfig,
    *,
    fallback: str | None = None,
) -> tuple[str, str]:
    """
    Resolve primary key and its corresponding API filter key.

    This is a convenience wrapper that returns both the primary key
    and the filter key (pk + "__in") used for API batch queries.

    Args:
        config: Pipeline configuration object.
        fallback: Optional fallback value if primary key cannot be determined.

    Returns:
        Tuple of (primary_key, filter_key) where filter_key is "{pk}__in".

    Raises:
        ValueError: If primary key cannot be resolved and no fallback provided.

    Examples:
        >>> pk, filter_key = resolve_primary_key_with_filter(config)
        >>> # pk = "activity_id", filter_key = "activity_id__in"
    """
    pk = resolve_primary_key(config, fallback=fallback)
    return pk, f"{pk}__in"
