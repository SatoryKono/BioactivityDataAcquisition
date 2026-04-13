"""Unit tests for file-backed lineage fragment storage."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

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

    loaded_by_semantic_id = store.get("silver:fragment-1")

    assert loaded_by_semantic_id is not None
    assert loaded_by_semantic_id.fragment_id == "silver:fragment-1"
    assert loaded_by_semantic_id.stored_fragment_id is not None
    assert loaded_by_semantic_id.run_id == str(run_id)
    assert loaded_by_semantic_id.manifest_id == "manifest-1"
    assert store.list_by_run_id(run_id) == [loaded_by_semantic_id]
    assert store.list_by_manifest_id("manifest-1") == [loaded_by_semantic_id]
    assert store.list_by_node_id(dataset_node.node_id) == [loaded_by_semantic_id]


def test_file_store_emits_lineage_read_metric_on_manifest_lookup(tmp_path) -> None:
    metrics = MagicMock()
    store = FileLineageStore(
        base_path=tmp_path / "lineage",
        metrics=metrics,
    )
    run_id = RunID(uuid4())
    run_node = LineageNodeRef(
        node_type=LineageNodeType.RUN,
        node_id=f"run:{run_id}",
        label="chembl_activity",
    )
    dataset_node = DatasetRef(
        layer="silver",
        logical_name="chembl.activity",
        version=13,
        provider="chembl",
        entity="activity",
        path="data/output/silver/chembl/activity",
        manifest_id="manifest-2",
        run_id=str(run_id),
    ).to_node_ref()
    fragment = LineageGraphFragment(
        fragment_id="silver:fragment-2",
        nodes=(run_node, dataset_node),
        edges=(
            LineageEdge(
                edge_type=LineageEdgeType.PRODUCED_BY,
                source=dataset_node,
                target=run_node,
                run_id=str(run_id),
                manifest_id="manifest-2",
                created_at=datetime.now(UTC),
            ),
        ),
        run_id=str(run_id),
        manifest_id="manifest-2",
        created_at=datetime.now(UTC),
    )

    store.save(fragment)
    metrics.reset_mock()

    assert store.list_by_manifest_id("manifest-2") == [fragment]

    metrics.increment_counter.assert_called_once_with(
        "bioetl_control_plane_reads_total",
        1,
        {
            "store": "lineage",
            "operation": "list_by_manifest_id",
            "status": "success",
        },
    )
    metrics.observe_histogram.assert_called_once()


def test_file_store_preserves_occurrence_specific_history_for_semantically_equivalent_fragments(
    tmp_path,
) -> None:
    store = FileLineageStore(base_path=tmp_path / "lineage")
    first_run_id = RunID(uuid4())
    second_run_id = RunID(uuid4())

    def _build_fragment(*, run_id: RunID, manifest_id: str) -> LineageGraphFragment:
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
            manifest_id=manifest_id,
            run_id=str(run_id),
        ).to_node_ref()
        return LineageGraphFragment(
            fragment_id="silver:fragment-semantic",
            nodes=(run_node, dataset_node),
            edges=(
                LineageEdge(
                    edge_type=LineageEdgeType.PRODUCED_BY,
                    source=dataset_node,
                    target=run_node,
                    run_id=str(run_id),
                    manifest_id=manifest_id,
                    created_at=datetime.now(UTC),
                ),
            ),
            run_id=str(run_id),
            manifest_id=manifest_id,
            created_at=datetime.now(UTC),
        )

    first_fragment = _build_fragment(run_id=first_run_id, manifest_id="manifest-1")
    second_fragment = _build_fragment(run_id=second_run_id, manifest_id="manifest-2")

    store.save(first_fragment)
    store.save(second_fragment)

    first_loaded = store.list_by_run_id(first_run_id)
    second_loaded = store.list_by_run_id(second_run_id)

    assert len(first_loaded) == 1
    assert len(second_loaded) == 1
    assert first_loaded[0].fragment_id == "silver:fragment-semantic"
    assert second_loaded[0].fragment_id == "silver:fragment-semantic"
    assert first_loaded[0].stored_fragment_id is not None
    assert second_loaded[0].stored_fragment_id is not None
    assert first_loaded[0].stored_fragment_id != second_loaded[0].stored_fragment_id
    assert first_loaded[0].manifest_id == "manifest-1"
    assert second_loaded[0].manifest_id == "manifest-2"
    assert store.list_by_manifest_id("manifest-1") == first_loaded
    assert store.list_by_manifest_id("manifest-2") == second_loaded

    with pytest.raises(
        ValueError,
        match="Semantic lineage fragment id resolves to multiple stored occurrence records",
    ):
        store.get("silver:fragment-semantic")
