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
"""Unit tests for sidecar/lineage bundle contract enforcement."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from tests.helpers.metadata_fixtures import build_bronze_metadata

from bioetl.application.services.lineage import MetadataLineageBundleResult
from bioetl.domain.lineage import (
    LineageEdge,
    LineageEdgeType,
    LineageGraphFragment,
    LineageNodeRef,
    LineageNodeType,
)
from bioetl.domain.models.metadata import BronzeMetadata


pytestmark = pytest.mark.unit


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


def _make_produced_fragment(
    *,
    artifact_id: str = "bronze_batch:batch-1",
    fragment_id: str = "fragment-1",
    manifest_id: str | None = "manifest-1",
) -> LineageGraphFragment:
    """Build one minimal fragment exposing a produced Bronze artifact node."""
    batch_node = LineageNodeRef(
        node_type=LineageNodeType.BRONZE_BATCH,
        node_id=artifact_id,
        attributes={"batch_id": artifact_id.split(":")[-1]},
    )
    run_node = LineageNodeRef(
        node_type=LineageNodeType.RUN,
        node_id="run:run-1",
        attributes={"run_id": "run-1"},
    )
    return LineageGraphFragment(
        fragment_id=fragment_id,
        run_id="run-1",
        manifest_id=manifest_id,
        nodes=(batch_node, run_node),
        edges=(
            LineageEdge(
                edge_type=LineageEdgeType.PRODUCED_BY,
                source=batch_node,
                target=run_node,
                run_id="run-1",
                manifest_id=manifest_id,
            ),
        ),
    )


def test_metadata_lineage_bundle_sets_output_artifact_id() -> None:
    metadata = _make_bronze_metadata()
    fragment = _make_produced_fragment()

    bundle = MetadataLineageBundleResult(metadata=metadata, lineage_fragment=fragment)

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
        MetadataLineageBundleResult(metadata=metadata, lineage_fragment=fragment)


def test_metadata_lineage_bundle_rejects_preexisting_artifact_id_mismatch() -> None:
    metadata = _make_bronze_metadata()
    metadata.output.artifact_id = "bronze_batch:other-batch"
    fragment = _make_produced_fragment()

    with pytest.raises(
        ValueError,
        match=r"Sidecar output\.artifact_id does not match lineage fragment produced artifact",
    ):
        MetadataLineageBundleResult(metadata=metadata, lineage_fragment=fragment)


def test_metadata_lineage_bundle_rejects_preexisting_fragment_id_mismatch() -> None:
    metadata = _make_bronze_metadata()
    metadata.output.lineage_fragment_id = "fragment-other"
    fragment = _make_produced_fragment()

    with pytest.raises(
        ValueError,
        match=r"Sidecar output\.lineage_fragment_id does not match lineage fragment fragment_id",
    ):
        MetadataLineageBundleResult(metadata=metadata, lineage_fragment=fragment)


def test_metadata_lineage_bundle_requires_runtime_manifest_id_for_strict_closure() -> (
    None
):
    metadata = _make_bronze_metadata()
    metadata.runtime.manifest_id = None
    fragment = _make_produced_fragment()

    with pytest.raises(
        ValueError,
        match=r"Strict sidecar lineage closure requires runtime\.manifest_id",
    ):
        MetadataLineageBundleResult(
            metadata=metadata,
            lineage_fragment=fragment,
            strict_manifest_id_required=True,
        )


def test_metadata_lineage_bundle_requires_fragment_manifest_id_for_strict_closure() -> (
    None
):
    metadata = _make_bronze_metadata()
    fragment = _make_produced_fragment(manifest_id=None)

    with pytest.raises(
        ValueError,
        match="Strict sidecar lineage closure requires lineage fragment manifest_id",
    ):
        MetadataLineageBundleResult(
            metadata=metadata,
            lineage_fragment=fragment,
            strict_manifest_id_required=True,
        )


def test_metadata_lineage_bundle_allows_legacy_missing_manifest_id_without_strict_closure() -> (
    None
):
    metadata = _make_bronze_metadata()
    metadata.runtime.manifest_id = None
    fragment = _make_produced_fragment(manifest_id=None)

    bundle = MetadataLineageBundleResult(
        metadata=metadata,
        lineage_fragment=fragment,
    )

    assert bundle.metadata.output.artifact_id == "bronze_batch:batch-1"


def test_bundle_does_not_mutate_caller_metadata() -> None:
    """Anchors attach to a copy; caller metadata stays clean for reuse (#8169)."""
    metadata = _make_bronze_metadata()
    metadata.output.lineage_fragment_id = None
    metadata.output.artifact_id = None
    fragment_a = _make_produced_fragment(
        artifact_id="bronze_batch:batch-a",
        fragment_id="fragment-a",
    )
    fragment_b = _make_produced_fragment(
        artifact_id="bronze_batch:batch-b",
        fragment_id="fragment-b",
    )

    bundle_a = MetadataLineageBundleResult(
        metadata=metadata,
        lineage_fragment=fragment_a,
    )
    bundle_b = MetadataLineageBundleResult(
        metadata=metadata,
        lineage_fragment=fragment_b,
    )

    assert metadata.output.lineage_fragment_id in (None, "")
    assert metadata.output.artifact_id in (None, "")
    assert bundle_a.metadata.output.lineage_fragment_id == "fragment-a"
    assert bundle_a.metadata.output.artifact_id == "bronze_batch:batch-a"
    assert bundle_b.metadata.output.lineage_fragment_id == "fragment-b"
    assert bundle_b.metadata.output.artifact_id == "bronze_batch:batch-b"
    assert bundle_a.metadata is not metadata
    assert bundle_b.metadata is not metadata
