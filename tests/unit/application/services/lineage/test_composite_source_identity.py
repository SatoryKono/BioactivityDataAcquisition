"""Composite context belongs to edges, not shared source identities."""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from bioetl.application.observability.control_plane_evidence.lineage_graph_validation import (
    conflicting_node_ids,
)
from bioetl.application.services.lineage.metadata_lineage_composite import (
    _build_composite_source_nodes_and_edges,
)
from bioetl.domain.lineage import LineageGraphFragment, LineageNodeRef, LineageNodeType

pytestmark = pytest.mark.unit


def fragment(name, run_id, layer):
    dataset = LineageNodeRef(
        node_type=LineageNodeType.DATASET, node_id=f"{layer}:{name}:{run_id}"
    )
    nodes, edges = _build_composite_source_nodes_and_edges(
        dataset_node=dataset,
        run_context=SimpleNamespace(run_id=run_id, manifest_id=f"manifest-{run_id}"),
        created_at=datetime(2026, 10, 3, tzinfo=UTC),
        source_providers=["seed", "chembl_compound_record"],
        provider_field_map={"seed": ["activity_id"]},
        enrichment_status={"chembl_compound_record": "success"},
        composite_run_id=run_id,
        composite_name=name,
    )
    return LineageGraphFragment(
        fragment_id=f"{layer}-{run_id}",
        run_id=run_id,
        manifest_id=f"manifest-{run_id}",
        nodes=(dataset, *nodes),
        edges=tuple(edges),
    )


@pytest.mark.parametrize(
    "name", ["activity", "assay", "molecule", "target", "publication"]
)
@pytest.mark.parametrize("reverse", [False, True])
def test_layers_and_runs_share_source_identity_without_context_conflicts(name, reverse):
    fragments = (
        fragment("composite.merged", "run-1", "silver"),
        fragment(f"composite/{name}", "run-1", "gold"),
        fragment(f"composite/{name}", "run-2", "gold"),
    )
    assert (
        conflicting_node_ids(tuple(reversed(fragments)) if reverse else fragments) == []
    )
    for part in fragments:
        for edge in part.edges:
            assert edge.attributes["composite_run_id"] == part.run_id
            assert edge.attributes["composite_name"]


def test_real_source_contradiction_is_still_rejected():
    original = fragment("composite/activity", "run-1", "gold")
    wrong = LineageNodeRef(
        node_type=LineageNodeType.SOURCE_SYSTEM,
        node_id="source_system:seed",
        attributes={"provider": "different"},
    )
    corrupted = LineageGraphFragment(
        fragment_id="corrupt", run_id="run-1", nodes=(wrong,), edges=()
    )
    assert conflicting_node_ids((original, corrupted)) == ["source_system:seed"]
