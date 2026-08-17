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
"""Unit tests for shared lineage fragment finalization helpers."""

from __future__ import annotations

import pytest
from tests.helpers.deterministic_ids import deterministic_run_uuid_from_callsite

from datetime import UTC, datetime

from bioetl.application.services.lineage._fragment_finalization import (
    finalize_lineage_fragment,
)
from bioetl.application.services.lineage.metadata_lineage_node_builders import (
    build_semantic_fragment_id,
)
from bioetl.domain.lineage import (
    LineageEdge,
    LineageEdgeType,
    LineageNodeRef,
    LineageNodeType,
)
from bioetl.domain.types import RunType
from bioetl.domain.value_objects.run_context import RunContext


pytestmark = pytest.mark.unit


def _make_run_context() -> RunContext:
    return RunContext.create(
        run_id=deterministic_run_uuid_from_callsite("test_fragment_finalization"),
        run_type=RunType.INCREMENTAL,
        started_at=datetime(2026, 4, 24, 12, 0, tzinfo=UTC),
        provider="chembl",
        entity="activity",
    )


def test_finalize_lineage_fragment_dedupes_nodes_and_preserves_envelope() -> None:
    run_context = _make_run_context()
    created_at = datetime(2026, 4, 24, 12, 30, tzinfo=UTC)
    run_node = LineageNodeRef(
        node_type=LineageNodeType.RUN,
        node_id=f"run:{run_context.run_id}",
        label=run_context.pipeline_name,
        attributes={"run_id": str(run_context.run_id)},
    )
    duplicate_run_node = LineageNodeRef(
        node_type=LineageNodeType.RUN,
        node_id=run_node.node_id,
        label="duplicate",
        attributes={"run_id": str(run_context.run_id)},
    )
    dataset_node = LineageNodeRef(
        node_type=LineageNodeType.DATASET,
        node_id="silver:chembl.activity",
        label="activity",
        attributes={"layer": "silver"},
    )
    edge = LineageEdge(
        edge_type=LineageEdgeType.PRODUCED_BY,
        source=dataset_node,
        target=run_node,
        run_id=str(run_context.run_id),
        manifest_id=run_context.manifest_id,
        created_at=created_at,
    )

    fragment = finalize_lineage_fragment(
        fragment_name="silver",
        run_context=run_context,
        nodes=[run_node, duplicate_run_node, dataset_node],
        edges=[edge],
        created_at=created_at,
    )

    assert fragment.nodes == (run_node, dataset_node)
    assert fragment.edges == (edge,)
    assert fragment.run_id == str(run_context.run_id)
    assert fragment.manifest_id == run_context.manifest_id
    assert fragment.created_at == created_at
    assert fragment.fragment_id == build_semantic_fragment_id(
        "silver",
        nodes=fragment.nodes,
        edges=fragment.edges,
    )


def test_finalize_lineage_fragment_rejects_dangling_edge_endpoints() -> None:
    run_context = _make_run_context()
    created_at = datetime(2026, 4, 24, 12, 30, tzinfo=UTC)
    run_node = LineageNodeRef(
        node_type=LineageNodeType.RUN,
        node_id=f"run:{run_context.run_id}",
    )
    missing = LineageNodeRef(node_type=LineageNodeType.DATASET, node_id="dataset:missing")
    with pytest.raises(ValueError, match="dataset:missing"):
        finalize_lineage_fragment(
            fragment_name="bronze",
            run_context=run_context,
            nodes=[run_node],
            edges=[
                LineageEdge(
                    edge_type=LineageEdgeType.PRODUCED_BY,
                    source=missing,
                    target=run_node,
                )
            ],
            created_at=created_at,
        )


def test_finalize_lineage_fragment_orders_nodes_by_stable_identifier() -> None:
    run_context = _make_run_context()
    created_at = datetime(2026, 4, 24, 12, 30, tzinfo=UTC)
    later_node = LineageNodeRef(
        node_type=LineageNodeType.DATASET,
        node_id="silver:z",
        attributes={"layer": "silver"},
    )
    earlier_node = LineageNodeRef(
        node_type=LineageNodeType.DATASET,
        node_id="silver:a",
        attributes={"layer": "silver"},
    )

    fragment = finalize_lineage_fragment(
        fragment_name="silver",
        run_context=run_context,
        nodes=[later_node, earlier_node, later_node],
        edges=[],
        created_at=created_at,
    )

    assert [node.node_id for node in fragment.nodes] == ["silver:a", "silver:z"]
