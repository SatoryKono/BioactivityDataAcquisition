"""Registry-manifest validation against tracked config surfaces.

The pipeline registry manifest is the canonical composition-owned runtime
binding surface. Entity/provider YAML remains the canonical tracked config
surface. This module validates that the two remain in sync.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import cast

from bioetl.composition.factories.pipeline_support.registry_validation_helpers import (
    RegistryEntryProtocol,
    _iter_entity_files,
    _validate_entity_config_against_registry,
    _validate_registry_entry,
)
from bioetl.infrastructure.config.config_root import resolve_configs_root

__all__ = ["validate_registry_manifest"]


def validate_registry_manifest(
    *,
    configs_root: Path,
    pipeline_configs: Iterable[RegistryEntryProtocol] | None = None,
) -> list[str]:
    """Validate registry-manifest entries against tracked entity/provider configs.

    When ``pipeline_configs`` is omitted, the canonical in-tree
    ``PIPELINE_CONFIGS`` registry is used (backward-compatible for callers that
    only pass ``configs_root``).
    """
    resolved_configs_root = resolve_configs_root(configs_root)
    repo_root = resolved_configs_root.parent
    if pipeline_configs is None:
        # Import via public registry facade to keep family fan-in of
        # ``registry_manifest`` under the hotspot budget (ARCH-RES-01).
        from bioetl.composition.factories.pipeline.registry import (
            PIPELINE_CONFIGS,
        )

        # NamedTuple registry entries are structurally RegistryEntryProtocol;
        # cast keeps basedpyright from union-widening against the concrete type.
        registry_entries: Sequence[RegistryEntryProtocol] = cast(
            Sequence[RegistryEntryProtocol],
            tuple(PIPELINE_CONFIGS),
        )
    else:
        registry_entries = tuple(pipeline_configs)
    errors: list[str] = []

    seen_pipeline_names: set[str] = set()
    seen_provider_entities: set[tuple[str, str]] = set()
    registered_pipeline_names: set[str] = set()
    registered_provider_entities: set[tuple[str, str]] = set()

    for entry in registry_entries:
        errors.extend(
            _validate_registry_entry(
                entry,
                resolved_configs_root=resolved_configs_root,
                repo_root=repo_root,
                seen_pipeline_names=seen_pipeline_names,
                seen_provider_entities=seen_provider_entities,
                registered_pipeline_names=registered_pipeline_names,
                registered_provider_entities=registered_provider_entities,
            )
        )

    for entity_path in _iter_entity_files(resolved_configs_root):
        errors.extend(
            _validate_entity_config_against_registry(
                entity_path,
                repo_root=repo_root,
                registered_pipeline_names=registered_pipeline_names,
                registered_provider_entities=registered_provider_entities,
            )
        )

    return errors
