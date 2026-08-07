"""Canonical lineage edge and fragment models."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from bioetl.domain.lineage._shared import (
    load_attributes,
    load_mapping,
    load_optional_datetime,
    load_optional_str,
    mapping_to_plain,
    normalize_mapping,
)
from bioetl.domain.lineage.refs import LineageNodeRef

__all__ = [
    "LineageEdge",
    "LineageEdgeType",
    "LineageGraphFragment",
]


def _load_node_refs(raw_nodes: object) -> tuple[LineageNodeRef, ...]:
    """Deserialize serialized node payloads into lineage node refs."""
    if not isinstance(raw_nodes, list):
        return ()
    return tuple(
        LineageNodeRef.from_dict(node) for node in raw_nodes if isinstance(node, dict)
    )


class LineageEdgeType(StrEnum):
    """Canonical lineage edge semantics."""

    DERIVED_FROM = "derived_from"
    PRODUCED_BY = "produced_by"
    USED_SCHEMA = "used_schema"
    EXECUTED_IN = "executed_in"
    CONSUMED_BY = "consumed_by"
    EXPLAINS = "explains"


@dataclass(frozen=True, slots=True)
class LineageEdge:
    """Directed canonical edge between two lineage nodes."""

    edge_type: LineageEdgeType
    source: LineageNodeRef
    target: LineageNodeRef
    run_id: str | None = None
    manifest_id: str | None = None
    created_at: datetime | None = None
    attributes: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Normalize edge attributes for deterministic storage."""
        object.__setattr__(self, "attributes", normalize_mapping(self.attributes))

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
            "attributes": mapping_to_plain(self.attributes),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> LineageEdge:
        """Hydrate edge from serialized payload."""
        return cls(
            edge_type=LineageEdgeType(str(payload["edge_type"])),
            source=LineageNodeRef.from_dict(load_mapping(payload.get("source"))),
            target=LineageNodeRef.from_dict(load_mapping(payload.get("target"))),
            run_id=load_optional_str(payload, "run_id"),
            manifest_id=load_optional_str(payload, "manifest_id"),
            created_at=load_optional_datetime(payload, "created_at"),
            attributes=load_attributes(payload.get("attributes")),
        )


def _load_edges(raw_edges: object) -> tuple[LineageEdge, ...]:
    """Deserialize serialized edge payloads into lineage edges."""
    if not isinstance(raw_edges, list):
        return ()
    return tuple(
        LineageEdge.from_dict(edge) for edge in raw_edges if isinstance(edge, dict)
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
    stored_fragment_id: str | None = field(default=None, compare=False)

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
            "stored_fragment_id": self.stored_fragment_id,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> LineageGraphFragment:
        """Hydrate fragment from serialized payload."""
        return cls(
            fragment_id=str(payload["fragment_id"]),
            nodes=_load_node_refs(payload.get("nodes")),
            edges=_load_edges(payload.get("edges")),
            run_id=load_optional_str(payload, "run_id"),
            manifest_id=load_optional_str(payload, "manifest_id"),
            created_at=load_optional_datetime(payload, "created_at"),
            stored_fragment_id=load_optional_str(payload, "stored_fragment_id"),
        )
