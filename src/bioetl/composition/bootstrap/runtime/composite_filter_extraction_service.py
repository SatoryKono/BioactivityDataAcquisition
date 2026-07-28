"""Filter extraction helpers for composite runtime runner factories."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

import polars as pl

from bioetl.domain.normalization.join_keys import (
    JOIN_KEY_NORMALIZATION_POLICIES,
    JoinKeyNormalizationPolicy,
    stringify_join_key_value,
)

if TYPE_CHECKING:
    from bioetl.domain.composite import DependencyConfig, EnricherConfig
    from bioetl.domain.ports import LoggerPort

class CompositeFilterExtractor:
    """Extract runner filter inputs from keys DataFrame."""

    def __init__(
        self,
        logger: LoggerPort | None = None,
        normalization_policies: Mapping[
            str, JoinKeyNormalizationPolicy
        ] = JOIN_KEY_NORMALIZATION_POLICIES,
    ) -> None:
        self._logger = logger
        self._normalization_policies = normalization_policies

    def to_id_str(self, value: object, *, key: str) -> str:
        """Convert a join key to a canonical filter ID string."""
        return str(
            stringify_join_key_value(
                value,
                key=key,
                normalization_policies=self._normalization_policies,
            )
        )

    def _deduplicate_filter_ids(
        self,
        values: list[object],
        *,
        key: str,
    ) -> tuple[str, ...]:
        """Normalize values and preserve first-seen order after deduplication."""
        return tuple(dict.fromkeys(self.to_id_str(value, key=key) for value in values))

    def build_fallback_mapping(
        self,
        keys: pl.DataFrame,
        filter_key: str,
        join_keys: tuple[str, ...],
    ) -> dict[str, str] | None:
        """Build ID-to-title mapping when title is part of the join keys."""
        if "title" not in join_keys or "title" not in keys.columns:
            return None
        pairs = keys.select([filter_key, "title"]).drop_nulls().iter_rows()
        mapping: dict[str, str] = {}
        for key, title in pairs:
            mapping.setdefault(self.to_id_str(key, key=filter_key), str(title))
        return mapping

    @staticmethod
    def find_filter_key(
        join_keys: tuple[str, ...],
        columns: list[str],
    ) -> str | None:
        """Find the first usable join key, preferring non-title keys."""
        for key in join_keys:
            if key == "title" and len(join_keys) > 1:
                continue
            if key in columns:
                return key
        return None

    def extract_enricher_filters(
        self,
        enricher_cfg: EnricherConfig,
        keys: pl.DataFrame | None,
    ) -> tuple[tuple[str, ...] | None, str | None, dict[str, str] | None]:
        """Extract single-field filters and fallback mapping for an enricher."""
        if keys is None or len(keys) == 0:
            self._debug(
                "No keys available for enricher", pipeline=enricher_cfg.pipeline
            )
            return None, None, None

        filter_key = self.find_filter_key(enricher_cfg.join_keys, keys.columns)
        if filter_key is None:
            self._warning(
                "Join key not found in keys columns",
                pipeline=enricher_cfg.pipeline,
                join_keys=list(enricher_cfg.join_keys),
                available_columns=list(keys.columns),
            )
            return None, None, None

        key_values = keys.select(filter_key).drop_nulls().to_series().to_list()
        if not key_values:
            return None, None, None

        filter_ids = self._deduplicate_filter_ids(key_values, key=filter_key)
        fallback_mapping = self.build_fallback_mapping(
            keys=keys,
            filter_key=filter_key,
            join_keys=enricher_cfg.join_keys,
        )
        return filter_ids, filter_key, fallback_mapping

    def extract_field_values(
        self,
        keys: pl.DataFrame,
        field: str,
    ) -> tuple[str, ...] | None:
        """Extract unique non-null values for a field from the keys frame."""
        if field not in keys.columns:
            return None
        values = keys.select(field).drop_nulls().to_series().to_list()
        if not values:
            return None
        return self._deduplicate_filter_ids(values, key=field)

    def extract_multi_filter_ids(
        self,
        dep_cfg: DependencyConfig,
        keys: pl.DataFrame | None,
    ) -> dict[str, tuple[str, ...]] | None:
        """Extract multi-field filter IDs for a dependency pipeline."""
        if keys is None or len(keys) == 0:
            return None

        result: dict[str, tuple[str, ...]] = {}
        for field in dep_cfg.effective_filter_fields:
            values = self.extract_field_values(keys, field)
            if values is None:
                self._warning(
                    "Multi-filter field missing or empty",
                    pipeline=dep_cfg.pipeline,
                    field=field,
                    available_columns=list(keys.columns),
                )
                return None
            result[field] = values

        self._info(
            "Extracted multi-field filter IDs",
            pipeline=dep_cfg.pipeline,
            fields=list(result.keys()),
            counts={field: len(ids) for field, ids in result.items()},
        )
        return result

    def resolve_dependency_filter_inputs(
        self,
        dep_cfg: DependencyConfig | None,
        keys: pl.DataFrame | None,
    ) -> tuple[tuple[str, ...] | None, str | None, dict[str, tuple[str, ...]] | None]:
        """Resolve single-field or multi-field dependency filter inputs."""
        filter_ids: tuple[str, ...] | None = None
        filter_field: str | None = None
        multi_filter_ids: dict[str, tuple[str, ...]] | None = None

        if dep_cfg is None or keys is None or len(keys) == 0:
            return filter_ids, filter_field, multi_filter_ids

        if dep_cfg.is_multi_field_filter:
            multi_filter_ids = self.extract_multi_filter_ids(dep_cfg, keys)
            return filter_ids, filter_field, multi_filter_ids

        for key in dep_cfg.join_keys:
            if key not in keys.columns:
                continue
            key_values = keys.select(key).drop_nulls().to_series().to_list()
            if not key_values:
                continue
            filter_ids = self._deduplicate_filter_ids(key_values, key=key)
            filter_field = dep_cfg.filter_field or key
            break

        return filter_ids, filter_field, multi_filter_ids

    def _debug(self, event: str, **kwargs: object) -> None:
        if self._logger is not None:
            self._logger.debug(event, **kwargs)

    def _info(self, event: str, **kwargs: object) -> None:
        if self._logger is not None:
            self._logger.info(event, **kwargs)

    def _warning(self, event: str, **kwargs: object) -> None:
        if self._logger is not None:
            self._logger.warning(event, **kwargs)

__all__ = ["CompositeFilterExtractor"]
