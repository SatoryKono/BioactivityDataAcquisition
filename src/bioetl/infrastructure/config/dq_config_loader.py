"""DQ configuration loader with hierarchical merge."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bioetl.domain.config import DQConfig
from bioetl.domain.types import JsonDict
from bioetl.infrastructure.config_merge import ListMergeFn, config_merge
from bioetl.infrastructure.schemas.dq_config import DQConfigFile

from ._dq_config_layers import (
    load_defaults_layer as _load_defaults_layer_impl,
)
from ._dq_config_layers import (
    load_entity_layer as _load_entity_layer_impl,
)
from ._dq_config_layers import (
    load_provider_layer as _load_provider_layer_impl,
)
from ._dq_config_normalization import (
    normalize_to_file_format as _normalize_to_file_format_impl,
)
from ._dq_config_validation_merge import (
    merge_validation_lists as _merge_validation_lists_impl,
)
from ._dq_config_validation_merge import (
    merge_validation_lists_for_key as _merge_validation_lists_for_key_impl,
)
from ._dq_config_validation_merge import (
    resolve_list_merger as _resolve_list_merger_impl,
)
from .base_config_loader import _load_yaml_file


class DQConfigLoader:
    """Load and merge DQ configurations from base/provider/entity/inline layers."""

    def __init__(self, configs_root: Path, relaxed_dq: bool = False) -> None:
        self._configs_root = configs_root
        self._base_root = configs_root / "base"
        self._relaxed_dq = relaxed_dq
        self._cache: dict[str, DQConfig] = {}

    def _load_provider_layer(
        self,
        provider: str,
    ) -> JsonDict:  # Any: YAML DQ config has heterogeneous values
        """Load provider DQ layer from unified provider config."""
        return _load_provider_layer_impl(self._configs_root, provider, self._load_yaml)

    def _load_entity_layer(
        self,
        provider: str,
        entity: str,
    ) -> JsonDict:  # Any: YAML DQ config has heterogeneous values
        """Load entity DQ layer from unified entity config."""
        return _load_entity_layer_impl(
            self._configs_root, provider, entity, self._load_yaml
        )

    def _merge_hierarchy(
        self,
        provider: str,
        entity: str,
        inline_overrides: (
            JsonDict | None  # Any: YAML config has heterogeneous values
        ),  # Any: YAML DQ config has heterogeneous values
    ) -> JsonDict:  # Any: YAML DQ config has heterogeneous values
        """Build merged config from defaults → provider → entity → inline."""
        merged = self._load_defaults_layer()
        if not merged:
            raise FileNotFoundError(
                "Required DQ defaults file not found in configs/base/quality.yaml. "
                "Create defaults in this location."
            )

        layers = (
            self._load_provider_layer(provider),
            self._load_entity_layer(provider, entity),
            inline_overrides or {},
        )
        for layer in layers:
            if layer:
                merged = self._deep_merge(merged, layer)

        if self._relaxed_dq:
            merged = self._deep_merge(
                merged,
                {"thresholds": {"soft_fail": 0.99, "hard_fail": 1.0}},
            )
        return merged

    def _load_defaults_layer(
        self,
    ) -> JsonDict:  # Any: YAML DQ config has heterogeneous values
        """Load DQ defaults from consolidated base path."""
        return _load_defaults_layer_impl(self._base_root, self._load_yaml)

    def load(
        self,
        provider: str,
        entity: str,
        inline_overrides: (
            JsonDict | None  # Any: YAML config has heterogeneous values
        ) = None,  # Any: YAML DQ config has heterogeneous values
    ) -> DQConfig:
        """Load merged DQ config for provider/entity."""
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
        """Clear DQ configuration cache."""
        self._cache.clear()

    def _load_yaml(
        self,
        path: Path,
    ) -> JsonDict:  # Any: YAML DQ config has heterogeneous values
        """Load YAML file content via base config loader utility."""
        return _load_yaml_file(path)

    def _deep_merge(
        self,
        base: JsonDict,  # Any: YAML DQ config has heterogeneous values
        override: JsonDict,  # Any: YAML DQ config has heterogeneous values
    ) -> JsonDict:  # Any: YAML DQ config has heterogeneous values
        """Deep merge two dicts preserving DQ-specific validation list semantics."""
        return config_merge(
            base,
            override,
            list_merger_resolver=self._resolve_list_merger,
        )

    def _resolve_list_merger(self, key: str) -> ListMergeFn | None:
        """Resolve DQ list merge strategy for a given key."""
        return _resolve_list_merger_impl(
            key,
            merge_validation_lists_for_key=self._merge_validation_lists_for_key,
        )

    def _merge_validation_lists_for_key(
        self,
        base: list[Any],  # Any: YAML DQ validation items have heterogeneous types
        override: list[Any],  # Any: YAML DQ validation items have heterogeneous types
        _key: str,
    ) -> list[Any]:  # Any: YAML DQ validation items have heterogeneous types
        """Adapter for config_merge list strategy callback."""
        return _merge_validation_lists_for_key_impl(base, override, _key)

    def _merge_validation_lists(
        self,
        base: list[JsonDict],  # Any: YAML DQ config has heterogeneous values
        override: list[JsonDict],  # Any: YAML DQ config has heterogeneous values
    ) -> list[JsonDict]:  # Any: YAML DQ config has heterogeneous values
        """Merge validation lists, deduplicating by semantic key."""
        return _merge_validation_lists_impl(base, override)

    def _normalize_to_file_format(
        self,
        merged: JsonDict,  # Any: YAML DQ config has heterogeneous values
    ) -> JsonDict:  # Any: YAML DQ config has heterogeneous values
        """Normalize merged config to DQConfigFile-compatible shape."""
        return _normalize_to_file_format_impl(merged)


__all__ = ["DQConfigLoader"]
