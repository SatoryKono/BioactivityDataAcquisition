"""Docs-only executable-unit inventory."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True, slots=True)
class ExecutableUnit:
    """One canonical executable identity and its config owner."""

    kind: str
    unit_id: str
    config_path: Path

    @property
    def typed_id(self) -> str:
        return f"{self.kind}:{self.unit_id}"


def _yaml(path: Path) -> dict[str, object]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected YAML mapping: {path}")
    return payload


def discover_units(configs_root: Path) -> tuple[ExecutableUnit, ...]:
    """Discover ordinary, composite, and workflow units deterministically."""
    units: list[ExecutableUnit] = []
    entities = configs_root / "entities"
    for path in sorted(entities.glob("*/*.yaml")):
        if path.parent.name == "composite":
            continue
        payload = _yaml(path)
        pipeline = payload.get("pipeline")
        if not isinstance(pipeline, dict):
            raise ValueError(f"Missing pipeline mapping: {path}")
        pipeline_name = pipeline.get("pipeline_name")
        if not isinstance(pipeline_name, str) or not pipeline_name:
            raise ValueError(f"Missing pipeline.pipeline_name: {path}")
        units.append(ExecutableUnit("pipeline", pipeline_name, path))

    for path in sorted((configs_root / "composites").glob("*.yaml")):
        payload = _yaml(path)
        composite = payload.get("composite")
        if not isinstance(composite, dict):
            continue
        name = composite.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError(f"Missing composite.name: {path}")
        units.append(ExecutableUnit("composite", name, path))

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
    return ordered
