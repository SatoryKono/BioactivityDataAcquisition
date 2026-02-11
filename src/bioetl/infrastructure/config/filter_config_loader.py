"""Filter Configuration loader with hierarchical merge.

Loads and merges filter configurations from:
1. configs/filter/_defaults.yaml (global defaults)
2. configs/filter/providers/{provider}.yaml (provider-specific)
3. configs/filter/entities/{provider}/{entity}.yaml (entity-specific)
4. Inline overrides from pipeline config

Implements ADR-028: Filter Rules Externalization.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bioetl.domain.filtering import GoldFilterConfig, InputFilterConfig
from bioetl.domain.models.filter import ExtractionParams
from bioetl.infrastructure.config.base_config_loader import BaseConfigLoader
from bioetl.infrastructure.schemas.filter_config import FilterConfigFile

# Keys whose lists should concatenate (not override)
_FILTER_CONCAT_KEYS = frozenset({"required_fields", "exclude_if_present"})


class FilterConfigLoader(
    BaseConfigLoader[
        tuple[InputFilterConfig, GoldFilterConfig, GoldFilterConfig, ExtractionParams]
    ],
):
    """Loads and merges filter configurations from hierarchical files.

    Thread-safe with internal caching for performance.

    Attributes:
        _filter_root: Path to configs/filter/ directory.
    """

    def __init__(self, configs_root: Path) -> None:
        """Initialize loader with configs root directory.

        Args:
            configs_root: Path to configs/ directory.
        """
        super().__init__(configs_root)
        self._filter_root = configs_root / "filter"

    def load(
        self,
        provider: str,
        entity: str,
        inline_overrides: dict[str, Any] | None = None,
    ) -> tuple[InputFilterConfig, GoldFilterConfig, GoldFilterConfig, ExtractionParams]:
        """Load merged filter config for provider/entity.

        Merge order (later wins for scalars, special handling for collections):
        1. _defaults.yaml
        2. providers/{provider}.yaml
        3. entities/{provider}/{entity}.yaml
        4. inline_overrides (from pipeline config filter_rules)

        Args:
            provider: Provider name (e.g., "chembl").
            entity: Entity name (e.g., "activity").
            inline_overrides: Optional inline overrides from pipeline config.

        Returns:
            Tuple of (InputFilterConfig, SilverFilterConfig, GoldFilterConfig,
            ExtractionParams) domain objects.  Silver and Gold filters both use
            GoldFilterConfig as the domain type.

        Raises:
            FileNotFoundError: If _defaults.yaml doesn't exist.
            ValidationError: If merged config fails validation.
        """
        cache_key = f"{provider}:{entity}"

        if inline_overrides is None and cache_key in self._cache:
            return self._cache[cache_key]

        # 1. Load defaults (MUST exist)
        defaults_path = self._filter_root / "_defaults.yaml"
        if not defaults_path.exists():
            raise FileNotFoundError(
                f"Required filter defaults file not found: {defaults_path}. "
                "Create configs/filter/_defaults.yaml with global filter settings."
            )
        merged = self._load_yaml(defaults_path)

        # 2. Load provider config (optional)
        provider_path = self._filter_root / "providers" / f"{provider}.yaml"
        provider_config = self._load_yaml(provider_path)
        if provider_config:
            merged = self._deep_merge(merged, provider_config)

        # 3. Load entity config (optional)
        entity_path = self._filter_root / "entities" / provider / f"{entity}.yaml"
        entity_config = self._load_yaml(entity_path)
        if entity_config:
            merged = self._deep_merge(merged, entity_config)

        # 4. Apply inline overrides (optional)
        if inline_overrides:
            merged = self._deep_merge(merged, inline_overrides)

        # Validate via Pydantic
        validated = FilterConfigFile.model_validate(merged)
        domain_configs: tuple[
            InputFilterConfig, GoldFilterConfig, GoldFilterConfig, ExtractionParams
        ] = validated.to_domain()

        # Cache result if no inline overrides
        if inline_overrides is None:
            self._cache[cache_key] = domain_configs

        return domain_configs

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
