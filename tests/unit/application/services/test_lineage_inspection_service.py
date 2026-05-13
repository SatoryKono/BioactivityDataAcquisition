"""Unit tests for LineageInspectionService."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from bioetl.application.services.lineage.lineage_inspection_service import (
    LineageInspectionService,
)
from bioetl.domain.control_plane import RunCodeProvenance, RunManifest
from bioetl.domain.lineage import (
    DatasetRef,
    LineageEdge,
    LineageEdgeType,
    LineageGraphFragment,
    LineageNodeRef,
    LineageNodeType,
    TransformRef,
)
from bioetl.domain.ports import LineageStorePort
from bioetl.domain.types import RunID, RunType
from tests.helpers.control_plane import InMemoryRunManifestStore


class _InMemoryLineageStore(LineageStorePort):
    def __init__(self) -> None:
        self._items: dict[str, LineageGraphFragment] = {}

    def save(self, fragment: LineageGraphFragment) -> None:
        self._items[fragment.fragment_id] = fragment

    def get(self, fragment_id: str) -> LineageGraphFragment | None:
        return self._items.get(fragment_id)

    def list_by_run_id(self, run_id: RunID) -> list[LineageGraphFragment]:
        return [item for item in self._items.values() if item.run_id == str(run_id)]

    def list_by_manifest_id(self, manifest_id: str) -> list[LineageGraphFragment]:
        return [
            item for item in self._items.values() if item.manifest_id == manifest_id
        ]

    def list_by_node_id(self, node_id: str) -> list[LineageGraphFragment]:
        return [
            item
            for item in self._items.values()
            if any(node.node_id == node_id for node in item.nodes)
        ]


_InMemoryRunManifestStore = InMemoryRunManifestStore


def _make_manifest(*, manifest_id: str, run_id: RunID) -> RunManifest:
    return RunManifest(
        manifest_id=manifest_id,
        execution_fingerprint=f"fingerprint-{manifest_id}",
        schema_version="1.0",
        created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        launch_context={"limit": 100},
        runtime_config={"run_type": "incremental", "limit": 100},
        resolved_config={"provider": "chembl", "entity_type": "activity"},
        code_provenance=RunCodeProvenance(
            pipeline_version="1.0.0",
            git_commit="abc1234",
            config_hash="deadbeef",
        ),
    )


def test_show_fragment_returns_stored_fragment() -> None:
    store = _InMemoryLineageStore()
    fragment = LineageGraphFragment(
        fragment_id="silver:fragment-1",
        stored_fragment_id="silver:fragment-1:occurrence:abc123",
        created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )
    store.save(fragment)
    service = LineageInspectionService(lineage_store=store)

    result = service.show_fragment("silver:fragment-1")

    assert result.fragment == fragment
    assert result.to_dict()["fragment"]["stored_fragment_id"] == (
        "silver:fragment-1:occurrence:abc123"
    )


def test_trace_returns_upstream_and_downstream_relations() -> None:
    store = _InMemoryLineageStore()
    run_id = RunID(uuid4())
    silver_node = DatasetRef(
        layer="silver",
        logical_name="chembl.activity",
        version=12,
    ).to_node_ref()
    bronze_node = LineageNodeRef(
        node_type=LineageNodeType.BRONZE_BATCH,
        node_id="bronze_batch:batch-1",
    )
    gold_node = DatasetRef(
        layer="gold",
        logical_name="chembl.activity",
        version=3,
    ).to_node_ref()
    silver_fragment = LineageGraphFragment(
        fragment_id="silver:fragment-1",
        stored_fragment_id="silver:fragment-1:occurrence:silver",
        nodes=(silver_node, bronze_node),
        edges=(
            LineageEdge(
                edge_type=LineageEdgeType.DERIVED_FROM,
                source=silver_node,
                target=bronze_node,
                run_id=str(run_id),
            ),
        ),
        run_id=str(run_id),
    )
    gold_fragment = LineageGraphFragment(
        fragment_id="gold:fragment-1",
        stored_fragment_id="gold:fragment-1:occurrence:gold",
        nodes=(gold_node, silver_node),
        edges=(
            LineageEdge(
                edge_type=LineageEdgeType.DERIVED_FROM,
                source=gold_node,
                target=silver_node,
                run_id=str(run_id),
            ),
        ),
        run_id=str(run_id),
    )
    store.save(silver_fragment)
    store.save(gold_fragment)
    service = LineageInspectionService(lineage_store=store)

    result = service.trace(silver_node.node_id)

    assert result.dataset_ref == silver_node.node_id
    assert result.fragment_ids == ("silver:fragment-1", "gold:fragment-1")
    assert result.stored_fragment_ids == (
        "silver:fragment-1:occurrence:silver",
        "gold:fragment-1:occurrence:gold",
    )
    assert result.upstream[0].node.node_id == bronze_node.node_id
    assert result.upstream[0].stored_fragment_id == (
        "silver:fragment-1:occurrence:silver"
    )
    assert result.downstream[0].node.node_id == gold_node.node_id
    assert result.downstream[0].stored_fragment_id == (
        "gold:fragment-1:occurrence:gold"
    )


def test_explain_run_resolves_manifest_and_aggregates_outputs() -> None:
    store = _InMemoryLineageStore()
    manifest_store = _InMemoryRunManifestStore()
    run_id = RunID(uuid4())
    manifest = _make_manifest(manifest_id="manifest-1", run_id=run_id)
    manifest_store.save(manifest)
    silver_node = DatasetRef(
        layer="silver",
        logical_name="chembl.activity",
        version=12,
    ).to_node_ref()
    transform_node = TransformRef(
        name="normalize",
        version="1.0.0",
        step_index=1,
        pipeline_name="chembl_activity",
    ).to_node_ref()
    source_node = LineageNodeRef(
        node_type=LineageNodeType.SOURCE_SYSTEM,
        node_id="source_system:chembl",
        label="chembl",
    )
    fragment = LineageGraphFragment(
        fragment_id="silver:fragment-1",
        stored_fragment_id="silver:fragment-1:occurrence:manifest-1",
        nodes=(silver_node, transform_node, source_node),
        edges=(
            LineageEdge(
                edge_type=LineageEdgeType.PRODUCED_BY,
                source=silver_node,
                target=transform_node,
                run_id=str(run_id),
                manifest_id="manifest-1",
            ),
        ),
        run_id=str(run_id),
        manifest_id="manifest-1",
    )
    store.save(fragment)
    service = LineageInspectionService(
        lineage_store=store,
        manifest_port=manifest_store,
    )

    result = service.explain_run("manifest-1")

    assert result.manifest_id == "manifest-1"
    assert result.run_id == str(run_id)
    assert result.fragment_ids == ("silver:fragment-1",)
    assert result.stored_fragment_ids == ("silver:fragment-1:occurrence:manifest-1",)
    assert result.produced_datasets[0].node_id == silver_node.node_id
    assert result.transforms[0].node_id == transform_node.node_id
    assert result.source_systems[0].node_id == source_node.node_id
