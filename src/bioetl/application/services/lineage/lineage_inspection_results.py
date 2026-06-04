"""DTOs returned by lineage inspection services."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.lineage import LineageGraphFragment, LineageNodeRef


@dataclass(frozen=True, slots=True)
class LineageFragmentInspectionResult:
    """Resolved view for one persisted lineage graph fragment."""

    fragment: LineageGraphFragment

    def to_dict(self) -> dict[str, object]:
        """Return a JSON/YAML-safe CLI payload."""
        return {"fragment": self.fragment.to_dict()}


@dataclass(frozen=True, slots=True)
class LineageNodeRelationResult:
    """One upstream/downstream relation around a traced lineage node."""

    fragment_id: str
    stored_fragment_id: str | None
    edge_type: str
    node: LineageNodeRef

    def to_dict(self) -> dict[str, object]:
        """Return a JSON/YAML-safe CLI payload."""
        return {
            "fragment_id": self.fragment_id,
            "stored_fragment_id": self.stored_fragment_id,
            "edge_type": self.edge_type,
            "node": self.node.to_dict(),
        }


LineageNodeRelation = LineageNodeRelationResult


@dataclass(frozen=True, slots=True)
class LineageTraceResult:
    """Resolved immediate neighborhood around one dataset/node reference."""

    dataset_ref: str
    fragment_ids: tuple[str, ...]
    stored_fragment_ids: tuple[str, ...] = ()
    upstream: tuple[LineageNodeRelationResult, ...] = ()
    downstream: tuple[LineageNodeRelationResult, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return a JSON/YAML-safe CLI payload."""
        return {
            "dataset_ref": self.dataset_ref,
            "fragment_ids": list(self.fragment_ids),
            "stored_fragment_ids": list(self.stored_fragment_ids),
            "upstream": [relation.to_dict() for relation in self.upstream],
            "downstream": [relation.to_dict() for relation in self.downstream],
        }


@dataclass(frozen=True, slots=True)
class LineageRunExplanationResult:
    """Resolved lineage view for one manifest/run identifier."""

    identifier: str
    run_id: str | None
    manifest_id: str | None
    fragment_ids: tuple[str, ...]
    stored_fragment_ids: tuple[str, ...] = ()
    produced_datasets: tuple[LineageNodeRef, ...] = ()
    produced_bronze_batches: tuple[LineageNodeRef, ...] = ()
    transforms: tuple[LineageNodeRef, ...] = ()
    source_systems: tuple[LineageNodeRef, ...] = ()
    source_requests: tuple[LineageNodeRef, ...] = ()
    schemas: tuple[LineageNodeRef, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return a JSON/YAML-safe CLI payload."""
        return {
            "identifier": self.identifier,
            "run_id": self.run_id,
            "manifest_id": self.manifest_id,
            "fragment_ids": list(self.fragment_ids),
            "stored_fragment_ids": list(self.stored_fragment_ids),
            "produced_datasets": [node.to_dict() for node in self.produced_datasets],
            "produced_bronze_batches": [
                node.to_dict() for node in self.produced_bronze_batches
            ],
            "transforms": [node.to_dict() for node in self.transforms],
            "source_systems": [node.to_dict() for node in self.source_systems],
            "source_requests": [node.to_dict() for node in self.source_requests],
            "schemas": [node.to_dict() for node in self.schemas],
        }


__all__ = [
    "LineageFragmentInspectionResult",
    "LineageNodeRelation",
    "LineageNodeRelationResult",
    "LineageRunExplanationResult",
    "LineageTraceResult",
]
