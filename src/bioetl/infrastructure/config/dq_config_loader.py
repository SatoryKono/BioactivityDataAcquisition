"""DQ Configuration loader with hierarchical merge.

Loads and merges DQ configurations from:
1. configs/quality/_defaults.yaml (fallback: configs/dq/_defaults.yaml) (global defaults)
2. configs/quality/providers/{provider}.yaml (fallback: configs/dq/providers/{provider}.yaml) (provider-specific)
3. configs/quality/entities/{provider}/{entity}.yaml (fallback: configs/dq/entities/{provider}/{entity}.yaml) (entity-specific)
4. Inline overrides from pipeline config

Implements RULES.md §3.1.2 DQ Thresholds.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml

from bioetl.domain.config import DQConfig
from bioetl.infrastructure.schemas.dq_config import DQConfigFile


class DQConfigLoader:
    """Loads and merges DQ configurations from hierarchical files.

    Thread-safe with internal caching for performance.

    Attributes:
        _configs_root: Root path to configs/ directory.
        _dq_roots: Paths to configs/quality and configs/dq directories.
        _cache: Cache of loaded configs keyed by "provider:entity".
    """

    def __init__(self, configs_root: Path, relaxed_dq: bool = False) -> None:
        """Initialize loader with configs root directory.

        Args:
            configs_root: Path to configs/ directory.
            relaxed_dq: Whether to relax DQ thresholds (default: False).
        """
        self._configs_root = configs_root
        self._dq_roots = (configs_root / "quality", configs_root / "dq")
        self._relaxed_dq = relaxed_dq
        self._cache: dict[str, DQConfig] = {}

    def _resolve_dq_path(self, *parts: str) -> Path | None:
        """Resolve DQ config path with new->legacy directory fallback."""
        for root in self._dq_roots:
            candidate = root.joinpath(*parts)
            if candidate.exists():
                return candidate
        return None

    def _load_optional(self, *parts: str) -> dict[str, Any]:
        """Load YAML from DQ path if it exists, else return empty dict."""
        path = self._resolve_dq_path(*parts)
        return self._load_yaml(path) if path else {}

    def _merge_hierarchy(
        self,
        provider: str,
        entity: str,
        inline_overrides: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Build merged config from defaults → provider → entity → inline."""
        defaults_path = self._resolve_dq_path("_defaults.yaml")
        if defaults_path is None:
            raise FileNotFoundError(
                "Required DQ defaults file not found in configs/quality or configs/dq. "
                "Create _defaults.yaml with global DQ settings."
            )
        merged = self._load_yaml(defaults_path)

        for layer in (
            self._load_optional("providers", f"{provider}.yaml"),
            self._load_optional("entities", provider, f"{entity}.yaml"),
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

    def load(
        self,
        provider: str,
        entity: str,
        inline_overrides: dict[str, Any] | None = None,
    ) -> DQConfig:
        """Load merged DQ config for provider/entity.

        Merge order (later wins for scalars, concatenate for lists):
        1. _defaults.yaml
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
            FileNotFoundError: If _defaults.yaml doesn't exist.
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
        result = copy.deepcopy(base)

        for key, override_value in override.items():
            if key not in result:
                result[key] = copy.deepcopy(override_value)
            elif isinstance(override_value, dict) and isinstance(result[key], dict):
                # Recursive merge for nested dicts
                result[key] = self._deep_merge(result[key], override_value)
            elif (
                isinstance(override_value, list)
                and isinstance(result[key], list)
                and key.endswith("_validations")
            ):
                # Concatenate validation lists (deduplicate by name/field)
                result[key] = self._merge_validation_lists(result[key], override_value)
            else:
                # Scalar or non-validation list: override
                result[key] = copy.deepcopy(override_value)

        return result

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
            """Get unique key for validation item."""
            # Use 'name' for cross-field/conditional, 'field' for field validations
            return str(item.get("name") or item.get("field", ""))

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

        return result


__all__ = ["DQConfigLoader"]
