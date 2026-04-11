"""Application-level bundle for metadata sidecars and lineage fragments."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, TypeVar

from bioetl.domain.lineage import LineageEdgeType, LineageNodeType
from bioetl.domain.models.metadata import BronzeMetadata, GoldMetadata, SilverMetadata

if TYPE_CHECKING:
    from bioetl.domain.lineage import LineageGraphFragment

__all__ = ["MetadataLineageBundle", "MetadataLineageBundleResult", "MetadataT"]

MetadataT = TypeVar("MetadataT", BronzeMetadata, SilverMetadata, GoldMetadata)


def _resolve_primary_artifact_id(fragment: LineageGraphFragment) -> str:
    """Resolve the canonical produced artifact id for one lineage fragment."""
    node_index = {node.node_id: node for node in fragment.nodes}
    produced_artifact_ids: list[str] = []
    for edge in fragment.edges:
        if edge.edge_type is not LineageEdgeType.PRODUCED_BY:
            continue
        node = node_index.get(edge.source.node_id, edge.source)
        if node.node_type in {LineageNodeType.DATASET, LineageNodeType.BRONZE_BATCH}:
            produced_artifact_ids.append(node.node_id)
    unique_artifact_ids = tuple(dict.fromkeys(produced_artifact_ids))
    if not unique_artifact_ids:
        raise ValueError(
            f"Lineage fragment {fragment.fragment_id} does not expose a produced artifact node"
        )
    if len(unique_artifact_ids) > 1:
        raise ValueError(
            f"Lineage fragment {fragment.fragment_id} exposes multiple produced artifacts: {unique_artifact_ids}"
        )
    return unique_artifact_ids[0]


def _attach_fragment_anchor(
    metadata: object,
    fragment_id: str,
    artifact_id: str,
) -> None:
    """Attach canonical lineage anchors to sidecar output metadata."""
    output = getattr(metadata, "output", None)
    if output is None or not hasattr(output, "lineage_fragment_id"):
        return
    output.lineage_fragment_id = fragment_id
    if hasattr(output, "artifact_id"):
        output.artifact_id = artifact_id


def _validate_bundle_identity_contract(
    metadata: object,
    fragment: LineageGraphFragment,
    artifact_id: str,
) -> None:
    """Validate the minimal cross-layer sidecar identity contract."""
    runtime = getattr(metadata, "runtime", None)
    if runtime is None or not str(getattr(runtime, "run_id", "")).strip():
        raise ValueError("Sidecar metadata must include runtime.run_id")
    fragment_run_id = str(fragment.run_id or "").strip()
    if fragment_run_id and str(runtime.run_id) != fragment_run_id:
        raise ValueError(
            "Sidecar runtime.run_id does not match lineage fragment run_id"
        )
    runtime_manifest_id = str(getattr(runtime, "manifest_id", "") or "").strip()
    fragment_manifest_id = str(fragment.manifest_id or "").strip()
    if runtime_manifest_id and fragment_manifest_id and runtime_manifest_id != fragment_manifest_id:
        raise ValueError(
            "Sidecar runtime.manifest_id does not match lineage fragment manifest_id"
        )
    output = getattr(metadata, "output", None)
    if output is None:
        raise ValueError("Sidecar metadata must include output metadata")
    if not str(artifact_id).strip():
        raise ValueError("Sidecar metadata must resolve a canonical artifact_id")


@dataclass(frozen=True, slots=True)
class MetadataLineageBundleResult(Generic[MetadataT]):
    """Bundle one sidecar metadata payload together with its lineage fragment."""

    metadata: MetadataT
    lineage_fragment: LineageGraphFragment

    def __post_init__(self) -> None:
        """Keep sidecar summary and full lineage fragment explicitly linked."""
        artifact_id = _resolve_primary_artifact_id(self.lineage_fragment)
        _attach_fragment_anchor(
            metadata=self.metadata,
            fragment_id=self.lineage_fragment.fragment_id,
            artifact_id=artifact_id,
        )
        _validate_bundle_identity_contract(
            metadata=self.metadata,
            fragment=self.lineage_fragment,
            artifact_id=artifact_id,
        )


MetadataLineageBundle = MetadataLineageBundleResult
