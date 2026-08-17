"""Canonical lineage node and reference models."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from enum import StrEnum

from bioetl.domain.lineage._shared import (
    load_optional_int,
    load_optional_str,
    load_optional_version,
    mapping_to_plain,
    normalize_mapping,
)
from bioetl.domain.medallion import Layer

__all__ = [
    "DatasetRef",
    "LineageNodeRef",
    "LineageNodeType",
    "SchemaRef",
    "TransformRef",
]


def _node_id_segment(value: str) -> str:
    """Encode a node-id segment so ``:`` / ``@`` cannot collide with delimiters."""
    return value.replace("%", "%25").replace(":", "%3A").replace("@", "%40")


class LineageNodeType(StrEnum):
    """Canonical node types for lineage graph fragments."""

    SOURCE_SYSTEM = "source_system"
    SOURCE_REQUEST = "source_request"
    BRONZE_BATCH = "bronze_batch"
    DATASET = "dataset"
    TRANSFORM = "transform"
    SCHEMA = "schema"
    RUN = "run"
    MANIFEST = "manifest"
    CONSUMPTION = "consumption"


@dataclass(frozen=True, slots=True)
class LineageNodeRef:
    """Canonical reference to one lineage graph node."""

    node_type: LineageNodeType
    node_id: str
    label: str | None = None
    attributes: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Normalize input values for deterministic storage."""
        object.__setattr__(self, "attributes", normalize_mapping(self.attributes))

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe node payload."""
        return {
            "node_type": self.node_type.value,
            "node_id": self.node_id,
            "label": self.label,
            "attributes": mapping_to_plain(self.attributes),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> LineageNodeRef:
        """Hydrate node reference from serialized payload."""
        raw_attributes = payload.get("attributes", {})
        attributes = (
            {}
            if not isinstance(raw_attributes, dict)
            else {str(key): value for key, value in raw_attributes.items()}
        )
        return cls(
            node_type=LineageNodeType(str(payload["node_type"])),
            node_id=str(payload["node_id"]),
            label=None if payload.get("label") is None else str(payload.get("label")),
            attributes=attributes,
        )


@dataclass(frozen=True, slots=True)
class DatasetRef:
    """Logical dataset reference used by Bronze/Silver/Gold lineage."""

    layer: Layer | str
    logical_name: str
    version: int | str | None = None
    provider: str | None = None
    entity: str | None = None
    path: str | None = None
    manifest_id: str | None = None
    run_id: str | None = None

    def __post_init__(self) -> None:
        """Normalize layer enum to stable string value."""
        if isinstance(self.layer, Layer):
            object.__setattr__(self, "layer", self.layer.value)

    @property
    def node_id(self) -> str:
        """Return canonical dataset node identifier.

        ``logical_name`` and ``version`` are percent-encoded for ``:`` / ``@`` so a
        name that embeds the version delimiter cannot collide with an explicit
        versioned reference (e.g. ``foo@1`` vs logical ``foo`` + version ``1``).
        """
        name = _node_id_segment(str(self.logical_name))
        if self.version is None:
            return f"{self.layer}:{name}"
        return f"{self.layer}:{name}@{_node_id_segment(str(self.version))}"

    def to_node_ref(self) -> LineageNodeRef:
        """Convert dataset reference into generic lineage node."""
        return LineageNodeRef(
            node_type=LineageNodeType.DATASET,
            node_id=self.node_id,
            label=self.logical_name,
            attributes={
                "layer": str(self.layer),
                "logical_name": self.logical_name,
                "version": self.version,
                "provider": self.provider,
                "entity": self.entity,
                "path": self.path,
                "manifest_id": self.manifest_id,
                "run_id": self.run_id,
            },
        )

    def to_dict(self) -> dict[str, object]:
        """Return JSON-safe dataset payload."""
        return {
            "layer": str(self.layer),
            "logical_name": self.logical_name,
            "version": self.version,
            "provider": self.provider,
            "entity": self.entity,
            "path": self.path,
            "manifest_id": self.manifest_id,
            "run_id": self.run_id,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> DatasetRef:
        """Hydrate dataset reference from serialized payload."""
        return cls(
            layer=str(payload["layer"]),
            logical_name=str(payload["logical_name"]),
            version=load_optional_version(payload, "version"),
            provider=load_optional_str(payload, "provider"),
            entity=load_optional_str(payload, "entity"),
            path=load_optional_str(payload, "path"),
            manifest_id=load_optional_str(payload, "manifest_id"),
            run_id=load_optional_str(payload, "run_id"),
        )


@dataclass(frozen=True, slots=True)
class TransformRef:
    """Reference to one transform stage in a lineage graph."""

    name: str
    version: str | None = None
    step_index: int | None = None
    pipeline_name: str | None = None
    code_ref: str | None = None

    @property
    def node_id(self) -> str:
        """Return canonical transform node identifier."""
        pipeline = self.pipeline_name or "unknown_pipeline"
        version = self.version or "unknown_version"
        step_index = self.step_index if self.step_index is not None else "na"
        return (
            "transform:"
            f"{_node_id_segment(pipeline)}:"
            f"{_node_id_segment(self.name)}:"
            f"{_node_id_segment(version)}:"
            f"{_node_id_segment(str(step_index))}"
        )

    def to_node_ref(self) -> LineageNodeRef:
        """Convert transform reference into generic lineage node."""
        return LineageNodeRef(
            node_type=LineageNodeType.TRANSFORM,
            node_id=self.node_id,
            label=self.name,
            attributes={
                "name": self.name,
                "version": self.version,
                "step_index": self.step_index,
                "pipeline_name": self.pipeline_name,
                "code_ref": self.code_ref,
            },
        )

    def to_dict(self) -> dict[str, object]:
        """Return JSON-safe transform payload."""
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> TransformRef:
        """Hydrate transform reference from serialized payload."""
        return cls(
            name=str(payload["name"]),
            version=None if payload.get("version") is None else str(payload["version"]),
            step_index=load_optional_int(payload, "step_index"),
            pipeline_name=(
                None
                if payload.get("pipeline_name") is None
                else str(payload["pipeline_name"])
            ),
            code_ref=(
                None if payload.get("code_ref") is None else str(payload["code_ref"])
            ),
        )


@dataclass(frozen=True, slots=True)
class SchemaRef:
    """Reference to schema/contract version used in lineage."""

    contract_path: str
    version: str | None = None
    validation_mode: str | None = None
    dataset_name: str | None = None

    @property
    def node_id(self) -> str:
        """Return canonical schema node identifier."""
        version = self.version or "unknown_version"
        return (
            f"schema:{_node_id_segment(self.contract_path)}:"
            f"{_node_id_segment(version)}"
        )

    def to_node_ref(self) -> LineageNodeRef:
        """Convert schema reference into generic lineage node."""
        return LineageNodeRef(
            node_type=LineageNodeType.SCHEMA,
            node_id=self.node_id,
            label=self.dataset_name or self.contract_path,
            attributes={
                "contract_path": self.contract_path,
                "version": self.version,
                "validation_mode": self.validation_mode,
                "dataset_name": self.dataset_name,
            },
        )

    def to_dict(self) -> dict[str, object]:
        """Return JSON-safe schema payload."""
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> SchemaRef:
        """Hydrate schema reference from serialized payload."""
        return cls(
            contract_path=str(payload["contract_path"]),
            version=None if payload.get("version") is None else str(payload["version"]),
            validation_mode=(
                None
                if payload.get("validation_mode") is None
                else str(payload["validation_mode"])
            ),
            dataset_name=(
                None
                if payload.get("dataset_name") is None
                else str(payload["dataset_name"])
            ),
        )
