# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for LineageInspectionService."""

from __future__ import annotations

import pytest
from tests.helpers.deterministic_ids import deterministic_run_uuid_from_callsite

from datetime import UTC, datetime

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


pytestmark = pytest.mark.unit


class _InMemoryLineageStore(LineageStorePort):
    def __init__(self) -> None:
        self._items: list[LineageGraphFragment] = []

    def save(self, fragment: LineageGraphFragment) -> None:
        self._items.append(fragment)

    def get(self, fragment_id: str) -> LineageGraphFragment | None:
        return next(
            (item for item in self._items if item.fragment_id == fragment_id),
            None,
        )

    def get_occurrence(self, fragment_id: str) -> LineageGraphFragment | None:
        return next(
            (
                item
                for item in self._items
                if (item.stored_fragment_id or item.fragment_id) == fragment_id
            ),
            None,
        )

    def list_by_run_id(self, run_id: RunID) -> list[LineageGraphFragment]:
        return [item for item in self._items if item.run_id == str(run_id)]

    def list_by_manifest_id(self, manifest_id: str) -> list[LineageGraphFragment]:
        return [item for item in self._items if item.manifest_id == manifest_id]

    def list_by_node_id(self, node_id: str) -> list[LineageGraphFragment]:
        return [
            item
            for item in self._items
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

    result = service.show_fragment("silver:fragment-1:occurrence:abc123")

    assert result.fragment == fragment
    assert result.to_dict()["fragment"]["stored_fragment_id"] == (
        "silver:fragment-1:occurrence:abc123"
    )


def test_show_fragment_semantic_lookup_is_explicit() -> None:
    store = _InMemoryLineageStore()
    fragment = LineageGraphFragment(
        fragment_id="silver:fragment-1",
        stored_fragment_id="silver:fragment-1:occurrence:abc123",
        created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )
    store.save(fragment)
    service = LineageInspectionService(lineage_store=store)

    result = service.show_fragment("silver:fragment-1", semantic=True)

    assert result.fragment == fragment


def test_show_fragment_raises_when_identifier_missing() -> None:
    service = LineageInspectionService(lineage_store=_InMemoryLineageStore())

    with pytest.raises(ValueError, match="Lineage fragment not found"):
        service.show_fragment("silver:missing")


def test_trace_returns_upstream_and_downstream_relations() -> None:
    store = _InMemoryLineageStore()
    run_id = deterministic_run_uuid_from_callsite("test_lineage_inspection_service")
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


def test_trace_raises_when_dataset_ref_is_missing() -> None:
    service = LineageInspectionService(lineage_store=_InMemoryLineageStore())

    with pytest.raises(ValueError, match="Lineage trace not found"):
        service.trace("silver:missing")


def test_explain_run_resolves_manifest_and_aggregates_outputs() -> None:
    store = _InMemoryLineageStore()
    manifest_store = _InMemoryRunManifestStore()
    run_id = deterministic_run_uuid_from_callsite("test_lineage_inspection_service")
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


def test_explain_run_falls_back_to_run_index_when_manifest_has_no_manifest_fragments() -> (
    None
):
    store = _InMemoryLineageStore()
    manifest_store = _InMemoryRunManifestStore()
    run_id = deterministic_run_uuid_from_callsite("lineage-manifest-run-fallback")
    manifest = _make_manifest(manifest_id="manifest-run-fallback", run_id=run_id)
    manifest_store.save(manifest)
    bronze_node = LineageNodeRef(
        node_type=LineageNodeType.BRONZE_BATCH,
        node_id="bronze_batch:manifest-fallback",
    )
    fragment = LineageGraphFragment(
        fragment_id="bronze:fragment-manifest-run-fallback",
        stored_fragment_id="bronze:fragment-manifest-run-fallback:occurrence",
        nodes=(bronze_node,),
        run_id=str(run_id),
    )
    store.save(fragment)

    result = LineageInspectionService(
        lineage_store=store,
        manifest_port=manifest_store,
    ).explain_run("manifest-run-fallback")

    assert result.manifest_id == "manifest-run-fallback"
    assert result.run_id == str(run_id)
    assert result.fragment_ids == ("bronze:fragment-manifest-run-fallback",)


def test_explain_run_resolves_direct_manifest_index_without_manifest_store() -> None:
    store = _InMemoryLineageStore()
    run_id = deterministic_run_uuid_from_callsite("lineage-direct-manifest")
    dataset_node = DatasetRef(
        layer="silver",
        logical_name="chembl.activity",
        version=13,
    ).to_node_ref()
    fragment = LineageGraphFragment(
        fragment_id="silver:fragment-direct",
        stored_fragment_id="silver:fragment-direct:occurrence",
        nodes=(dataset_node,),
        run_id=str(run_id),
        manifest_id="manifest-direct",
    )
    store.save(fragment)

    result = LineageInspectionService(lineage_store=store).explain_run(
        "manifest-direct"
    )

    assert result.manifest_id == "manifest-direct"
    assert result.run_id is None
    assert result.fragment_ids == ("silver:fragment-direct",)


def test_explain_run_resolves_direct_run_index_without_manifest_store() -> None:
    store = _InMemoryLineageStore()
    run_id = deterministic_run_uuid_from_callsite("lineage-direct-run")
    bronze_node = LineageNodeRef(
        node_type=LineageNodeType.BRONZE_BATCH,
        node_id="bronze_batch:run-direct",
    )
    fragment = LineageGraphFragment(
        fragment_id="bronze:fragment-direct",
        stored_fragment_id="bronze:fragment-direct:occurrence",
        nodes=(bronze_node,),
        run_id=str(run_id),
    )
    store.save(fragment)

    result = LineageInspectionService(lineage_store=store).explain_run(str(run_id))

    assert result.manifest_id is None
    assert result.run_id == str(run_id)
    assert result.fragment_ids == ("bronze:fragment-direct",)
    assert result.produced_bronze_batches == ()


def test_explain_run_raises_when_identifier_cannot_be_resolved() -> None:
    service = LineageInspectionService(lineage_store=_InMemoryLineageStore())

    with pytest.raises(ValueError, match="Lineage run explanation not found"):
        service.explain_run("missing-run")


def test_explain_run_resolves_via_manifest_lookup_by_run_id() -> None:
    store = _InMemoryLineageStore()
    manifest_store = _InMemoryRunManifestStore()
    run_id = deterministic_run_uuid_from_callsite("lineage-manifest-by-run-id")
    manifest = _make_manifest(manifest_id="manifest-run-lookup", run_id=run_id)
    manifest_store.save(manifest)
    dataset_node = DatasetRef(
        layer="silver",
        logical_name="chembl.activity",
        version=14,
    ).to_node_ref()
    fragment = LineageGraphFragment(
        fragment_id="silver:fragment-run-lookup",
        stored_fragment_id="silver:fragment-run-lookup:occurrence",
        nodes=(dataset_node,),
        manifest_id="manifest-run-lookup",
        run_id=str(run_id),
    )
    store.save(fragment)

    result = LineageInspectionService(
        lineage_store=store,
        manifest_port=manifest_store,
    ).explain_run(str(run_id))

    assert result.manifest_id == "manifest-run-lookup"
    assert result.run_id == str(run_id)
    assert result.fragment_ids == ("silver:fragment-run-lookup",)


def test_resolve_via_manifest_returns_none_when_manifest_lookup_by_run_id_has_no_fragments() -> (
    None
):
    manifest_store = _InMemoryRunManifestStore()
    run_id = deterministic_run_uuid_from_callsite("lineage-empty-manifest-run-id")
    manifest_store.save(_make_manifest(manifest_id="manifest-empty", run_id=run_id))
    service = LineageInspectionService(
        lineage_store=_InMemoryLineageStore(),
        manifest_port=manifest_store,
    )

    assert service._resolve_via_manifest(str(run_id)) is None


def test_parse_run_id_returns_none_for_invalid_identifier() -> None:
    assert LineageInspectionService._parse_run_id("not-a-uuid") is None
