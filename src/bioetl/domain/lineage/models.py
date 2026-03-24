"""Canonical lineage models used for end-to-end traceability."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import StrEnum

from bioetl.domain.medallion import Layer

__all__ = [
    "DatasetRef",
    "LineageEdge",
    "LineageEdgeType",
    "LineageGraphFragment",
    "LineageNodeRef",
    "LineageNodeType",
    "SchemaRef",
    "TransformRef",
]


def _normalize_mapping(values: dict[str, object]) -> dict[str, object]:
    """Return a detached shallow copy of attribute mappings."""
    return {str(key): value for key, value in values.items()}


def _optional_str(payload: dict[str, object], key: str) -> str | None:
    """Return string field when present, otherwise None."""
    value = payload.get(key)
    return None if value is None else str(value)


def _optional_datetime(payload: dict[str, object], key: str) -> datetime | None:
    """Return parsed datetime field when present, otherwise None."""
    value = payload.get(key)
    return None if value is None else datetime.fromisoformat(str(value))


def _load_attributes(raw_attributes: object) -> dict[str, object]:
    """Return normalized attributes payload from serialized object."""
    if not isinstance(raw_attributes, dict):
        return {}
    return {str(key): value for key, value in raw_attributes.items()}


def _load_mapping(raw_mapping: object) -> dict[str, object]:
    """Return normalized mapping payload from serialized object."""
    if not isinstance(raw_mapping, dict):
        return {}
    return {str(key): value for key, value in raw_mapping.items()}


def _optional_version(payload: dict[str, object], key: str) -> int | str | None:
    """Return dataset version when present and representable."""
    value = payload.get(key)
    return value if isinstance(value, (int, str)) else None


def _optional_int(payload: dict[str, object], key: str) -> int | None:
    """Return integer field when present, otherwise None."""
    value = payload.get(key)
    return None if value is None else int(str(value))


def _load_node_refs(raw_nodes: object) -> tuple[LineageNodeRef, ...]:
    """Deserialize serialized node payloads into lineage node refs."""
    if not isinstance(raw_nodes, list):
        return ()
    return tuple(
        LineageNodeRef.from_dict(node) for node in raw_nodes if isinstance(node, dict)
    )


def _load_edges(raw_edges: object) -> tuple[LineageEdge, ...]:
    """Deserialize serialized edge payloads into lineage edges."""
    if not isinstance(raw_edges, list):
        return ()
    return tuple(
        LineageEdge.from_dict(edge) for edge in raw_edges if isinstance(edge, dict)
    )


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


class LineageEdgeType(StrEnum):
    """Canonical lineage edge semantics."""

    DERIVED_FROM = "derived_from"
    PRODUCED_BY = "produced_by"
    USED_SCHEMA = "used_schema"
    EXECUTED_IN = "executed_in"
    CONSUMED_BY = "consumed_by"
    EXPLAINS = "explains"


@dataclass(frozen=True, slots=True)
class LineageNodeRef:
    """Canonical reference to one lineage graph node."""

    node_type: LineageNodeType
    node_id: str
    label: str | None = None
    attributes: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Normalize input values for deterministic storage."""
        object.__setattr__(self, "attributes", _normalize_mapping(self.attributes))

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe node payload."""
        return {
            "node_type": self.node_type.value,
            "node_id": self.node_id,
            "label": self.label,
            "attributes": dict(self.attributes),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> LineageNodeRef:
        """Hydrate node reference from serialized payload."""
        raw_attributes = payload.get("attributes", {})
        return cls(
            node_type=LineageNodeType(str(payload["node_type"])),
            node_id=str(payload["node_id"]),
            label=(None if payload.get("label") is None else str(payload.get("label"))),
            attributes=(
                {}
                if not isinstance(raw_attributes, dict)
                else {str(key): value for key, value in raw_attributes.items()}
            ),
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
        """Return canonical dataset node identifier."""
        version_part = f"@{self.version}" if self.version is not None else ""
        return f"{self.layer}:{self.logical_name}{version_part}"

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
            version=_optional_version(payload, "version"),
            provider=_optional_str(payload, "provider"),
            entity=_optional_str(payload, "entity"),
            path=_optional_str(payload, "path"),
            manifest_id=_optional_str(payload, "manifest_id"),
            run_id=_optional_str(payload, "run_id"),
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
        return f"transform:{pipeline}:{self.name}:{version}:{step_index}"

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
            version=(
                None if payload.get("version") is None else str(payload["version"])
            ),
            step_index=_optional_int(payload, "step_index"),
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
        return f"schema:{self.contract_path}:{version}"

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
            version=(
                None if payload.get("version") is None else str(payload["version"])
            ),
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


@dataclass(frozen=True, slots=True)
class LineageEdge:
    """Directed canonical edge between two lineage nodes."""

    edge_type: LineageEdgeType
    source: LineageNodeRef
    target: LineageNodeRef
    run_id: str | None = None
    manifest_id: str | None = None
    created_at: datetime | None = None
    attributes: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Normalize edge attributes for deterministic storage."""
        object.__setattr__(self, "attributes", _normalize_mapping(self.attributes))

    def to_dict(self) -> dict[str, object]:
        """Return JSON-safe edge payload."""
        return {
            "edge_type": self.edge_type.value,
            "source": self.source.to_dict(),
            "target": self.target.to_dict(),
            "run_id": self.run_id,
            "manifest_id": self.manifest_id,
            "created_at": (
                self.created_at.isoformat() if self.created_at is not None else None
            ),
            "attributes": dict(self.attributes),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> LineageEdge:
        """Hydrate edge from serialized payload."""
        return cls(
            edge_type=LineageEdgeType(str(payload["edge_type"])),
            source=LineageNodeRef.from_dict(_load_mapping(payload.get("source"))),
            target=LineageNodeRef.from_dict(_load_mapping(payload.get("target"))),
            run_id=_optional_str(payload, "run_id"),
            manifest_id=_optional_str(payload, "manifest_id"),
            created_at=_optional_datetime(payload, "created_at"),
            attributes=_load_attributes(payload.get("attributes")),
        )


@dataclass(frozen=True, slots=True)
class LineageGraphFragment:
    """One appendable lineage graph fragment anchored to a run/manifest."""

    fragment_id: str
    nodes: tuple[LineageNodeRef, ...] = ()
    edges: tuple[LineageEdge, ...] = ()
    run_id: str | None = None
    manifest_id: str | None = None
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        """Normalize list inputs to tuples for immutability."""
        object.__setattr__(self, "nodes", tuple(self.nodes))
        object.__setattr__(self, "edges", tuple(self.edges))

    def to_dict(self) -> dict[str, object]:
        """Return JSON-safe fragment payload."""
        return {
            "fragment_id": self.fragment_id,
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "run_id": self.run_id,
            "manifest_id": self.manifest_id,
            "created_at": (
                self.created_at.isoformat() if self.created_at is not None else None
            ),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> LineageGraphFragment:
        """Hydrate fragment from serialized payload."""
        return cls(
            fragment_id=str(payload["fragment_id"]),
            nodes=_load_node_refs(payload.get("nodes")),
            edges=_load_edges(payload.get("edges")),
            run_id=_optional_str(payload, "run_id"),
            manifest_id=_optional_str(payload, "manifest_id"),
            created_at=_optional_datetime(payload, "created_at"),
        )
