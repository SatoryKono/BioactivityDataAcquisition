"""Unit tests for file-backed lineage fragment storage."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from bioetl.domain.lineage import (
    DatasetRef,
    LineageEdge,
    LineageEdgeType,
    LineageGraphFragment,
    LineageNodeRef,
    LineageNodeType,
)
from bioetl.domain.types import RunID
from bioetl.infrastructure.control_plane import FileLineageStore


def test_file_store_round_trips_fragments_by_id_run_manifest_and_node(tmp_path) -> None:
    store = FileLineageStore(base_path=tmp_path / "lineage")
    run_id = RunID(uuid4())
    run_node = LineageNodeRef(
        node_type=LineageNodeType.RUN,
        node_id=f"run:{run_id}",
        label="chembl_activity",
    )
    dataset_node = DatasetRef(
        layer="silver",
        logical_name="chembl.activity",
        version=12,
        provider="chembl",
        entity="activity",
        path="data/output/silver/chembl/activity",
        manifest_id="manifest-1",
        run_id=str(run_id),
    ).to_node_ref()
    fragment = LineageGraphFragment(
        fragment_id="silver:fragment-1",
        nodes=(run_node, dataset_node),
        edges=(
            LineageEdge(
                edge_type=LineageEdgeType.PRODUCED_BY,
                source=dataset_node,
                target=run_node,
                run_id=str(run_id),
                manifest_id="manifest-1",
                created_at=datetime.now(UTC),
            ),
        ),
        run_id=str(run_id),
        manifest_id="manifest-1",
        created_at=datetime.now(UTC),
    )

    store.save(fragment)

    assert store.get("silver:fragment-1") == fragment
    assert store.list_by_run_id(run_id) == [fragment]
    assert store.list_by_manifest_id("manifest-1") == [fragment]
    assert store.list_by_node_id(dataset_node.node_id) == [fragment]

