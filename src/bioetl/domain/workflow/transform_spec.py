"""Workflow transform execution identity helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json

from bioetl.domain.types import JsonDict
from bioetl.domain.workflow.config import TransformStepConfig

__all__ = [
    "WorkflowTransformSpec",
    "build_workflow_transform_fingerprint",
]


@dataclass(frozen=True, slots=True)
class WorkflowTransformSpec:
    """Stable execution identity for one declarative workflow transform step."""

    step_id: str
    transform_name: str
    depends_on: tuple[str, ...] = ()
    config: JsonDict | None = None

    @classmethod
    def from_step(cls, step: TransformStepConfig) -> WorkflowTransformSpec:
        """Build a transform spec from a workflow transform step config."""
        return cls(
            step_id=step.step_id,
            transform_name=step.transform_name,
            depends_on=step.depends_on,
            config=step.config,
        )

    @property
    def fingerprint(self) -> str:
        """Return a deterministic fingerprint for skip and resume decisions."""
        return build_workflow_transform_fingerprint(self)

    def to_fingerprint_payload(self) -> JsonDict:
        """Return the normalized payload that participates in fingerprinting."""
        return {
            "step_id": self.step_id,
            "transform_name": self.transform_name,
            "depends_on": list(self.depends_on),
            "config": _normalize_json_value(self.config or {}),
        }


def build_workflow_transform_fingerprint(spec: WorkflowTransformSpec) -> str:
    """Return a stable sha256 fingerprint for a workflow transform spec."""
    payload = json.dumps(
        spec.to_fingerprint_payload(),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _normalize_json_value(value: object) -> object:
    """Normalize JSON-compatible values without changing list ordering."""
    if isinstance(value, Mapping):
        return {
            str(key): _normalize_json_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, tuple):
        return [_normalize_json_value(item) for item in value]
    if isinstance(value, list):
        return [_normalize_json_value(item) for item in value]
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [_normalize_json_value(item) for item in value]
    return value
