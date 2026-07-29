"""Docs-only executable-unit inventory."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import yaml


class RegistryEntry(Protocol):
    """Minimal canonical registry entry surface used by docs projection."""

    pipeline_name: str
    provider: str
    entity_type: str
    data_source_provider: str | None


@dataclass(frozen=True, slots=True)
class ExecutableUnit:
    """One canonical executable identity and its config owner."""

    kind: str
    unit_id: str
    config_path: Path
    provider: str | None = None
    entity: str | None = None
    aliases: tuple[str, ...] = ()
    source_mode: str = "configured"

    @property
    def typed_id(self) -> str:
        return f"{self.kind}:{self.unit_id}"


def _yaml(path: Path) -> dict[str, object]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected YAML mapping: {path}")
    return payload


def _canonical_registry_entries() -> tuple[RegistryEntry, ...]:
    """Load the composition-owned manifest without constructing a registry."""
    from bioetl.composition.factories.pipeline.registry_manifest import (
        PIPELINE_CONFIGS,
    )

    return tuple(PIPELINE_CONFIGS)


def _entity_configs(configs_root: Path) -> dict[str, Path]:
    configs: dict[str, Path] = {}
    for path in sorted((configs_root / "entities").glob("*/*.yaml")):
        if path.parent.name == "composite":
            continue
        payload = _yaml(path)
        pipeline = payload.get("pipeline")
        if not isinstance(pipeline, dict):
            raise ValueError(f"Missing pipeline mapping: {path}")
        name = pipeline.get("pipeline_name")
        if not isinstance(name, str) or not name:
            raise ValueError(f"Missing pipeline.pipeline_name: {path}")
        if name in configs:
            raise ValueError(f"Duplicate entity config pipeline identity: {name}")
        configs[name] = path
    return configs


def discover_units(
    configs_root: Path,
    *,
    registry_entries: tuple[RegistryEntry, ...] | None = None,
) -> tuple[ExecutableUnit, ...]:
    """Discover ordinary, composite, and workflow units deterministically."""
    units: list[ExecutableUnit] = []
    entity_configs = _entity_configs(configs_root)
    entries = (
        registry_entries
        if registry_entries is not None
        else _canonical_registry_entries()
    )
    registry_names = [entry.pipeline_name for entry in entries]
    if len(registry_names) != len(set(registry_names)):
        raise ValueError("Duplicate pipeline identity in composition registry")
    missing_configs = sorted(set(registry_names) - set(entity_configs))
    orphan_configs = sorted(set(entity_configs) - set(registry_names))
    if missing_configs or orphan_configs:
        raise ValueError(
            "Pipeline registry/config mismatch: "
            f"missing_configs={missing_configs}, orphan_configs={orphan_configs}"
        )
    for entry in sorted(entries, key=lambda item: item.pipeline_name):
        alias = entry.data_source_provider
        aliases = (
            (f"data-source:{alias}",)
            if alias is not None and alias != entry.provider
            else ()
        )
        units.append(
            ExecutableUnit(
                "pipeline",
                entry.pipeline_name,
                entity_configs[entry.pipeline_name],
                provider=entry.provider,
                entity=entry.entity_type,
                aliases=aliases,
            )
        )

    for path in sorted((configs_root / "composites").glob("*.yaml")):
        payload = _yaml(path)
        composite = payload.get("composite")
        if not isinstance(composite, dict):
            continue
        name = composite.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError(f"Missing composite.name: {path}")
        units.append(
            ExecutableUnit(
                "composite",
                name,
                path,
                provider="composite",
                entity=name.removeprefix("composite_"),
            )
        )

    for path in sorted((configs_root / "workflows").glob("*.yaml")):
        payload = _yaml(path)
        workflow = payload.get("workflow")
        if not isinstance(workflow, dict):
            raise ValueError(f"Missing workflow mapping: {path}")
        name = workflow.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError(f"Missing workflow.name: {path}")
        units.append(ExecutableUnit("workflow", name, path))

    ordered = tuple(sorted(units, key=lambda item: item.typed_id))
    typed_ids = [item.typed_id for item in ordered]
    if len(typed_ids) != len(set(typed_ids)):
        raise ValueError("Duplicate executable typed identity")
    aliases = [alias for item in ordered for alias in item.aliases]
    if len(aliases) != len(set(aliases)):
        raise ValueError("Executable aliases must resolve exactly once")
    return ordered
