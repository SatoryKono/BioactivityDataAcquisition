"""Filter Configuration loader with hierarchical merge.

Loads and merges filter configurations from:
1. defaults layer from configs/base/pipeline.yaml
2. configs/providers/{provider}.yaml (section "filters")
3. configs/entities/{provider}/{entity}.yaml (section "filters")
4. Inline overrides from pipeline config

Implements ADR-028: Filter Rules Externalization.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bioetl.domain.filtering import (
    GoldFilterConfig,
    InputFilterConfig,
    SilverFilterConfig,
)
from bioetl.domain.models.filter import ExtractionParams
from bioetl.infrastructure.config.base_config_loader import BaseConfigLoader
from bioetl.infrastructure.schemas.filter_config import FilterConfigFile

# Keys whose lists should concatenate (not override)
_FILTER_CONCAT_KEYS = frozenset({"required_fields", "exclude_if_present"})


class FilterConfigLoader(
    BaseConfigLoader[
        tuple[InputFilterConfig, SilverFilterConfig, GoldFilterConfig, ExtractionParams]
    ],
):
    """Loads and merges filter configurations from hierarchical files.

    Thread-safe with internal caching for performance.

    """

    def __init__(self, configs_root: Path) -> None:
        """Initialize loader with configs root directory.

        Args:
            configs_root: Path to configs/ directory.
        """
        super().__init__(configs_root)
        self._base_root = configs_root / "base"

    def load(
        self,
        provider: str,
        entity: str,
        inline_overrides: dict[str, Any] | None = None,
    ) -> tuple[
        InputFilterConfig, SilverFilterConfig, GoldFilterConfig, ExtractionParams
    ]:
        """Load merged filter config for provider/entity.

        Merge order (later wins for scalars, special handling for collections):
        1. defaults layer (MUST exist): configs/base/pipeline.yaml.filter_defaults
        2. providers/{provider}.yaml
        3. entities/{provider}/{entity}.yaml
        4. inline_overrides (from pipeline config filter_rules)

        Args:
            provider: Provider name (e.g., "chembl").
            entity: Entity name (e.g., "activity").
            inline_overrides: Optional inline overrides from pipeline config.

        Returns:
            Tuple of (InputFilterConfig, SilverFilterConfig, GoldFilterConfig,
            ExtractionParams) domain objects.

        Raises:
            FileNotFoundError: If no defaults layer exists.
            ValidationError: If merged config fails validation.
        """
        cache_key = f"{provider}:{entity}"

        if inline_overrides is None and cache_key in self._cache:
            return self._cache[cache_key]

        defaults = self._load_defaults_layer()
        if not defaults:
            raise FileNotFoundError(
                "Required filter defaults not found in "
                "configs/base/pipeline.yaml (section 'filter_defaults')."
            )

        merged = self._merge_hierarchy(
            provider,
            entity,
            inline_overrides,
            defaults=defaults,
        )

        # Validate via Pydantic
        validated = FilterConfigFile.model_validate(merged)
        domain_configs: tuple[
            InputFilterConfig, SilverFilterConfig, GoldFilterConfig, ExtractionParams
        ] = validated.to_domain()

        # Cache result if no inline overrides
        if inline_overrides is None:
            self._cache[cache_key] = domain_configs

        return domain_configs

    def load_as_dict(
        self,
        provider: str,
        entity: str,
        inline_overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Load merged filter config hierarchy as raw dict.

        Same 4-level merge order as :meth:`load` but returns the merged
        dict **without** Pydantic validation or domain conversion.
        Returns empty dict when no filter config files exist at all.

        Merge order (later wins for scalars, concat for collection keys):
        1. defaults layer (optional — empty dict if absent)
        2. providers/{provider}.yaml (optional)
        3. entities/{provider}/{entity}.yaml (optional)
        4. inline_overrides from pipeline config (highest priority)

        Used by pipeline config loading to integrate the filter hierarchy
        into the pipeline config dict before PipelineYamlConfig validation.

        Args:
            provider: Provider name (e.g., "chembl").
            entity: Entity name (e.g., "activity").
            inline_overrides: Optional inline overrides from pipeline config.

        Returns:
            Merged configuration dict (may be empty).
        """
        return self._merge_hierarchy(provider, entity, inline_overrides)

    def _merge_hierarchy(
        self,
        provider: str,
        entity: str,
        inline_overrides: dict[str, Any] | None = None,
        defaults: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Merge the 4-level filter config hierarchy into a single dict.

        Shared logic for both :meth:`load` and :meth:`load_as_dict`.

        Args:
            provider: Provider name.
            entity: Entity name.
            inline_overrides: Optional inline overrides.
            defaults: Preloaded defaults layer. If omitted, loaded automatically.

        Returns:
            Merged configuration dict.
        """
        # 1. Load defaults (returns {} if absent)
        merged = defaults if defaults is not None else self._load_defaults_layer()

        # 2. Load provider config (optional)
        provider_config = self._load_provider_layer(provider)
        if provider_config:
            merged = self._deep_merge(merged, provider_config)

        # 3. Load entity config (optional)
        entity_config = self._load_entity_layer(provider, entity)
        if entity_config:
            merged = self._deep_merge(merged, entity_config)

        # 4. Apply inline overrides (optional)
        if inline_overrides:
            merged = self._deep_merge(merged, inline_overrides)

        return merged

    def _load_defaults_layer(self) -> dict[str, Any]:
        """Load filter defaults from configs/base/pipeline.yaml."""
        base_pipeline_path = self._base_root / "pipeline.yaml"
        if base_pipeline_path.exists():
            base_pipeline = self._load_yaml(base_pipeline_path)
            defaults: dict[str, Any] = {}

            # input_filter defaults are still a top-level pipeline concern.
            input_filter = base_pipeline.get("input_filter")
            if isinstance(input_filter, dict):
                defaults["input_filter"] = input_filter

            filter_defaults = base_pipeline.get("filter_defaults")
            if isinstance(filter_defaults, dict):
                defaults = self._deep_merge(defaults, filter_defaults)

            if defaults:
                defaults.setdefault("version", "1.0.0")
                return defaults

        return {}

    def _load_provider_layer(self, provider: str) -> dict[str, Any]:
        """Load provider filter layer from unified provider config."""
        unified_provider_path = self._configs_root / "providers" / f"{provider}.yaml"
        if unified_provider_path.exists():
            unified_raw = self._load_yaml(unified_provider_path)

            filters_section = unified_raw.get("filters")
            if isinstance(filters_section, dict):
                return filters_section

            if any(
                key in unified_raw
                for key in (
                    "input_filter",
                    "silver_filters",
                    "gold_filters",
                    "extraction_params",
                )
            ):
                return unified_raw

        return {}

    def _load_entity_layer(self, provider: str, entity: str) -> dict[str, Any]:
        """Load entity filter layer from unified entity config."""
        unified_entity_path = (
            self._configs_root / "entities" / provider / f"{entity}.yaml"
        )
        if unified_entity_path.exists():
            unified_raw = self._load_yaml(unified_entity_path)

            filters_section = unified_raw.get("filters")
            if isinstance(filters_section, dict):
                return filters_section

            if any(
                key in unified_raw
                for key in (
                    "input_filter",
                    "silver_filters",
                    "gold_filters",
                    "extraction_params",
                )
            ):
                return unified_raw

        return {}

    def _deep_merge(
        self,
        base: dict[str, Any],
        override: dict[str, Any],
    ) -> dict[str, Any]:
        """Deep merge two dicts with filter-specific rules.

        Rules:
        - Scalars: override wins
        - required_fields, exclude_if_present: concatenate with deduplication
        - columns, ranges, list_lengths, list_contains: merge dicts
        - Other nested dicts: recursive merge

        Args:
            base: Base configuration dict.
            override: Override configuration dict.

        Returns:
            Merged dict (new object, inputs unchanged).
        """
        return self._deep_merge_base(base, override, _FILTER_CONCAT_KEYS)

    def _merge_string_lists(
        self,
        base: list[str],
        override: list[str],
    ) -> list[str]:
        """Merge string lists with deduplication, preserving order.

        Args:
            base: Base list.
            override: Override list.

        Returns:
            Merged list with unique values, base items first.
        """
        seen: set[str] = set()
        result: list[str] = []

        for item in base + override:
            if item not in seen:
                seen.add(item)
                result.append(item)

        return result


__all__ = ["FilterConfigLoader"]
