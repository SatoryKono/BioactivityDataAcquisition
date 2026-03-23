"""Retained convenience loader for hierarchical DQ config resolution."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bioetl.domain.config import DQConfig
from bioetl.domain.types import JsonDict
from bioetl.infrastructure.config.dq_config_resolution import (
    build_dq_cache_key,
    map_dq_config,
    run_dq_config_flow,
    validate_dq_config_payload,
)
from bioetl.infrastructure.config_merge import ListMergeFn, config_merge

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
    """Retained convenience facade for cached hierarchical DQ config loading."""

    def __init__(self, configs_root: Path, relaxed_dq: bool = False) -> None:
        """Initialize DQ config loader with root path and relaxed mode flag.

        Args:
            configs_root: Root directory containing ``base/``, ``providers/``,
                and ``entities/`` subdirectories.
            relaxed_dq: When True, merge a relaxed threshold override
                (soft_fail=0.99, hard_fail=1.0) into every loaded config.
        """
        self._configs_root = configs_root
        self._base_root = configs_root / "base"
        self._relaxed_dq = relaxed_dq
        self._cache: dict[str, DQConfig] = {}

    def _load_provider_layer(
        self,
        provider: str,
    ) -> JsonDict:  # Any: YAML DQ config has heterogeneous values
        """Load provider DQ layer from unified provider config.

        Args:
            provider: Provider name matching the YAML filename under
                ``configs/providers/`` (e.g., ``"chembl"``).

        Returns:
            Dictionary with provider-level DQ config, or empty dict if absent.
        """
        return _load_provider_layer_impl(self._configs_root, provider, self._load_yaml)

    def _load_entity_layer(
        self,
        provider: str,
        entity: str,
    ) -> JsonDict:  # Any: YAML DQ config has heterogeneous values
        """Load entity DQ layer from unified entity config.

        Args:
            provider: Provider name (e.g., ``"chembl"``).
            entity: Entity type name matching the YAML file under
                ``configs/entities/{provider}/`` (e.g., ``"activity"``).

        Returns:
            Dictionary with entity-level DQ config, or empty dict if absent.
        """
        return _load_entity_layer_impl(
            self._configs_root, provider, entity, self._load_yaml
        )

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
        """Load merged DQ config for provider/entity.

        Args:
            provider: Provider name (e.g., ``"chembl"``).
            entity: Entity type name (e.g., ``"activity"``).
            inline_overrides: Optional per-call overrides applied on top of the
                layered config; bypasses cache when provided.

        Returns:
            Validated and merged DQConfig domain object.
        """
        cache_key = build_dq_cache_key(
            provider,
            entity,
            relaxed_dq=self._relaxed_dq,
        )
        if inline_overrides is None and cache_key in self._cache:
            return self._cache[cache_key]

        domain_config = run_dq_config_flow(
            provider,
            entity,
            inline_overrides=inline_overrides,
            load_defaults_layer=self._load_defaults_layer,
            load_provider_layer=self._load_provider_layer,
            load_entity_layer=self._load_entity_layer,
            deep_merge=self._deep_merge,
            normalize_payload=self._normalize_to_file_format,
            validate_payload=validate_dq_config_payload,
            map_config=map_dq_config,
            relaxed_dq=self._relaxed_dq,
        )

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
        """Load YAML file content via base config loader utility.

        Args:
            path: Absolute path to the YAML file to load.

        Returns:
            Parsed YAML content as a dictionary, or empty dict if file is missing.
        """
        return _load_yaml_file(path)

    def _deep_merge(
        self,
        base: JsonDict,  # Any: YAML DQ config has heterogeneous values
        override: JsonDict,  # Any: YAML DQ config has heterogeneous values
    ) -> JsonDict:  # Any: YAML DQ config has heterogeneous values
        """Deep merge two dicts preserving DQ-specific validation list semantics.

        Args:
            base: Base configuration dictionary to merge into.
            override: Override dictionary whose values take precedence.

        Returns:
            New deeply merged dictionary with DQ list semantics applied.
        """
        return config_merge(
            base,
            override,
            list_merger_resolver=self._resolve_list_merger,
        )

    def _resolve_list_merger(self, key: str) -> ListMergeFn | None:
        """Resolve DQ list merge strategy for a given key.

        Args:
            key: Config key name being merged (e.g., ``"field_validations"``).

        Returns:
            ListMergeFn callable for validation list keys, or None for scalar merge.
        """
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
        """Adapter for config_merge list strategy callback.

        Args:
            base: Base validation list from lower-priority config layer.
            override: Override validation list from higher-priority config layer.
            _key: Config key name (passed by config_merge but unused here).

        Returns:
            Merged validation list with semantic deduplication applied.
        """
        return _merge_validation_lists_for_key_impl(base, override, _key)

    def _merge_validation_lists(
        self,
        base: list[JsonDict],  # Any: YAML DQ config has heterogeneous values
        override: list[JsonDict],  # Any: YAML DQ config has heterogeneous values
    ) -> list[JsonDict]:  # Any: YAML DQ config has heterogeneous values
        """Merge validation lists, deduplicating by semantic key.

        Args:
            base: Base list of validation rule dicts from lower-priority config.
            override: Override list of validation rule dicts; rules with matching
                semantic keys replace base entries.

        Returns:
            Merged list of validation rule dicts with duplicates resolved.
        """
        return _merge_validation_lists_impl(base, override)

    def _normalize_to_file_format(
        self,
        merged: JsonDict,  # Any: YAML DQ config has heterogeneous values
    ) -> JsonDict:  # Any: YAML DQ config has heterogeneous values
        """Normalize merged config to DQConfigFile-compatible shape.

        Args:
            merged: Raw merged DQ config dict prior to Pydantic validation.

        Returns:
            Normalized dictionary ready for DQConfigFile.model_validate().
        """
        return _normalize_to_file_format_impl(merged)


__all__ = ["DQConfigLoader"]
