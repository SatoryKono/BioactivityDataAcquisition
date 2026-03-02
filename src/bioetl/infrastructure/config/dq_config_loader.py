"""DQ Configuration loader with hierarchical merge.

Loads and merges DQ configurations from:
1. configs/base/quality.yaml (global defaults, preferred)
2. configs/providers/{provider}.yaml (section "quality", preferred)
3. configs/quality/providers/{provider}.yaml (legacy fallback)
4. configs/entities/{provider}/{entity}.yaml (section "quality", preferred)
5. configs/quality/entities/{provider}/{entity}.yaml (legacy fallback)
6. Inline overrides from pipeline config

Implements RULES.md §3.1.2 DQ Thresholds.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, cast

from bioetl.domain.config import DQConfig
from bioetl.infrastructure.config_merge import ListMergeFn, config_merge
from bioetl.infrastructure.schemas.dq_config import DQConfigFile

from .base_config_loader import _load_yaml_file


class DQConfigLoader:
    """Loads and merges DQ configurations from hierarchical files.

    Thread-safe with internal caching for performance.

    Attributes:
        _configs_root: Root path to configs/ directory.
        _dq_root: Path to configs/quality directory.
        _cache: Cache of loaded configs keyed by "provider:entity".
    """

    def __init__(self, configs_root: Path, relaxed_dq: bool = False) -> None:
        """Initialize loader with configs root directory.

        Args:
            configs_root: Path to configs/ directory.
            relaxed_dq: Whether to relax DQ thresholds (default: False).
        """
        self._configs_root = configs_root
        self._base_root = configs_root / "base"
        self._dq_root = configs_root / "quality"
        self._relaxed_dq = relaxed_dq
        self._cache: dict[str, DQConfig] = {}

    def _load_optional(self, *parts: str) -> dict[str, Any]:
        """Load YAML from DQ path if it exists, else return empty dict."""
        path = self._dq_root.joinpath(*parts)
        return self._load_yaml(path) if path.exists() else {}

    def _load_provider_layer(self, provider: str) -> dict[str, Any]:
        """Load provider DQ layer from unified provider config or legacy path."""
        unified_provider_path = self._configs_root / "providers" / f"{provider}.yaml"
        if unified_provider_path.exists():
            unified_raw = self._load_yaml(unified_provider_path)

            quality_section = unified_raw.get("quality")
            if isinstance(quality_section, dict):
                return quality_section

            if any(
                key in unified_raw
                for key in (
                    "thresholds",
                    "field_validations",
                    "provider_field_validations",
                    "cross_field_validations",
                )
            ):
                return unified_raw

        return self._load_optional("providers", f"{provider}.yaml")

    def _load_entity_layer(self, provider: str, entity: str) -> dict[str, Any]:
        """Load entity DQ layer from unified entity config or legacy path."""
        unified_entity_path = (
            self._configs_root / "entities" / provider / f"{entity}.yaml"
        )
        if unified_entity_path.exists():
            unified_raw = self._load_yaml(unified_entity_path)

            quality_section = unified_raw.get("quality")
            if isinstance(quality_section, dict):
                return quality_section

            if any(
                key in unified_raw
                for key in (
                    "thresholds",
                    "field_validations",
                    "entity_field_validations",
                    "cross_field_validations",
                )
            ):
                return unified_raw

        return self._load_optional("entities", provider, f"{entity}.yaml")

    def _merge_hierarchy(
        self,
        provider: str,
        entity: str,
        inline_overrides: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Build merged config from defaults → provider → entity → inline."""
        merged = self._load_defaults_layer()
        if not merged:
            raise FileNotFoundError(
                "Required DQ defaults file not found in configs/base/quality.yaml. "
                "Create defaults in this location."
            )

        for layer in (
            self._load_provider_layer(provider),
            self._load_entity_layer(provider, entity),
            inline_overrides or {},
        ):
            if layer:
                merged = self._deep_merge(merged, layer)

        if self._relaxed_dq:
            merged = self._deep_merge(
                merged,
                {"thresholds": {"soft_fail": 0.99, "hard_fail": 1.0}},
            )
        return merged

    def _load_defaults_layer(self) -> dict[str, Any]:
        """Load DQ defaults from consolidated base path."""
        base_defaults_path = self._base_root / "quality.yaml"
        if base_defaults_path.exists():
            return self._load_yaml(base_defaults_path)

        return {}

    def load(
        self,
        provider: str,
        entity: str,
        inline_overrides: dict[str, Any] | None = None,
    ) -> DQConfig:
        """Load merged DQ config for provider/entity.

        Merge order (later wins for scalars, concatenate for lists):
        1. base/quality.yaml
        2. providers/{provider}.yaml
        3. entities/{provider}/{entity}.yaml
        4. inline_overrides (from pipeline config)

        Args:
            provider: Provider name (e.g., "chembl").
            entity: Entity name (e.g., "activity").
            inline_overrides: Optional inline overrides from pipeline config.

        Returns:
            Merged DQConfig domain object.

        Raises:
            FileNotFoundError: If no DQ defaults file exists.
            ValidationError: If merged config fails validation.
        """
        cache_key = f"{provider}:{entity}:relaxed={self._relaxed_dq}"

        if inline_overrides is None and cache_key in self._cache:
            return self._cache[cache_key]

        merged = self._merge_hierarchy(provider, entity, inline_overrides)

        normalized = self._normalize_to_file_format(merged)
        validated = DQConfigFile.model_validate(normalized)
        domain_config: DQConfig = validated.to_domain()

        if inline_overrides is None:
            self._cache[cache_key] = domain_config

        return domain_config

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
        return _load_yaml_file(path)

    def _deep_merge(
        self,
        base: dict[str, Any],
        override: dict[str, Any],
    ) -> dict[str, Any]:
        """Deep merge two dicts.

        Rules:
        - Scalars: override wins
        - Lists ending with '_validations': concatenate with deduplication
        - Other lists: override wins
        - Nested dicts: recursive merge

        Args:
            base: Base configuration dict.
            override: Override configuration dict.

        Returns:
            Merged dict (new object, inputs unchanged).
        """
        return config_merge(
            base,
            override,
            list_merger_resolver=self._resolve_list_merger,
        )

    def _resolve_list_merger(self, key: str) -> ListMergeFn | None:
        """Resolve list merge strategy for a given key."""
        if key.endswith("_validations"):
            return self._merge_validation_lists_for_key
        return None

    def _merge_validation_lists_for_key(
        self,
        base: list[Any],
        override: list[Any],
        _key: str,
    ) -> list[Any]:
        """Adapter for config_merge list strategy callback."""
        if not all(isinstance(item, dict) for item in base) or not all(
            isinstance(item, dict) for item in override
        ):
            return copy.deepcopy(override)

        return self._merge_validation_lists(
            cast(list[dict[str, Any]], base),
            cast(list[dict[str, Any]], override),
        )

    def _merge_validation_lists(
        self,
        base: list[dict[str, Any]],
        override: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Merge validation lists, avoiding duplicates by name/field.

        Override entries with same name/field replace base entries.

        Args:
            base: Base validation list.
            override: Override validation list.

        Returns:
            Merged validation list with deduplication.
        """

        def get_key(item: dict[str, Any]) -> str:
            """Get unique key for validation item.

            Cross-field/conditional validations use 'name' as key.
            Field validations use composite key (field, type, severity)
            to allow multiple rules per field (e.g. error + warn ranges).

            Args:
                item: Item.

            Returns:
                Key.
            """
            if "name" in item:
                return str(item["name"])
            field = item.get("field", "")
            vtype = item.get("type", "")
            severity = item.get("severity", "error")
            return f"{field}:{vtype}:{severity}"

        # Build result map, override entries replace base entries with same key
        result_map: dict[str, dict[str, Any]] = {}
        for item in base:
            key = get_key(item)
            result_map[key] = copy.deepcopy(item)

        for item in override:
            key = get_key(item)
            result_map[key] = copy.deepcopy(item)

        return list(result_map.values())

    def _normalize_to_file_format(
        self,
        merged: dict[str, Any],
    ) -> dict[str, Any]:
        """Normalize merged dict to DQConfigFile schema.

        Handles conversion from inline format (soft_fail_threshold)
        to file format (thresholds.soft_fail).

        Also maps field_validations, cross_field_validations,
        conditional_validations to their hierarchical counterparts.

        Args:
            merged: Raw merged configuration dict.

        Returns:
            Dict compatible with DQConfigFile schema.
        """
        result = copy.deepcopy(merged)

        # Handle threshold normalization
        # inline: soft_fail_threshold, hard_fail_threshold
        # file: thresholds.soft_fail, thresholds.hard_fail
        if "soft_fail_threshold" in result or "hard_fail_threshold" in result:
            thresholds = result.get("thresholds", {})
            if not isinstance(thresholds, dict):
                thresholds = {}

            if "soft_fail_threshold" in result:
                thresholds["soft_fail"] = result.pop("soft_fail_threshold")
            if "hard_fail_threshold" in result:
                thresholds["hard_fail"] = result.pop("hard_fail_threshold")

            result["thresholds"] = thresholds

        # Map flat validation lists to hierarchical structure
        # This handles cases where inline config has flat lists
        if "field_validations" in result:
            # Move to entity level (highest priority in merge)
            result.setdefault("entity_field_validations", [])
            result["entity_field_validations"].extend(result.pop("field_validations"))

        if "cross_field_validations" in result:
            result.setdefault("entity_cross_field_validations", [])
            result["entity_cross_field_validations"].extend(
                result.pop("cross_field_validations")
            )

        if "conditional_validations" in result:
            result.setdefault("entity_conditional_validations", [])
            result["entity_conditional_validations"].extend(
                result.pop("conditional_validations")
            )

        if "key_nullability_rules" in result:
            result.setdefault("key_nullability", [])
            result["key_nullability"].extend(result.pop("key_nullability_rules"))

        return result


__all__ = ["DQConfigLoader"]
