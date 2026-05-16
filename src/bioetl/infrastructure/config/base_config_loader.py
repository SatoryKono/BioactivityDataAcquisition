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

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, TypeVar

import yaml

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.config_merge import config_merge

T = TypeVar("T")


def _load_yaml_file(
    path: Path,
) -> JsonDict:  # Any: YAML config has heterogeneous values
    """Load YAML file, returning empty dict if missing or empty.

    Returns:
        Dictionary of YAML config content, or empty dict if file missing or empty.
    """
    if not path.exists():
        return {}

    with open(path, encoding="utf-8") as f:
        content = yaml.safe_load(f)
        return content if content is not None else {}


class BaseConfigLoader[T](ABC):
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
        inline_overrides: JsonDict | None = None,  # Any: YAML config heterogeneous
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

    def _load_yaml(
        self, path: Path
    ) -> JsonDict:  # Any: YAML config has heterogeneous values
        """Load YAML file, return empty dict if not exists.

        Args:
            path: Path to YAML file.

        Returns:
            Parsed YAML content or empty dict.
        """
        return _load_yaml_file(path)

    def _deep_merge_base(
        self,
        base: JsonDict,  # Any: YAML config has heterogeneous values
        override: JsonDict,  # Any: YAML config has heterogeneous values
        list_concat_keys: frozenset[str],
    ) -> JsonDict:  # Any: YAML config has heterogeneous values
        """Deep merge two dicts with configurable list handling.

        Args:
            base: Base configuration dict.
            override: Override configuration dict.
            list_concat_keys: Keys whose lists should concatenate (not override).

        Returns:
            Merged dict (new object, inputs unchanged).
        """
        return config_merge(
            base,
            override,
            list_concat_keys=list_concat_keys,
            concat_list_merger=self._merge_lists,
        )

    def _merge_lists(
        self,
        base: list[Any],  # Any: YAML config has heterogeneous values
        override: list[Any],  # Any: YAML config has heterogeneous values
        key: str,
    ) -> list[Any]:  # Any: YAML config has heterogeneous values
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
            import itertools

            return list(dict.fromkeys(itertools.chain(base, override)))
        # Non-string lists: just concatenate
        return base + override


__all__ = ["BaseConfigLoader"]
