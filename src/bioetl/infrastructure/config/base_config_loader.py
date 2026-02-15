"""Base configuration loader with common merge utilities.

Provides shared functionality for hierarchical config loaders:
- YAML file loading with safe defaults
- Deep merge with configurable list handling
- Caching infrastructure

Used by:
- DQConfigLoader
- FilterConfigLoader
"""

from __future__ import annotations

import copy
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Generic, TypeVar

import yaml

T = TypeVar("T")


def _load_yaml_file(path: Path) -> dict[str, Any]:
    """Load YAML file, returning empty dict if missing or empty."""
    if not path.exists():
        return {}

    with open(path, encoding="utf-8") as f:
        content = yaml.safe_load(f)
        return content if content is not None else {}


class BaseConfigLoader(ABC, Generic[T]):
    """Abstract base class for hierarchical config loaders.

    Provides common utilities for loading and merging YAML configs.
    Subclasses implement specific merge rules and domain conversion.

    Type Parameters:
        T: The domain type returned by load().
    """

    def __init__(self, configs_root: Path) -> None:
        """Initialize loader with configs root directory.

        Args:
            configs_root: Path to configs/ directory.
        """
        self._configs_root = configs_root
        self._cache: dict[str, T] = {}

    def clear_cache(self) -> None:
        """Clear the configuration cache.

        Call after modifying config files during development/testing.
        """
        self._cache.clear()

    @abstractmethod
    def load(
        self,
        provider: str,
        entity: str,
        inline_overrides: dict[str, Any] | None = None,
    ) -> T:
        """Load merged config for provider/entity.

        Args:
            provider: Provider name (e.g., "chembl").
            entity: Entity name (e.g., "activity").
            inline_overrides: Optional inline overrides from pipeline config.

        Returns:
            Domain configuration object.
        """
        ...

    def _load_yaml(self, path: Path) -> dict[str, Any]:
        """Load YAML file, return empty dict if not exists.

        Args:
            path: Path to YAML file.

        Returns:
            Parsed YAML content or empty dict.
        """
        return _load_yaml_file(path)

    def _deep_merge_base(
        self,
        base: dict[str, Any],
        override: dict[str, Any],
        list_concat_keys: frozenset[str],
    ) -> dict[str, Any]:
        """Deep merge two dicts with configurable list handling.

        Args:
            base: Base configuration dict.
            override: Override configuration dict.
            list_concat_keys: Keys whose lists should concatenate (not override).

        Returns:
            Merged dict (new object, inputs unchanged).
        """
        result = copy.deepcopy(base)

        for key, override_value in override.items():
            if key not in result:
                result[key] = copy.deepcopy(override_value)
            elif isinstance(override_value, dict) and isinstance(result[key], dict):
                # Recursive merge for nested dicts
                result[key] = self._deep_merge_base(
                    result[key], override_value, list_concat_keys
                )
            elif (
                isinstance(override_value, list)
                and isinstance(result[key], list)
                and key in list_concat_keys
            ):
                # Concatenate lists for specified keys
                result[key] = self._merge_lists(result[key], override_value, key)
            else:
                # Scalar or other list: override wins
                result[key] = copy.deepcopy(override_value)

        return result

    def _merge_lists(
        self,
        base: list[Any],
        override: list[Any],
        key: str,
    ) -> list[Any]:
        """Merge two lists. Subclasses can override for custom behavior.

        Default behavior: concatenate and deduplicate strings.

        Args:
            base: Base list.
            override: Override list.
            key: The key name (for context).

        Returns:
            Merged list.
        """
        # Default: simple concatenation with deduplication for string lists
        if base and isinstance(base[0], str):
            seen: set[str] = set()
            result: list[str] = []
            for item in base + override:
                if item not in seen:
                    seen.add(item)
                    result.append(item)
            return result
        # Non-string lists: just concatenate
        return base + override


__all__ = ["BaseConfigLoader", "_load_yaml_file"]
