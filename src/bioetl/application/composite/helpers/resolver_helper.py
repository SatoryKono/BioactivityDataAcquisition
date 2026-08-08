"""Helper for creating resolver services with common patterns."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import TypeVar

import polars as pl

from bioetl.application.composite.join_key_normalization import (
    JOIN_KEY_NORMALIZATION_POLICIES,
    JoinKeyNormalizationPolicy,
)
from bioetl.domain.ports import LoggerPort

TResolver = TypeVar("TResolver")


class ResolverHelper:
    """Helper for creating resolver services with common normalization and logging patterns."""

    def __init__(
        self,
        *,
        logger: LoggerPort,
        normalization_policies: Mapping[
            str, JoinKeyNormalizationPolicy
        ] = JOIN_KEY_NORMALIZATION_POLICIES,
    ) -> None:
        self._logger = logger
        self._normalization_policies = normalization_policies

    def normalize_join_keys(
        self,
        df: pl.DataFrame,
        join_keys: list[str],
        pipeline: str | None = None,
        parse_pipeline_name: Callable[[str], tuple[str, str]] | None = None,
    ) -> pl.DataFrame:
        """Apply canonical join key normalization to DataFrame columns.

        Args:
            df: DataFrame containing columns to normalize.
            join_keys: List of join key names to normalize.
            pipeline: Optional pipeline name used to locate qualified column variants.
            parse_pipeline_name: Optional function to parse pipeline names.

        Returns:
            DataFrame with normalized join key columns.
        """
        from bioetl.application.composite.join_key_resolution_helpers import (
            normalize_join_key_columns,
        )

        return normalize_join_key_columns(
            df=df,
            join_keys=join_keys,
            pipeline=pipeline,
            normalization_policies=self._normalization_policies,
            parse_pipeline_name=parse_pipeline_name or (lambda _value: ("", "")),
        )

    def log_info(
        self,
        message: str,
        **kwargs: object,
    ) -> None:
        """Log informational message with context."""
        self._logger.info(message, **kwargs)

    def log_warning(
        self,
        message: str,
        **kwargs: object,
    ) -> None:
        """Log warning message with context."""
        self._logger.warning(message, **kwargs)

    def log_debug(
        self,
        message: str,
        **kwargs: object,
    ) -> None:
        """Log debug message with context."""
        self._logger.debug(message, **kwargs)

    def log_error(
        self,
        message: str,
        **kwargs: object,
    ) -> None:
        """Log error message with context."""
        self._logger.error(message, **kwargs)

    def create_resolver_service(
        self,
        service_class: Callable[..., TResolver],
        **init_kwargs: object,
    ) -> TResolver:
        """Create a resolver service instance with shared helper configuration.

        Args:
            service_class: The resolver service class to instantiate.
            **init_kwargs: Additional initialization arguments for the service.

        Returns:
            Instantiated resolver service.
        """
        return service_class(
            logger=self._logger,
            normalization_policies=self._normalization_policies,
            **init_kwargs,
        )


def create_resolver_helper(
    logger: LoggerPort,
    normalization_policies: Mapping[
        str, JoinKeyNormalizationPolicy
    ] = JOIN_KEY_NORMALIZATION_POLICIES,
) -> ResolverHelper:
    """Create a resolver helper with default configuration.

    Args:
        logger: Logger instance for diagnostic messages.
        normalization_policies: Join key normalization policies.

    Returns:
        Configured ResolverHelper instance.
    """
    return ResolverHelper(
        logger=logger,
        normalization_policies=normalization_policies,
    )


__all__ = [
    "ResolverHelper",
    "create_resolver_helper",
]
