"""Helpers for valid lineage fragments in storage-focused unit tests."""

from __future__ import annotations

from datetime import UTC, datetime

from bioetl.domain.lineage import (
    DatasetRef,
    LineageEdge,
    LineageEdgeType,
    LineageGraphFragment,
    LineageNodeRef,
    LineageNodeType,
    TransformRef,
)

__all__ = ["make_produced_artifact_fragment"]


def make_produced_artifact_fragment(
    *,
    fragment_id: str,
    layer: str = "silver",
    logical_name: str = "test.dataset",
    artifact_node_type: LineageNodeType = LineageNodeType.DATASET,
) -> LineageGraphFragment:
    """Create one minimal lineage fragment with a valid produced artifact node."""
    created_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    if artifact_node_type is LineageNodeType.BRONZE_BATCH:
        artifact_node = LineageNodeRef(
            node_type=LineageNodeType.BRONZE_BATCH,
            node_id=f"bronze_batch:{logical_name}",
            label=logical_name,
            attributes={"layer": "bronze", "logical_name": logical_name},
        )
    else:
        artifact_node = DatasetRef(
            layer=layer,
            logical_name=logical_name,
        ).to_node_ref()
    transform_node = TransformRef(
        name="test_transform",
        version="test",
        pipeline_name="test_pipeline",
    ).to_node_ref()
    return LineageGraphFragment(
        fragment_id=fragment_id,
        nodes=(artifact_node, transform_node),
        edges=(
            LineageEdge(
                edge_type=LineageEdgeType.PRODUCED_BY,
                source=artifact_node,
                target=transform_node,
                created_at=created_at,
            ),
        ),
        created_at=created_at,
    )
