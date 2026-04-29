"""Domain-level bundle for sidecar metadata and lineage fragments."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeVar

from bioetl.domain.lineage.models import (
    LineageEdge,
    LineageEdgeType,
    LineageNodeRef,
    LineageNodeType,
)
from bioetl.domain.models.metadata import BronzeMetadata, GoldMetadata, SilverMetadata

if TYPE_CHECKING:
    from bioetl.domain.lineage.models import LineageGraphFragment

__all__ = ["MetadataLineageBundleResult", "MetadataT"]

MetadataT = TypeVar("MetadataT", BronzeMetadata, SilverMetadata, GoldMetadata)


def _resolve_primary_artifact_id(fragment: LineageGraphFragment) -> str:
    """Resolve the canonical produced artifact id for one lineage fragment."""
    unique_artifact_ids = _produced_artifact_ids(fragment)
    if not unique_artifact_ids:
        raise ValueError(
            f"Lineage fragment {fragment.fragment_id} does not expose a produced artifact node"
        )
    if len(unique_artifact_ids) > 1:
        raise ValueError(
            f"Lineage fragment {fragment.fragment_id} exposes multiple produced artifacts: {unique_artifact_ids}"
        )
    return unique_artifact_ids[0]


def _produced_artifact_ids(fragment: LineageGraphFragment) -> tuple[str, ...]:
    node_index = {node.node_id: node for node in fragment.nodes}
    artifact_ids = [
        artifact_id
        for edge in fragment.edges
        if (artifact_id := _produced_artifact_id_for_edge(edge, node_index)) is not None
    ]
    return tuple(dict.fromkeys(artifact_ids))


def _produced_artifact_id_for_edge(
    edge: LineageEdge,
    node_index: dict[str, LineageNodeRef],
) -> str | None:
    if edge.edge_type is not LineageEdgeType.PRODUCED_BY:
        return None
    node = node_index.get(edge.source.node_id)
    if node is None:
        return None
    if node.node_type not in {LineageNodeType.DATASET, LineageNodeType.BRONZE_BATCH}:
        return None
    return str(node.node_id)


def _attach_fragment_anchor(
    metadata: object,
    fragment_id: str,
    artifact_id: str,
) -> None:
    """Attach canonical lineage anchors to sidecar output metadata."""
    output = getattr(metadata, "output", None)
    if output is None or not hasattr(output, "lineage_fragment_id"):
        return
    _set_missing_anchor(output, "lineage_fragment_id", fragment_id)
    if hasattr(output, "artifact_id"):
        _set_missing_anchor(output, "artifact_id", artifact_id)


def _set_missing_anchor(output: object, attribute_name: str, value: str) -> None:
    if _normalized_attr(output, attribute_name):
        return
    setattr(output, attribute_name, value)


def _normalized_attr(target: object, attribute_name: str) -> str:
    return str(getattr(target, attribute_name, "") or "").strip()


def _validate_runtime_identity_contract(
    metadata: object,
    fragment: LineageGraphFragment,
) -> None:
    """Validate runtime-side lineage anchors against the fragment identity."""
    runtime = getattr(metadata, "runtime", None)
    runtime_run_id = _require_runtime_run_id(runtime)
    _validate_runtime_run_id_matches_fragment(runtime_run_id, fragment)
    _validate_runtime_manifest_matches_fragment(runtime, fragment)


def _require_runtime_run_id(runtime: object) -> str:
    """Return the persisted runtime.run_id or raise when it is absent."""
    runtime_run_id = str(getattr(runtime, "run_id", "") or "").strip()
    if runtime is None or not runtime_run_id:
        raise ValueError("Sidecar metadata must include runtime.run_id")
    return runtime_run_id


def _validate_runtime_run_id_matches_fragment(
    runtime_run_id: str,
    fragment: LineageGraphFragment,
) -> None:
    """Ensure runtime.run_id matches the lineage fragment run identity."""
    fragment_run_id = str(fragment.run_id or "").strip()
    if fragment_run_id and runtime_run_id != fragment_run_id:
        raise ValueError(
            "Sidecar runtime.run_id does not match lineage fragment run_id"
        )


def _validate_runtime_manifest_matches_fragment(
    runtime: object,
    fragment: LineageGraphFragment,
) -> None:
    """Ensure runtime.manifest_id matches the lineage fragment manifest identity."""
    runtime_manifest_id = _normalized_attr(runtime, "manifest_id")
    fragment_manifest_id = str(fragment.manifest_id or "").strip()
    if _non_empty_mismatch(runtime_manifest_id, fragment_manifest_id):
        raise ValueError(
            "Sidecar runtime.manifest_id does not match lineage fragment manifest_id"
        )


def _non_empty_mismatch(left: str, right: str) -> bool:
    return bool(left and right and left != right)


def _validate_output_identity_contract(
    metadata: object,
    fragment: LineageGraphFragment,
    artifact_id: str,
) -> None:
    """Validate output-side lineage anchors against the fragment identity."""
    output = getattr(metadata, "output", None)
    if output is None:
        raise ValueError("Sidecar metadata must include output metadata")
    _raise_if_anchor_mismatch(
        actual=_normalized_attr(output, "lineage_fragment_id"),
        expected=fragment.fragment_id,
        message="Sidecar output.lineage_fragment_id does not match lineage fragment fragment_id",
    )
    _raise_if_anchor_mismatch(
        actual=_normalized_attr(output, "artifact_id"),
        expected=artifact_id,
        message="Sidecar output.artifact_id does not match lineage fragment produced artifact",
    )
    _require_non_empty_artifact_id(artifact_id)


def _raise_if_anchor_mismatch(*, actual: str, expected: str, message: str) -> None:
    if _non_empty_mismatch(actual, expected):
        raise ValueError(message)


def _require_non_empty_artifact_id(artifact_id: str) -> None:
    if not str(artifact_id).strip():
        raise ValueError("Sidecar metadata must resolve a canonical artifact_id")


def _validate_bundle_identity_contract(
    metadata: object,
    fragment: LineageGraphFragment,
    artifact_id: str,
) -> None:
    """Validate the minimal cross-layer sidecar identity contract."""
    _validate_runtime_identity_contract(metadata, fragment)
    _validate_output_identity_contract(metadata, fragment, artifact_id)


@dataclass(frozen=True, slots=True)
class MetadataLineageBundleResult[
    MetadataT: (BronzeMetadata, SilverMetadata, GoldMetadata)
]:
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
