"""Filter Configuration loader with hierarchical merge.

Loads and merges filter configurations from:
1. configs/filter/_defaults.yaml (global defaults)
2. configs/filter/providers/{provider}.yaml (provider-specific)
3. configs/filter/entities/{provider}/{entity}.yaml (entity-specific)
4. Inline overrides from pipeline config

Implements ADR-028: Filter Rules Externalization.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml

from bioetl.domain.filtering import GoldFilterConfig, InputFilterConfig
from bioetl.infrastructure.schemas.filter_config import FilterConfigFile


class FilterConfigLoader:
    """Loads and merges filter configurations from hierarchical files.

    Thread-safe with internal caching for performance.

    Attributes:
        _configs_root: Root path to configs/ directory.
        _filter_root: Path to configs/filter/ directory.
        _cache: Cache of loaded configs keyed by "provider:entity".
    """

    def __init__(self, configs_root: Path) -> None:
        """Initialize loader with configs root directory.

        Args:
            configs_root: Path to configs/ directory.
        """
        self._configs_root = configs_root
        self._filter_root = configs_root / "filter"
        self._cache: dict[str, tuple[InputFilterConfig, GoldFilterConfig]] = {}

    def load(
        self,
        provider: str,
        entity: str,
        inline_overrides: dict[str, Any] | None = None,
    ) -> tuple[InputFilterConfig, GoldFilterConfig]:
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
            Tuple of (InputFilterConfig, GoldFilterConfig) domain objects.

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
        domain_configs = validated.to_domain()

        # Cache result if no inline overrides
        if inline_overrides is None:
            self._cache[cache_key] = domain_configs

        return domain_configs

    def clear_cache(self) -> None:
        """Clear the configuration cache.

        Call after modifying config files during development/testing.
        """
        self._cache.clear()

    def _load_yaml(self, path: Path) -> dict[str, Any]:
        """Load YAML file, return empty dict if not exists.

        Args:
            path: Path to YAML file.

        Returns:
            Parsed YAML content or empty dict.
        """
        if not path.exists():
            return {}

        with open(path, encoding="utf-8") as f:
            content = yaml.safe_load(f)
            return content if content is not None else {}

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
        result = copy.deepcopy(base)

        for key, override_value in override.items():
            if key not in result:
                result[key] = copy.deepcopy(override_value)
            elif isinstance(override_value, dict) and isinstance(result[key], dict):
                # Recursive merge for nested dicts (including gold_filters)
                result[key] = self._deep_merge(result[key], override_value)
            elif (
                isinstance(override_value, list)
                and isinstance(result[key], list)
                and key in ("required_fields", "exclude_if_present")
            ):
                # Concatenate and deduplicate lists for these keys
                result[key] = self._merge_string_lists(result[key], override_value)
            else:
                # Scalar or other list: override wins
                result[key] = copy.deepcopy(override_value)

        return result

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
