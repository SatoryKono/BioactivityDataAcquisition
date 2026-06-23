"""Unit tests for metadata_lineage_node_builders module."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from bioetl.application.services.lineage.metadata_lineage_node_builders import (
    build_fragment_id,
    build_semantic_fragment_id,
    bronze_batch_node_from_input,
    bronze_batch_nodes_for_silver,
    dedupe_nodes,
    fragment_timestamp,
    gold_dataset_node,
    manifest_edges,
    manifest_node,
    resolve_transform_metadata,
    run_node,
    schema_node,
    silver_dataset_node,
    silver_source_nodes,
    source_request_node,
    source_system_node,
    transform_edges,
    transform_nodes,
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


class TestFragmentTimestamp:
    """Tests for fragment_timestamp function."""

    def test_fragment_timestamp_first_non_none(self):
        """Test that first non-None timestamp is returned."""
        dt1 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        dt2 = datetime(2026, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
        result = fragment_timestamp(dt1, dt2, None)
        assert result == dt1

    def test_fragment_timestamp_all_none(self):
        """Test that current_utc_time is returned when all values are None."""
        result = fragment_timestamp(None, None, None)
        assert isinstance(result, datetime)


class TestBuildFragmentId:
    """Tests for build_fragment_id function."""

    def test_build_fragment_id_basic(self):
        """Test basic fragment ID building."""
        result = build_fragment_id("prefix", "part1", "part2", "part3")
        assert result.startswith("prefix:")
        assert len(result) == len("prefix:") + 12  # 12 char digest

    def test_build_fragment_id_with_none_parts(self):
        """Test fragment ID building with None parts."""
        result = build_fragment_id("prefix", "part1", None, "part3")
        assert result.startswith("prefix:")


class TestBuildSemanticFragmentId:
    """Tests for build_semantic_fragment_id function."""

    def test_build_semantic_fragment_id_basic(self):
        """Test semantic fragment ID building from nodes and edges."""
        node1 = LineageNodeRef(
            node_type=LineageNodeType.SOURCE_SYSTEM,
            node_id="source_system:chembl",
            label="chembl",
            attributes={},
        )
        node2 = LineageNodeRef(
            node_type=LineageNodeType.RUN,
            node_id="run:123",
            label="run",
            attributes={},
        )
        edge = LineageEdge(
            edge_type=LineageEdgeType.DERIVED_FROM,
            source=node1,
            target=node2,
            run_id="123",
            manifest_id="manifest-1",
            created_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            attributes={},
        )

        result = build_semantic_fragment_id(
            "prefix",
            nodes=[node1, node2],
            edges=[edge],
        )

        assert result.startswith("prefix:")
        assert len(result) == len("prefix:") + 12


class TestDedupeNodes:
    """Tests for dedupe_nodes function."""

    def test_dedupe_nodes_basic(self):
        """Test basic node deduplication."""
        node1 = LineageNodeRef(
            node_type=LineageNodeType.SOURCE_SYSTEM,
            node_id="source_system:chembl",
            label="chembl",
            attributes={"version": "1.0"},
        )
        node2 = LineageNodeRef(
            node_type=LineageNodeType.SOURCE_SYSTEM,
            node_id="source_system:chembl",
            label="chembl_v2",
            attributes={"version": "2.0"},
        )
        node3 = LineageNodeRef(
            node_type=LineageNodeType.SOURCE_SYSTEM,
            node_id="source_system:pubmed",
            label="pubmed",
            attributes={},
        )

        result = dedupe_nodes([node1, node2, node3])

        assert len(result) == 2
        result_ids = {node.node_id for node in result}
        assert "source_system:chembl" in result_ids
        assert "source_system:pubmed" in result_ids
        # Should keep the first occurrence
        chembl_node = [n for n in result if n.node_id == "source_system:chembl"][0]
        assert chembl_node.attributes["version"] == "1.0"


class TestRunNode:
    """Tests for run_node function."""

    def test_run_node_basic(self):
        """Test basic run node building."""
        run_context = RunContext(
            run_id="run-123",
            manifest_id="manifest-1",
            pipeline_name="test_pipeline",
            provider="chembl",
            entity="activity",
            run_type=RunType.INCREMENTAL,
            started_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            execution_fingerprint="abc123",
            config_hash="hash1",
            resolved_config_hash="hash2",
            effective_config_hash="hash3",
            effective_config_artifact_id="artifact-1",
            contract_ref="contract-1",
            contract_version="1.0",
            contract_schema_hash="schema-hash",
            dq_policy_ref="dq-policy",
            rule_bundle_version="1.0",
            dq_contract_compatibility_hash="compat-hash",
        )

        result = run_node(run_context)

        assert result.node_type == LineageNodeType.RUN
        assert result.node_id == "run:run-123"
        assert result.label == "test_pipeline"
        assert result.attributes["run_id"] == "run-123"
        assert result.attributes["pipeline_name"] == "test_pipeline"
        assert result.attributes["provider"] == "chembl"
        assert result.attributes["entity"] == "activity"


class TestManifestNode:
    """Tests for manifest_node function."""

    def test_manifest_node_with_manifest_id(self):
        """Test manifest node building with manifest_id."""
        run_context = RunContext(
            run_id="run-123",
            manifest_id="manifest-1",
            pipeline_name="test_pipeline",
            provider="chembl",
            entity="activity",
            run_type=RunType.INCREMENTAL,
            started_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            execution_fingerprint="abc123",
            config_hash="hash1",
            resolved_config_hash="hash2",
            effective_config_hash="hash3",
            effective_config_artifact_id="artifact-1",
            contract_ref="contract-1",
            contract_version="1.0",
            contract_schema_hash="schema-hash",
            dq_policy_ref="dq-policy",
            rule_bundle_version="1.0",
            dq_contract_compatibility_hash="compat-hash",
        )

        result = manifest_node(run_context)

        assert result is not None
        assert result.node_type == LineageNodeType.MANIFEST
        assert result.node_id == "manifest:manifest-1"
        assert result.attributes["manifest_id"] == "manifest-1"

    def test_manifest_node_without_manifest_id(self):
        """Test manifest node building without manifest_id."""
        run_context = RunContext(
            run_id="run-123",
            manifest_id=None,
            pipeline_name="test_pipeline",
            provider="chembl",
            entity="activity",
            run_type=RunType.INCREMENTAL,
            started_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            execution_fingerprint="abc123",
            config_hash="hash1",
            resolved_config_hash="hash2",
            effective_config_hash="hash3",
            effective_config_artifact_id="artifact-1",
            contract_ref="contract-1",
            contract_version="1.0",
            contract_schema_hash="schema-hash",
            dq_policy_ref="dq-policy",
            rule_bundle_version="1.0",
            dq_contract_compatibility_hash="compat-hash",
        )

        result = manifest_node(run_context)

        assert result is None


class TestManifestEdges:
    """Tests for manifest_edges function."""

    def test_manifest_edges_with_manifest(self):
        """Test manifest edges building with manifest node."""
        run_context = RunContext(
            run_id="run-123",
            manifest_id="manifest-1",
            pipeline_name="test_pipeline",
            provider="chembl",
            entity="activity",
            run_type=RunType.INCREMENTAL,
            started_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            execution_fingerprint="abc123",
            config_hash="hash1",
            resolved_config_hash="hash2",
            effective_config_hash="hash3",
            effective_config_artifact_id="artifact-1",
            contract_ref="contract-1",
            contract_version="1.0",
            contract_schema_hash="schema-hash",
            dq_policy_ref="dq-policy",
            rule_bundle_version="1.0",
            dq_contract_compatibility_hash="compat-hash",
        )
        manifest_node_ref = LineageNodeRef(
            node_type=LineageNodeType.MANIFEST,
            node_id="manifest:manifest-1",
            label="test_pipeline",
            attributes={},
        )
        run_node_ref = LineageNodeRef(
            node_type=LineageNodeType.RUN,
            node_id="run:run-123",
            label="test_pipeline",
            attributes={},
        )
        created_at = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        result = manifest_edges(
            manifest=manifest_node_ref,
            run=run_node_ref,
            created_at=created_at,
            run_context=run_context,
        )

        assert len(result) == 1
        assert result[0].edge_type == LineageEdgeType.EXPLAINS
        assert result[0].source == manifest_node_ref
        assert result[0].target == run_node_ref

    def test_manifest_edges_without_manifest(self):
        """Test manifest edges building without manifest node."""
        run_context = RunContext(
            run_id="run-123",
            manifest_id=None,
            pipeline_name="test_pipeline",
            provider="chembl",
            entity="activity",
            run_type=RunType.INCREMENTAL,
            started_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            execution_fingerprint="abc123",
            config_hash="hash1",
            resolved_config_hash="hash2",
            effective_config_hash="hash3",
            effective_config_artifact_id="artifact-1",
            contract_ref="contract-1",
            contract_version="1.0",
            contract_schema_hash="schema-hash",
            dq_policy_ref="dq-policy",
            rule_bundle_version="1.0",
            dq_contract_compatibility_hash="compat-hash",
        )
        run_node_ref = LineageNodeRef(
            node_type=LineageNodeType.RUN,
            node_id="run:run-123",
            label="test_pipeline",
            attributes={},
        )
        created_at = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        result = manifest_edges(
            manifest=None,
            run=run_node_ref,
            created_at=created_at,
            run_context=run_context,
        )

        assert len(result) == 0


class TestSourceSystemNode:
    """Tests for source_system_node function."""

    def test_source_system_node_basic(self):
        """Test basic source system node building."""
        run_context = RunContext(
            run_id="run-123",
            manifest_id="manifest-1",
            pipeline_name="test_pipeline",
            provider="chembl",
            entity="activity",
            run_type=RunType.INCREMENTAL,
            started_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            execution_fingerprint="abc123",
            config_hash="hash1",
            resolved_config_hash="hash2",
            effective_config_hash="hash3",
            effective_config_artifact_id="artifact-1",
            contract_ref="contract-1",
            contract_version="1.0",
            contract_schema_hash="schema-hash",
            dq_policy_ref="dq-policy",
            rule_bundle_version="1.0",
            dq_contract_compatibility_hash="compat-hash",
        )

        result = source_system_node(run_context=run_context, source_metadata=None)

        assert result.node_type == LineageNodeType.SOURCE_SYSTEM
        assert result.node_id == "source_system:chembl"
        assert result.label == "chembl"
        assert result.attributes["provider"] == "chembl"
        assert result.attributes["entity"] == "activity"
        assert result.attributes["source_type"] is None


class TestSourceRequestNode:
    """Tests for source_request_node function."""

    def test_source_request_node_without_metadata(self):
        """Test source request node building without source metadata."""
        run_context = RunContext(
            run_id="run-123",
            manifest_id="manifest-1",
            pipeline_name="test_pipeline",
            provider="chembl",
            entity="activity",
            run_type=RunType.INCREMENTAL,
            started_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            execution_fingerprint="abc123",
            config_hash="hash1",
            resolved_config_hash="hash2",
            effective_config_hash="hash3",
            effective_config_artifact_id="artifact-1",
            contract_ref="contract-1",
            contract_version="1.0",
            contract_schema_hash="schema-hash",
            dq_policy_ref="dq-policy",
            rule_bundle_version="1.0",
            dq_contract_compatibility_hash="compat-hash",
        )
        input_data = MagicMock()
        input_data.source_metadata = None
        input_data.query_string = None

        result = source_request_node(run_context=run_context, input_data=input_data)

        assert result is None


class TestBronzeBatchNodeFromInput:
    """Tests for bronze_batch_node_from_input function."""

    def test_bronze_batch_node_from_input_basic(self):
        """Test basic bronze batch node building from input."""
        run_context = RunContext(
            run_id="run-123",
            manifest_id="manifest-1",
            pipeline_name="test_pipeline",
            provider="chembl",
            entity="activity",
            run_type=RunType.INCREMENTAL,
            started_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            execution_fingerprint="abc123",
            config_hash="hash1",
            resolved_config_hash="hash2",
            effective_config_hash="hash3",
            effective_config_artifact_id="artifact-1",
            contract_ref="contract-1",
            contract_version="1.0",
            contract_schema_hash="schema-hash",
            dq_policy_ref="dq-policy",
            rule_bundle_version="1.0",
            dq_contract_compatibility_hash="compat-hash",
        )
        input_data = MagicMock()
        input_data.batch_id = "batch-123"
        input_data.output_path = "/data/bronze/activity"
        input_data.record_count = 1000
        input_data.compressed_size = 1024

        result = bronze_batch_node_from_input(
            run_context=run_context, input_data=input_data
        )

        assert result.node_type == LineageNodeType.BRONZE_BATCH
        assert result.node_id == "bronze_batch:batch-123"
        assert result.label == "chembl.activity"
        assert result.attributes["batch_id"] == "batch-123"
        assert result.attributes["provider"] == "chembl"
        assert result.attributes["entity"] == "activity"


class TestSilverDatasetNode:
    """Tests for silver_dataset_node function."""

    def test_silver_dataset_node_basic(self):
        """Test basic silver dataset node building."""
        run_context = RunContext(
            run_id="run-123",
            manifest_id="manifest-1",
            pipeline_name="test_pipeline",
            provider="chembl",
            entity="activity",
            run_type=RunType.INCREMENTAL,
            started_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            execution_fingerprint="abc123",
            config_hash="hash1",
            resolved_config_hash="hash2",
            effective_config_hash="hash3",
            effective_config_artifact_id="artifact-1",
            contract_ref="contract-1",
            contract_version="1.0",
            contract_schema_hash="schema-hash",
            dq_policy_ref="dq-policy",
            rule_bundle_version="1.0",
            dq_contract_compatibility_hash="compat-hash",
        )
        input_data = MagicMock()
        input_data.version_after = "1.0"
        input_data.table_path = "/data/silver/activity"

        result = silver_dataset_node(run_context=run_context, input_data=input_data)

        assert result.node_type == LineageNodeType.DATASET
        assert result.attributes["layer"] == "silver"
        assert result.attributes["provider"] == "chembl"
        assert result.attributes["entity"] == "activity"


class TestGoldDatasetNode:
    """Tests for gold_dataset_node function."""

    def test_gold_dataset_node_basic(self):
        """Test basic gold dataset node building."""
        run_context = RunContext(
            run_id="run-123",
            manifest_id="manifest-1",
            pipeline_name="test_pipeline",
            provider="chembl",
            entity="activity",
            run_type=RunType.INCREMENTAL,
            started_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            execution_fingerprint="abc123",
            config_hash="hash1",
            resolved_config_hash="hash2",
            effective_config_hash="hash3",
            effective_config_artifact_id="artifact-1",
            contract_ref="contract-1",
            contract_version="1.0",
            contract_schema_hash="schema-hash",
            dq_policy_ref="dq-policy",
            rule_bundle_version="1.0",
            dq_contract_compatibility_hash="compat-hash",
        )
        input_data = MagicMock()
        input_data.table_name = "activity"
        input_data.table_path = "/data/gold/activity"

        result = gold_dataset_node(run_context=run_context, input_data=input_data)

        assert result.node_type == LineageNodeType.DATASET
        assert result.attributes["layer"] == "gold"
        assert result.attributes["provider"] == "chembl"
        assert result.attributes["entity"] == "activity"


class TestSilverSourceNodes:
    """Tests for silver_source_nodes function."""

    def test_silver_source_nodes_empty(self):
        """Test silver source nodes with empty refs."""
        input_data = MagicMock()
        input_data.silver_refs = []

        result = silver_source_nodes(input_data)

        assert len(result) == 0


class TestSchemaNode:
    """Tests for schema_node function."""

    def test_schema_node_basic(self):
        """Test basic schema node building."""
        input_data = MagicMock()
        input_data.gold_schema = None

        result = schema_node(input_data)

        # With no schema metadata, should return None
        # This depends on extract_schema_metadata behavior
        assert result is None


class TestTransformNodes:
    """Tests for transform_nodes function."""

    def test_transform_nodes_basic(self):
        """Test basic transform nodes building."""
        run_context = RunContext(
            run_id="run-123",
            manifest_id="manifest-1",
            pipeline_name="test_pipeline",
            provider="chembl",
            entity="activity",
            run_type=RunType.INCREMENTAL,
            started_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            execution_fingerprint="abc123",
            config_hash="hash1",
            resolved_config_hash="hash2",
            effective_config_hash="hash3",
            effective_config_artifact_id="artifact-1",
            contract_ref="contract-1",
            contract_version="1.0",
            contract_schema_hash="schema-hash",
            dq_policy_ref="dq-policy",
            rule_bundle_version="1.0",
            dq_contract_compatibility_hash="compat-hash",
        )

        result = transform_nodes(
            run_context=run_context,
            transform_version="1.0",
            transform_steps=["step1", "step2", "step3"],
        )

        assert len(result) == 3
        assert all(node.node_type == LineageNodeType.TRANSFORM for node in result)


class TestTransformEdges:
    """Tests for transform_edges function."""

    def test_transform_edges_basic(self):
        """Test basic transform edges building."""
        run_context = RunContext(
            run_id="run-123",
            manifest_id="manifest-1",
            pipeline_name="test_pipeline",
            provider="chembl",
            entity="activity",
            run_type=RunType.INCREMENTAL,
            started_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            execution_fingerprint="abc123",
            config_hash="hash1",
            resolved_config_hash="hash2",
            effective_config_hash="hash3",
            effective_config_artifact_id="artifact-1",
            contract_ref="contract-1",
            contract_version="1.0",
            contract_schema_hash="schema-hash",
            dq_policy_ref="dq-policy",
            rule_bundle_version="1.0",
            dq_contract_compatibility_hash="compat-hash",
        )
        run_node_ref = LineageNodeRef(
            node_type=LineageNodeType.RUN,
            node_id="run:run-123",
            label="test_pipeline",
            attributes={},
        )
        transform1 = LineageNodeRef(
            node_type=LineageNodeType.TRANSFORM,
            node_id="transform:step1",
            label="step1",
            attributes={},
        )
        transform2 = LineageNodeRef(
            node_type=LineageNodeType.TRANSFORM,
            node_id="transform:step2",
            label="step2",
            attributes={},
        )
        created_at = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        result = transform_edges(
            run_context=run_context,
            run=run_node_ref,
            transforms=[transform1, transform2],
            created_at=created_at,
        )

        # Should have 2 EXECUTED_IN edges and 1 DERIVED_FROM edge
        assert len(result) == 3
        executed_in_edges = [
            e for e in result if e.edge_type == LineageEdgeType.EXECUTED_IN
        ]
        derived_from_edges = [
            e for e in result if e.edge_type == LineageEdgeType.DERIVED_FROM
        ]
        assert len(executed_in_edges) == 2
        assert len(derived_from_edges) == 1


class TestResolveTransformMetadata:
    """Tests for resolve_transform_metadata function."""

    def test_resolve_transform_metadata_basic(self):
        """Test basic transform metadata resolution."""
        run_context = RunContext(
            run_id="run-123",
            manifest_id="manifest-1",
            pipeline_name="test_pipeline",
            provider="chembl",
            entity="activity",
            run_type=RunType.INCREMENTAL,
            started_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            execution_fingerprint="abc123",
            config_hash="hash1",
            resolved_config_hash="hash2",
            effective_config_hash="hash3",
            effective_config_artifact_id="artifact-1",
            contract_ref="contract-1",
            contract_version="1.0",
            contract_schema_hash="schema-hash",
            dq_policy_ref="dq-policy",
            rule_bundle_version="1.0",
            dq_contract_compatibility_hash="compat-hash",
        )

        version, steps = resolve_transform_metadata(
            run_context=run_context,
            transform_version="1.0",
            transform_steps=["step1", "step2"],
        )

        assert isinstance(version, str)
        assert isinstance(steps, list)
        assert len(steps) == 2
