"""Workflow control-plane manifest models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from bioetl.domain.types import RunID

__all__ = ["WorkflowManifest", "WorkflowManifestStep"]


@dataclass(frozen=True, slots=True)
class WorkflowManifestStep:
    """Immutable description of one resolved workflow step."""

    step_id: str
    kind: str
    depends_on: tuple[str, ...] = ()
    pipeline_name: str | None = None
    transform_name: str | None = None
    run_options: dict[str, object] | None = None
    config: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable step payload."""
        return {
            "step_id": self.step_id,
            "kind": self.kind,
            "depends_on": list(self.depends_on),
            "pipeline_name": self.pipeline_name,
            "transform_name": self.transform_name,
            "run_options": dict(self.run_options or {}),
            "config": dict(self.config or {}),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> WorkflowManifestStep:
        """Hydrate a workflow manifest step from serialized payload."""
        return cls(
            step_id=str(payload["step_id"]),
            kind=str(payload["kind"]),
            depends_on=tuple(
                str(item) for item in _load_list(payload.get("depends_on"))
            ),
            pipeline_name=_load_optional_str(payload, "pipeline_name"),
            transform_name=_load_optional_str(payload, "transform_name"),
            run_options=_load_object_mapping(payload.get("run_options")),
            config=_load_object_mapping(payload.get("config")),
        )


@dataclass(frozen=True, slots=True)
class WorkflowManifest:
    """Immutable workflow execution-intent artifact."""

    manifest_id: str
    workflow_run_id: RunID
    execution_fingerprint: str
    schema_version: str
    created_at: datetime
    workflow_name: str
    workflow_version: str
    launch_context: dict[str, object]
    defaults: dict[str, object]
    selected_step_ids: tuple[str, ...]
    steps: tuple[WorkflowManifestStep, ...]
    resumed_from_manifest_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable manifest payload."""
        return {
            "manifest_id": self.manifest_id,
            "workflow_run_id": str(self.workflow_run_id),
            "execution_fingerprint": self.execution_fingerprint,
            "schema_version": self.schema_version,
            "created_at": self.created_at.isoformat(),
            "workflow_name": self.workflow_name,
            "workflow_version": self.workflow_version,
            "launch_context": dict(self.launch_context),
            "defaults": dict(self.defaults),
            "selected_step_ids": list(self.selected_step_ids),
            "steps": [step.to_dict() for step in self.steps],
            "resumed_from_manifest_id": self.resumed_from_manifest_id,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> WorkflowManifest:
        """Hydrate a workflow manifest from serialized payload."""
        return cls(
            manifest_id=str(payload["manifest_id"]),
            workflow_run_id=RunID(UUID(str(payload["workflow_run_id"]))),
            execution_fingerprint=str(payload["execution_fingerprint"]),
            schema_version=str(payload["schema_version"]),
            created_at=datetime.fromisoformat(str(payload["created_at"])),
            workflow_name=str(payload["workflow_name"]),
            workflow_version=str(payload["workflow_version"]),
            launch_context=_load_object_mapping(payload.get("launch_context")),
            defaults=_load_object_mapping(payload.get("defaults")),
            selected_step_ids=tuple(
                str(item) for item in _load_list(payload.get("selected_step_ids"))
            ),
            steps=tuple(
                WorkflowManifestStep.from_dict(item)
                for item in _load_list_of_dicts(payload.get("steps"))
            ),
            resumed_from_manifest_id=_load_optional_str(
                payload,
                "resumed_from_manifest_id",
            ),
        )


def _load_optional_str(payload: dict[str, object], key: str) -> str | None:
    value = payload.get(key)
    return None if value is None else str(value)


def _load_object_mapping(raw_mapping: object) -> dict[str, object]:
    if not isinstance(raw_mapping, dict):
        return {}
    return {str(key): value for key, value in raw_mapping.items()}


def _load_list(raw_value: object) -> list[object]:
    if not isinstance(raw_value, list):
        return []
    return list(raw_value)


def _load_list_of_dicts(raw_value: object) -> list[dict[str, object]]:
    return [
        {str(key): value for key, value in item.items()}
        for item in _load_list(raw_value)
        if isinstance(item, dict)
    ]
