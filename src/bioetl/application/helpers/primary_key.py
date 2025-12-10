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
    1. config.primary_key (explicit field)
    2. config.pipeline["primary_key"] (pipeline options dict)
    3. f"{entity_name}_id" (convention-based fallback)
    4. fallback parameter (if provided)
    5. ValueError (if no resolution possible)

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
    # 1. Check explicit primary_key field
    pk = config.primary_key

    # 2. Check pipeline options dict
    if not pk:
        pipeline_opts = config.pipeline or {}
        if "primary_key" in pipeline_opts:
            pk = pipeline_opts["primary_key"]

    # 3. Use entity-based convention
    if not pk:
        pk = f"{config.entity_name}_id"

    # 4. Use fallback if provided and pk still empty
    if not pk and fallback is not None:
        pk = fallback

    # 5. Raise if still no resolution
    if not pk:
        raise ValueError(
            f"Could not resolve primary key for entity '{config.entity_name}'. "
            "Please set 'primary_key' in config or pipeline options."
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
