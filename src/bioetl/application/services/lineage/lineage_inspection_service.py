"""Application service for querying persisted lineage graph fragments."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from bioetl.domain.lineage import (
    LineageEdgeType,
    LineageGraphFragment,
    LineageNodeRef,
    LineageNodeType,
)
from bioetl.domain.ports import LineageStorePort, RunManifestPort
from bioetl.domain.types import RunID

__all__ = [
    "LineageFragmentInspectionResult",
    "LineageInspectionService",
    "LineageNodeRelationResult",
    "LineageRunExplanationResult",
    "LineageTraceResult",
]


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


def _dedupe_nodes(nodes: list[LineageNodeRef]) -> tuple[LineageNodeRef, ...]:
    """Deduplicate nodes by canonical identifier while preserving order."""
    unique: dict[str, LineageNodeRef] = {}
    for node in nodes:
        unique.setdefault(node.node_id, node)
    return tuple(unique.values())


def _dedupe_relations(
    relations: list[LineageNodeRelationResult],
) -> tuple[LineageNodeRelationResult, ...]:
    """Deduplicate relations by fragment, edge semantics, and related node id."""
    unique: dict[tuple[str, str, str, str | None], LineageNodeRelationResult] = {}
    for relation in relations:
        key = (
            relation.fragment_id,
            relation.edge_type,
            relation.node.node_id,
            relation.stored_fragment_id,
        )
        unique.setdefault(key, relation)
    return tuple(unique.values())


def _relation_for_edge(
    *,
    fragment: LineageGraphFragment,
    edge_type: str,
    node: LineageNodeRef,
) -> LineageNodeRelationResult:
    """Build one canonical relation payload for trace results."""
    return LineageNodeRelationResult(
        fragment_id=fragment.fragment_id,
        stored_fragment_id=fragment.stored_fragment_id,
        edge_type=edge_type,
        node=node,
    )


def _collect_nodes_by_type(
    *,
    fragments: tuple[LineageGraphFragment, ...],
    node_type: LineageNodeType,
) -> tuple[LineageNodeRef, ...]:
    """Collect nodes of one type across all fragments."""
    return _dedupe_nodes(
        [
            node
            for fragment in fragments
            for node in fragment.nodes
            if node.node_type is node_type
        ]
    )


def _resolve_produced_nodes(
    *,
    fragments: tuple[LineageGraphFragment, ...],
    node_type: LineageNodeType,
) -> tuple[LineageNodeRef, ...]:
    """Collect produced output nodes of one type across all fragments."""
    nodes: list[LineageNodeRef] = []
    for fragment in fragments:
        node_index = {node.node_id: node for node in fragment.nodes}
        for edge in fragment.edges:
            if edge.edge_type is not LineageEdgeType.PRODUCED_BY:
                continue
            node = node_index.get(edge.source.node_id, edge.source)
            if node.node_type is node_type:
                nodes.append(node)
    return _dedupe_nodes(nodes)


@dataclass(slots=True)
class LineageInspectionService:
    """Resolve stored lineage fragments into CLI-facing traceability views."""

    lineage_store: LineageStorePort
    manifest_port: RunManifestPort | None = None

    def show_fragment(
        self,
        fragment_id: str,
        *,
        semantic: bool = False,
    ) -> LineageFragmentInspectionResult:
        """Resolve one lineage fragment by occurrence id by default."""
        if semantic:
            fragment = self.lineage_store.get(fragment_id)
        else:
            get_occurrence = getattr(
                self.lineage_store,
                "get_occurrence",
                self.lineage_store.get,
            )
            fragment = get_occurrence(fragment_id)
        if fragment is None:
            raise ValueError(
                f"Lineage fragment not found for identifier: {fragment_id}"
            )
        return LineageFragmentInspectionResult(fragment=fragment)

    def trace(self, dataset_ref: str) -> LineageTraceResult:
        """Trace immediate upstream and downstream relations for one node id."""
        fragments = tuple(self.lineage_store.list_by_node_id(dataset_ref))
        if not fragments:
            raise ValueError(f"Lineage trace not found for dataset ref: {dataset_ref}")

        upstream_relations: list[LineageNodeRelationResult] = []
        downstream_relations: list[LineageNodeRelationResult] = []
        for fragment in fragments:
            node_index = {node.node_id: node for node in fragment.nodes}
            for edge in fragment.edges:
                if edge.source.node_id == dataset_ref:
                    upstream_relations.append(
                        _relation_for_edge(
                            fragment=fragment,
                            edge_type=edge.edge_type.value,
                            node=node_index.get(edge.target.node_id, edge.target),
                        )
                    )
                if edge.target.node_id == dataset_ref:
                    downstream_relations.append(
                        _relation_for_edge(
                            fragment=fragment,
                            edge_type=edge.edge_type.value,
                            node=node_index.get(edge.source.node_id, edge.source),
                        )
                    )

        return LineageTraceResult(
            dataset_ref=dataset_ref,
            fragment_ids=tuple(fragment.fragment_id for fragment in fragments),
            stored_fragment_ids=tuple(
                fragment.stored_fragment_id or fragment.fragment_id
                for fragment in fragments
            ),
            upstream=_dedupe_relations(upstream_relations),
            downstream=_dedupe_relations(downstream_relations),
        )

    def explain_run(self, identifier: str) -> LineageRunExplanationResult:
        """Resolve lineage fragments associated with one manifest_id or run_id."""
        manifest_id, run_id, fragments = self._resolve_fragments(identifier)
        return LineageRunExplanationResult(
            identifier=identifier,
            run_id=run_id,
            manifest_id=manifest_id,
            fragment_ids=tuple(fragment.fragment_id for fragment in fragments),
            stored_fragment_ids=tuple(
                fragment.stored_fragment_id or fragment.fragment_id
                for fragment in fragments
            ),
            produced_datasets=_resolve_produced_nodes(
                fragments=fragments,
                node_type=LineageNodeType.DATASET,
            ),
            produced_bronze_batches=_resolve_produced_nodes(
                fragments=fragments,
                node_type=LineageNodeType.BRONZE_BATCH,
            ),
            transforms=_collect_nodes_by_type(
                fragments=fragments,
                node_type=LineageNodeType.TRANSFORM,
            ),
            source_systems=_collect_nodes_by_type(
                fragments=fragments,
                node_type=LineageNodeType.SOURCE_SYSTEM,
            ),
            source_requests=_collect_nodes_by_type(
                fragments=fragments,
                node_type=LineageNodeType.SOURCE_REQUEST,
            ),
            schemas=_collect_nodes_by_type(
                fragments=fragments,
                node_type=LineageNodeType.SCHEMA,
            ),
        )

    def _resolve_via_manifest(
        self,
        identifier: str,
    ) -> tuple[str | None, str | None, tuple[LineageGraphFragment, ...]] | None:
        """Resolve fragments through manifest lookups when manifest storage exists."""
        if self.manifest_port is None:
            return None
        manifest = self.manifest_port.get(identifier)
        if manifest is not None:
            manifest_id = manifest.manifest_id
            run_id = str(manifest.run_id)
            manifest_fragments = tuple(
                self.lineage_store.list_by_manifest_id(manifest_id)
            )
            if manifest_fragments:
                return manifest_id, run_id, manifest_fragments
            run_fragments = tuple(self.lineage_store.list_by_run_id(manifest.run_id))
            if run_fragments:
                return manifest_id, run_id, run_fragments
        parsed_run_id = self._parse_run_id(identifier)
        if parsed_run_id is None:
            return None
        manifest = self.manifest_port.get_by_run_id(parsed_run_id)
        if manifest is None:
            return None
        manifest_id = manifest.manifest_id
        fragments = tuple(self.lineage_store.list_by_manifest_id(manifest_id))
        if not fragments:
            return None
        return manifest_id, str(manifest.run_id), fragments

    def _resolve_via_direct_indexes(
        self,
        identifier: str,
    ) -> tuple[str | None, str | None, tuple[LineageGraphFragment, ...]] | None:
        """Resolve fragments directly from manifest/run indexes."""
        manifest_fragments = tuple(self.lineage_store.list_by_manifest_id(identifier))
        if manifest_fragments:
            return identifier, None, manifest_fragments
        parsed_run_id = self._parse_run_id(identifier)
        if parsed_run_id is None:
            return None
        run_fragments = tuple(self.lineage_store.list_by_run_id(parsed_run_id))
        if not run_fragments:
            return None
        return None, str(parsed_run_id), run_fragments

    def _resolve_fragments(
        self,
        identifier: str,
    ) -> tuple[str | None, str | None, tuple[LineageGraphFragment, ...]]:
        """Resolve manifest/run identifiers into stored lineage fragments."""
        manifest_resolution = self._resolve_via_manifest(identifier)
        if manifest_resolution is not None:
            return manifest_resolution
        direct_resolution = self._resolve_via_direct_indexes(identifier)
        if direct_resolution is not None:
            return direct_resolution
        raise ValueError(
            f"Lineage run explanation not found for identifier: {identifier}"
        )

    @staticmethod
    def _parse_run_id(identifier: str) -> RunID | None:
        """Parse UUID-like run identifiers safely."""
        try:
            return RunID(UUID(identifier))
        except (TypeError, ValueError):
            return None
