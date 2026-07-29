# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
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
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Unit tests for canonical lineage domain models."""

from __future__ import annotations

import pytest

from datetime import UTC, datetime

from bioetl.domain.lineage import (
    DatasetRef,
    LineageEdge,
    LineageEdgeType,
    LineageGraphFragment,
    LineageNodeType,
    SchemaRef,
    TransformRef,
)
from bioetl.domain.lineage._shared import (
    load_attributes,
    load_mapping,
    load_optional_int,
    load_optional_version,
)
from bioetl.domain.medallion import Layer


pytestmark = pytest.mark.unit


def test_dataset_ref_normalizes_layer_and_builds_node_ref() -> None:
    ref = DatasetRef(
        layer=Layer.SILVER,
        logical_name="chembl.activity",
        version=7,
        provider="chembl",
        entity="activity",
        path="data/output/silver/chembl/activity",
        manifest_id="manifest-1",
        run_id="run-1",
    )

    node = ref.to_node_ref()

    assert ref.layer == "silver"
    assert node.node_type == LineageNodeType.DATASET
    assert node.node_id == "silver:chembl.activity@7"
    assert node.attributes["provider"] == "chembl"
    assert node.attributes["manifest_id"] == "manifest-1"


def test_transform_and_schema_refs_build_stable_node_ids() -> None:
    transform = TransformRef(
        name="normalize_values",
        version="1.2.3",
        step_index=1,
        pipeline_name="chembl_activity",
    )
    schema = SchemaRef(
        contract_path="contracts/gold/chembl/activity.py",
        version="3.0",
        validation_mode="strict",
        dataset_name="chembl.activity",
    )

    transform_node = transform.to_node_ref()
    schema_node = schema.to_node_ref()

    assert transform_node.node_id == (
        "transform:chembl_activity:normalize_values:1.2.3:1"
    )
    assert schema_node.node_id == "schema:contracts/gold/chembl/activity.py:3.0"
    assert schema_node.attributes["validation_mode"] == "strict"


def test_lineage_edge_and_fragment_roundtrip() -> None:
    dataset = DatasetRef(
        layer="gold",
        logical_name="chembl.activity",
        version=11,
    ).to_node_ref()
    transform = TransformRef(
        name="rank_records",
        version="2.0.0",
        step_index=2,
        pipeline_name="chembl_activity",
    ).to_node_ref()
    created_at = datetime(2026, 3, 24, 12, 0, tzinfo=UTC)

    edge = LineageEdge(
        edge_type=LineageEdgeType.PRODUCED_BY,
        source=dataset,
        target=transform,
        run_id="run-123",
        manifest_id="manifest-123",
        created_at=created_at,
        attributes={"validation": "strict"},
    )
    fragment = LineageGraphFragment(
        fragment_id="frag-001",
        nodes=[dataset, transform],
        edges=[edge],
        run_id="run-123",
        manifest_id="manifest-123",
        created_at=created_at,
    )

    restored = LineageGraphFragment.from_dict(fragment.to_dict())

    assert len(restored.nodes) == 2
    assert len(restored.edges) == 1
    assert restored.edges[0].edge_type == LineageEdgeType.PRODUCED_BY
    assert restored.edges[0].attributes["validation"] == "strict"
    assert restored.edges[0].source.node_id == "gold:chembl.activity@11"


def test_lineage_shared_helpers_normalize_edge_case_payloads() -> None:
    assert load_attributes(["not", "a", "mapping"]) == {}
    assert load_mapping("not-a-mapping") == {}
    assert load_optional_version({"version": 3.5}, "version") is None
    assert load_optional_int({"step_index": "7"}, "step_index") == 7
