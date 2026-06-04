"""Application service for querying persisted lineage graph fragments."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from bioetl.application.services.lineage.lineage_inspection_helpers import (
    collect_nodes_by_type,
    dedupe_relations,
    relation_for_edge,
    resolve_produced_nodes,
)
from bioetl.application.services.lineage.lineage_inspection_results import (
    LineageFragmentInspectionResult,
    LineageNodeRelationResult,
    LineageRunExplanationResult,
    LineageTraceResult,
)
from bioetl.domain.lineage import LineageGraphFragment, LineageNodeType
from bioetl.domain.ports import LineageStorePort, RunManifestPort
from bioetl.domain.types import RunID

__all__ = [
    "LineageFragmentInspectionResult",
    "LineageInspectionService",
    "LineageNodeRelationResult",
    "LineageRunExplanationResult",
    "LineageTraceResult",
]


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
        fragment = (
            self.lineage_store.get(fragment_id)
            if semantic
            else self.lineage_store.get_occurrence(fragment_id)
        )
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
                        relation_for_edge(
                            fragment=fragment,
                            edge_type=edge.edge_type.value,
                            node=node_index.get(edge.target.node_id, edge.target),
                        )
                    )
                if edge.target.node_id == dataset_ref:
                    downstream_relations.append(
                        relation_for_edge(
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
            upstream=dedupe_relations(upstream_relations),
            downstream=dedupe_relations(downstream_relations),
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
            produced_datasets=resolve_produced_nodes(
                fragments=fragments,
                node_type=LineageNodeType.DATASET,
            ),
            produced_bronze_batches=resolve_produced_nodes(
                fragments=fragments,
                node_type=LineageNodeType.BRONZE_BATCH,
            ),
            transforms=collect_nodes_by_type(
                fragments=fragments,
                node_type=LineageNodeType.TRANSFORM,
            ),
            source_systems=collect_nodes_by_type(
                fragments=fragments,
                node_type=LineageNodeType.SOURCE_SYSTEM,
            ),
            source_requests=collect_nodes_by_type(
                fragments=fragments,
                node_type=LineageNodeType.SOURCE_REQUEST,
            ),
            schemas=collect_nodes_by_type(
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
