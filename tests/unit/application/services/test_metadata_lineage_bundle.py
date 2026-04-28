"""Unit tests for sidecar/lineage bundle contract enforcement."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from tests.helpers.metadata_fixtures import build_bronze_metadata

from bioetl.application.services.lineage import MetadataLineageBundle
from bioetl.domain.lineage import (
    LineageEdge,
    LineageEdgeType,
    LineageGraphFragment,
    LineageNodeRef,
    LineageNodeType,
)
from bioetl.domain.models.metadata import BronzeMetadata


def _make_bronze_metadata() -> BronzeMetadata:
    metadata = build_bronze_metadata()
    metadata.runtime.run_id = "run-1"
    metadata.runtime.manifest_id = "manifest-1"
    metadata.runtime.started_at_utc = datetime(2026, 4, 10, 10, 0, tzinfo=UTC)
    metadata.runtime.completed_at_utc = None
    metadata.pipeline.version = "1.0.0"
    metadata.source.url = None
    metadata.source.api_version = None
    metadata.output.record_count = 1
    metadata.output.total_bytes = 128
    metadata.output_ext.files = []
    metadata.environment.hostname = "host"
    metadata.environment.python_version = "3.13.0"
    metadata.environment.bioetl_version = "6.0.0"
    return metadata


def test_metadata_lineage_bundle_sets_output_artifact_id() -> None:
    metadata = _make_bronze_metadata()
    batch_node = LineageNodeRef(
        node_type=LineageNodeType.BRONZE_BATCH,
        node_id="bronze_batch:batch-1",
        attributes={"batch_id": "batch-1"},
    )
    run_node = LineageNodeRef(
        node_type=LineageNodeType.RUN,
        node_id="run:run-1",
        attributes={"run_id": "run-1"},
    )
    fragment = LineageGraphFragment(
        fragment_id="fragment-1",
        run_id="run-1",
        manifest_id="manifest-1",
        nodes=(batch_node, run_node),
        edges=(
            LineageEdge(
                edge_type=LineageEdgeType.PRODUCED_BY,
                source=batch_node,
                target=run_node,
                run_id="run-1",
                manifest_id="manifest-1",
            ),
        ),
    )

    bundle = MetadataLineageBundle(metadata=metadata, lineage_fragment=fragment)

    assert bundle.metadata.output.artifact_id == "bronze_batch:batch-1"
    assert bundle.metadata.output.lineage_fragment_id == "fragment-1"


def test_metadata_lineage_bundle_requires_produced_artifact_node() -> None:
    metadata = _make_bronze_metadata()
    fragment = LineageGraphFragment(
        fragment_id="fragment-1",
        run_id="run-1",
        manifest_id="manifest-1",
        nodes=(
            LineageNodeRef(
                node_type=LineageNodeType.BRONZE_BATCH,
                node_id="bronze_batch:batch-1",
                attributes={"batch_id": "batch-1"},
            ),
        ),
        edges=(),
    )

    with pytest.raises(ValueError, match="does not expose a produced artifact node"):
        MetadataLineageBundle(metadata=metadata, lineage_fragment=fragment)


def test_metadata_lineage_bundle_rejects_preexisting_artifact_id_mismatch() -> None:
    metadata = _make_bronze_metadata()
    metadata.output.artifact_id = "bronze_batch:other-batch"
    batch_node = LineageNodeRef(
        node_type=LineageNodeType.BRONZE_BATCH,
        node_id="bronze_batch:batch-1",
        attributes={"batch_id": "batch-1"},
    )
    run_node = LineageNodeRef(
        node_type=LineageNodeType.RUN,
        node_id="run:run-1",
        attributes={"run_id": "run-1"},
    )
    fragment = LineageGraphFragment(
        fragment_id="fragment-1",
        run_id="run-1",
        manifest_id="manifest-1",
        nodes=(batch_node, run_node),
        edges=(
            LineageEdge(
                edge_type=LineageEdgeType.PRODUCED_BY,
                source=batch_node,
                target=run_node,
                run_id="run-1",
                manifest_id="manifest-1",
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match=r"Sidecar output\.artifact_id does not match lineage fragment produced artifact",
    ):
        MetadataLineageBundle(metadata=metadata, lineage_fragment=fragment)


def test_metadata_lineage_bundle_rejects_preexisting_fragment_id_mismatch() -> None:
    metadata = _make_bronze_metadata()
    metadata.output.lineage_fragment_id = "fragment-other"
    batch_node = LineageNodeRef(
        node_type=LineageNodeType.BRONZE_BATCH,
        node_id="bronze_batch:batch-1",
        attributes={"batch_id": "batch-1"},
    )
    run_node = LineageNodeRef(
        node_type=LineageNodeType.RUN,
        node_id="run:run-1",
        attributes={"run_id": "run-1"},
    )
    fragment = LineageGraphFragment(
        fragment_id="fragment-1",
        run_id="run-1",
        manifest_id="manifest-1",
        nodes=(batch_node, run_node),
        edges=(
            LineageEdge(
                edge_type=LineageEdgeType.PRODUCED_BY,
                source=batch_node,
                target=run_node,
                run_id="run-1",
                manifest_id="manifest-1",
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match=r"Sidecar output\.lineage_fragment_id does not match lineage fragment fragment_id",
    ):
        MetadataLineageBundle(metadata=metadata, lineage_fragment=fragment)
