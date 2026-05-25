"""Split owner tests for metadata coordinator lineage fragments."""

from __future__ import annotations

from tests.unit.application.services.test_metadata_coordinator import *  # noqa: F401,F403

class TestLineageFragments:
    """Tests for canonical lineage fragment assembly."""

    class _FakeGoldSchema:
        class Config:
            version = "7.0"
            strict = True

        @staticmethod
        def to_schema() -> object:
            class _Column:
                dtype = "string"
                nullable = False

            class _Schema:
                columns = {"compound_id": _Column()}

            return _Schema()

    def test_bronze_fragment_links_source_request_run_and_batch(self) -> None:
        context = RunContext.create(
            run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
            run_type=RunType.INCREMENTAL,
            started_at=_FIXED_TIME,
            provider="chembl",
            entity="activity",
            manifest_id="manifest-001",
            execution_fingerprint="fingerprint-001",
            config_hash="a" * 64,
            effective_config_hash="b" * 64,
            effective_config_artifact_id="artifact-001",
            dq_contract_compatibility_hash="dq-hash-001",
            contract_ref="chembl.activity",
            contract_version="1.0.0",
            contract_schema_hash="schema-hash-123",
            dq_policy_ref="chembl.dq.v1",
            rule_bundle_version="dq-rules.v1.0",
        )
        coordinator = MetadataCoordinator(context)
        input_data = BronzeMetadataInput(
            batch_id=BatchID(deterministic_uuid_from_callsite("replay-sensitive")),
            record_count=50,
            compressed_size=1024,
            output_path="v1/chembl/activity/2026-03-24/batch-1.jsonl.zst",
            started_at=_FIXED_TIME,
            completed_at=_FIXED_TIME,
            source_metadata=SourceMetadata(
                type="api",
                url="https://www.ebi.ac.uk/chembl/api/data/activity",
                query_string="assay_type=B",
                api_version="v33",
            ),
        )

        fragment = coordinator.build_bronze_lineage_fragment(input_data)

        node_types = {node.node_type for node in fragment.nodes}
        assert fragment.fragment_id.startswith("bronze:")
        assert fragment.manifest_id == "manifest-001"
        assert LineageNodeType.MANIFEST in node_types
        assert LineageNodeType.RUN in node_types
        assert LineageNodeType.SOURCE_SYSTEM in node_types
        assert LineageNodeType.SOURCE_REQUEST in node_types
        assert LineageNodeType.BRONZE_BATCH in node_types
        run = next(
            node for node in fragment.nodes if node.node_type == LineageNodeType.RUN
        )
        manifest = next(
            node
            for node in fragment.nodes
            if node.node_type == LineageNodeType.MANIFEST
        )
        assert run.attributes["contract_ref"] == "chembl.activity"
        assert run.attributes["execution_fingerprint"] == "fingerprint-001"
        assert run.attributes["config_hash"] == "a" * 64
        assert run.attributes["effective_config_hash"] == "b" * 64
        assert run.attributes["effective_config_artifact_id"] == "artifact-001"
        assert run.attributes["dq_contract_compatibility_hash"] == "dq-hash-001"
        assert run.attributes["contract_version"] == "1.0.0"
        assert run.attributes["contract_schema_hash"] == "schema-hash-123"
        assert run.attributes["dq_policy_ref"] == "chembl.dq.v1"
        assert run.attributes["rule_bundle_version"] == "dq-rules.v1.0"
        assert manifest.attributes["contract_ref"] == "chembl.activity"
        assert manifest.attributes["execution_fingerprint"] == "fingerprint-001"
        assert manifest.attributes["config_hash"] == "a" * 64
        assert manifest.attributes["effective_config_hash"] == "b" * 64
        assert manifest.attributes["effective_config_artifact_id"] == "artifact-001"
        assert manifest.attributes["dq_contract_compatibility_hash"] == "dq-hash-001"
        assert manifest.attributes["contract_version"] == "1.0.0"
        assert any(
            edge.edge_type == LineageEdgeType.PRODUCED_BY for edge in fragment.edges
        )
        assert any(
            edge.edge_type == LineageEdgeType.EXPLAINS for edge in fragment.edges
        )

    def test_bronze_fragment_id_is_stable_across_run_ids(self) -> None:
        """Bronze fragment identity must not depend on run_id."""
        batch_id = BatchID(deterministic_uuid_from_callsite("replay-sensitive"))
        input_data = BronzeMetadataInput(
            batch_id=batch_id,
            record_count=50,
            compressed_size=1024,
            output_path="v1/chembl/activity/2026-03-24/batch-1.jsonl.zst",
            started_at=_FIXED_TIME,
            completed_at=_FIXED_TIME,
            source_metadata=SourceMetadata(
                type="api",
                url="https://www.ebi.ac.uk/chembl/api/data/activity",
                query_string="assay_type=B",
                api_version="v33",
            ),
        )
        fragment_first = MetadataCoordinator(
            RunContext.create(
                run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
                run_type=RunType.INCREMENTAL,
                started_at=_FIXED_TIME,
                provider="chembl",
                entity="activity",
            )
        ).build_bronze_lineage_fragment(input_data)
        fragment_second = MetadataCoordinator(
            RunContext.create(
                run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
                run_type=RunType.INCREMENTAL,
                started_at=_FIXED_TIME,
                provider="chembl",
                entity="activity",
            )
        ).build_bronze_lineage_fragment(input_data)

        assert fragment_first.fragment_id == fragment_second.fragment_id

    def test_silver_fragment_uses_bronze_refs_and_transform_chain(self) -> None:
        context = RunContext.create(
            run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
            run_type=RunType.INCREMENTAL,
            started_at=_FIXED_TIME,
            provider="chembl",
            entity="activity",
            transform_version="2.1.0",
            transform_steps=("normalize", "validate"),
        )
        coordinator = MetadataCoordinator(context)
        bronze_ref = BronzeWriteResult(
            batch_id=BatchID(deterministic_uuid_from_callsite("replay-sensitive")),
            relative_path="chembl/activity/2026-03-24/batch-1.jsonl.zst",
            absolute_path="/data/output/bronze/chembl/activity/2026-03-24/batch-1.jsonl.zst",
            record_count=25,
            compressed_size=100,
            uncompressed_size=300,
            checksum_blake2="abc123",
        )
        input_data = SilverMetadataInput(
            table_path="/data/output/silver/chembl/activity",
            records=[{"id": 1, "_source_batch_id": str(bronze_ref.batch_id)}],
            primary_keys=["id"],
            mode=SilverWriteMode.MERGE,
            bronze_refs=[bronze_ref],
            version_after=7,
        )

        fragment = coordinator.build_silver_lineage_fragment(input_data)

        dataset_nodes = [
            node for node in fragment.nodes if node.node_type == LineageNodeType.DATASET
        ]
        transform_nodes = [
            node
            for node in fragment.nodes
            if node.node_type == LineageNodeType.TRANSFORM
        ]
        assert fragment.fragment_id.startswith("silver:")
        assert len(dataset_nodes) == 1
        assert dataset_nodes[0].node_id == "silver:chembl.activity@7"
        assert len(transform_nodes) == 2
        assert any(
            edge.edge_type == LineageEdgeType.DERIVED_FROM
            and edge.target.node_type == LineageNodeType.BRONZE_BATCH
            for edge in fragment.edges
        )
        assert any(
            edge.edge_type == LineageEdgeType.PRODUCED_BY
            and edge.target.node_type == LineageNodeType.TRANSFORM
            for edge in fragment.edges
        )

    def test_silver_fragment_id_is_stable_across_run_ids(self) -> None:
        """Silver fragment identity must not depend on run_id."""
        bronze_ref = BronzeWriteResult(
            batch_id=BatchID(deterministic_uuid_from_callsite("replay-sensitive")),
            relative_path="chembl/activity/2026-03-24/batch-1.jsonl.zst",
            absolute_path="/data/output/bronze/chembl/activity/2026-03-24/batch-1.jsonl.zst",
            record_count=25,
            compressed_size=100,
            uncompressed_size=300,
            checksum_blake2="abc123",
        )
        input_data = SilverMetadataInput(
            table_path="/data/output/silver/chembl/activity",
            records=[{"id": 1, "_source_batch_id": str(bronze_ref.batch_id)}],
            primary_keys=["id"],
            mode=SilverWriteMode.MERGE,
            bronze_refs=[bronze_ref],
            version_after=7,
        )
        fragment_first = MetadataCoordinator(
            RunContext.create(
                run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
                run_type=RunType.INCREMENTAL,
                started_at=_FIXED_TIME,
                provider="chembl",
                entity="activity",
                transform_version="2.1.0",
                transform_steps=("normalize", "validate"),
            )
        ).build_silver_lineage_fragment(input_data)
        fragment_second = MetadataCoordinator(
            RunContext.create(
                run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
                run_type=RunType.INCREMENTAL,
                started_at=_FIXED_TIME,
                provider="chembl",
                entity="activity",
                transform_version="2.1.0",
                transform_steps=("normalize", "validate"),
            )
        ).build_silver_lineage_fragment(input_data)

        assert fragment_first.fragment_id == fragment_second.fragment_id

    def test_silver_fragment_exposes_composite_source_and_cv_summary(self) -> None:
        context = RunContext.create(
            run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
            run_type=RunType.INCREMENTAL,
            started_at=_FIXED_TIME,
            provider="composite",
            entity="publication",
        )
        coordinator = MetadataCoordinator(context)
        input_data = SilverMetadataInput(
            table_path="/data/output/silver/composite/publication",
            records=[
                {
                    "id": 1,
                    "_source_providers": "['seed', 'crossref']",
                    "_enrichment_status": "{'crossref': 'success'}",
                    "_field_sources": "{'doi': 'seed', 'title': 'crossref'}",
                    "_seed_record_id": "seed-123",
                    "_cv_warn": True,
                },
                {
                    "id": 2,
                    "_field_sources": "{'abstract': 'crossref'}",
                    "_cv_error": True,
                    "_cv_quarantine": True,
                },
            ],
            primary_keys=["id"],
            mode=SilverWriteMode.DELETE,
            version_after=11,
            composite_run_id="comp-run-456",
        )

        fragment = coordinator.build_silver_lineage_fragment(input_data)

        silver_dataset = next(
            node
            for node in fragment.nodes
            if node.node_type == LineageNodeType.DATASET
            and node.node_id == "silver:composite.publication@11"
        )
        crossref_source = next(
            node
            for node in fragment.nodes
            if node.node_type == LineageNodeType.SOURCE_SYSTEM
            and node.node_id == "source_system:crossref"
        )

        assert silver_dataset.attributes["composite_run_id"] == "comp-run-456"
        assert silver_dataset.attributes["source_providers"] == ["seed", "crossref"]
        assert silver_dataset.attributes["provider_fields"] == {
            "crossref": ["abstract", "title"],
            "seed": ["doi"],
        }
        assert silver_dataset.attributes["cv_warn_count"] == 1
        assert silver_dataset.attributes["cv_error_count"] == 1
        assert silver_dataset.attributes["cv_quarantine_count"] == 1
        assert crossref_source.attributes["selected_fields"] == ["abstract", "title"]
        assert any(
            edge.edge_type == LineageEdgeType.DERIVED_FROM
            and edge.source.node_id == silver_dataset.node_id
            and edge.target.node_id == crossref_source.node_id
            for edge in fragment.edges
        )

    def test_gold_fragment_links_silver_refs_schema_and_transforms(self) -> None:
        context = RunContext.create(
            run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
            run_type=RunType.REBUILD,
            started_at=_FIXED_TIME,
            provider="chembl",
            entity="activity",
            transform_version="3.0.0",
            transform_steps=("merge", "rank"),
            manifest_id="manifest-002",
        )
        coordinator = MetadataCoordinator(context)
        silver_ref = SilverRef(
            table_name="chembl.activity",
            table_path="/data/output/silver/chembl/activity",
            delta_version=9,
        )
        input_data = GoldMetadataInput(
            table_path="/data/output/gold/chembl/activity",
            table_name="chembl.activity",
            records=[{"id": 1}],
            mode=GoldWriteMode.OVERWRITE,
            silver_refs=[silver_ref],
            gold_schema=self._FakeGoldSchema,
        )

        fragment = coordinator.build_gold_lineage_fragment(input_data)

        node_types = {node.node_type for node in fragment.nodes}
        assert fragment.fragment_id.startswith("gold:")
        assert LineageNodeType.DATASET in node_types
        assert LineageNodeType.SCHEMA in node_types
        assert LineageNodeType.TRANSFORM in node_types
        assert LineageNodeType.MANIFEST in node_types
        assert any(
            edge.edge_type == LineageEdgeType.DERIVED_FROM
            and edge.target.node_id == "silver:chembl.activity@9"
            for edge in fragment.edges
        )
        assert any(
            edge.edge_type == LineageEdgeType.USED_SCHEMA
            and edge.target.node_type == LineageNodeType.SCHEMA
            for edge in fragment.edges
        )
        assert any(
            edge.edge_type == LineageEdgeType.EXPLAINS for edge in fragment.edges
        )

    def test_gold_fragment_id_is_stable_across_run_ids(self) -> None:
        """Gold fragment identity must not depend on run_id."""
        input_data = GoldMetadataInput(
            table_path="/data/output/gold/chembl/activity",
            table_name="chembl.activity",
            records=[{"id": 1}],
            mode=GoldWriteMode.OVERWRITE,
            silver_refs=[
                SilverRef(
                    table_name="chembl.activity",
                    table_path="/data/output/silver/chembl/activity",
                    delta_version=9,
                )
            ],
            gold_schema=self._FakeGoldSchema,
        )
        fragment_first = MetadataCoordinator(
            RunContext.create(
                run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
                run_type=RunType.REBUILD,
                started_at=_FIXED_TIME,
                provider="chembl",
                entity="activity",
                transform_version="3.0.0",
                transform_steps=("merge", "rank"),
            )
        ).build_gold_lineage_fragment(input_data)
        fragment_second = MetadataCoordinator(
            RunContext.create(
                run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
                run_type=RunType.REBUILD,
                started_at=_FIXED_TIME,
                provider="chembl",
                entity="activity",
                transform_version="3.0.0",
                transform_steps=("merge", "rank"),
            )
        ).build_gold_lineage_fragment(input_data)

        assert fragment_first.fragment_id == fragment_second.fragment_id

    def test_gold_fragment_exposes_composite_source_and_cv_summary(self) -> None:
        context = RunContext.create(
            run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
            run_type=RunType.REBUILD,
            started_at=_FIXED_TIME,
            provider="composite",
            entity="publication",
            manifest_id="manifest-003",
        )
        coordinator = MetadataCoordinator(context)
        input_data = GoldMetadataInput(
            table_path="/data/output/gold/composite/publication",
            table_name="composite.publication",
            records=[
                {
                    "id": 1,
                    "_source_providers": "['seed', 'openalex']",
                    "_enrichment_status": "{'openalex': 'success'}",
                    "_field_sources": "{'title': 'openalex', 'doi': 'seed'}",
                    "_seed_record_id": "seed-001",
                    "_cv_warn": True,
                    "_cv_error": False,
                    "_cv_quarantine": False,
                },
                {
                    "id": 2,
                    "_field_sources": "{'abstract': 'openalex'}",
                    "_cv_warn": False,
                    "_cv_error": True,
                    "_cv_quarantine": True,
                },
            ],
            mode=GoldWriteMode.OVERWRITE,
            composite_run_id="comp-run-123",
            lineage_created_at=datetime(2026, 3, 24, 10, 0, tzinfo=UTC),
        )

        fragment = coordinator.build_gold_lineage_fragment(input_data)

        gold_dataset = next(
            node
            for node in fragment.nodes
            if node.node_type == LineageNodeType.DATASET
            and node.node_id == "gold:composite.publication"
        )
        openalex_source = next(
            node
            for node in fragment.nodes
            if node.node_type == LineageNodeType.SOURCE_SYSTEM
            and node.node_id == "source_system:openalex"
        )
        openalex_edge = next(
            edge
            for edge in fragment.edges
            if edge.edge_type == LineageEdgeType.DERIVED_FROM
            and edge.source.node_id == gold_dataset.node_id
            and edge.target.node_id == openalex_source.node_id
        )

        assert gold_dataset.attributes["composite_run_id"] == "comp-run-123"
        assert gold_dataset.attributes["composite_name"] == "composite.publication"
        assert gold_dataset.attributes["source_providers"] == ["seed", "openalex"]
        assert gold_dataset.attributes["seed_record_id"] == "seed-001"
        assert gold_dataset.attributes["field_sources"] == {
            "title": "openalex",
            "doi": "seed",
        }
        assert gold_dataset.attributes["provider_fields"] == {
            "openalex": ["abstract", "title"],
            "seed": ["doi"],
        }
        assert gold_dataset.attributes["cv_warn_count"] == 1
        assert gold_dataset.attributes["cv_error_count"] == 1
        assert gold_dataset.attributes["cv_quarantine_count"] == 1
        assert openalex_source.attributes["selected_fields"] == ["abstract", "title"]
        assert openalex_source.attributes["enrichment_status"] == "success"
        assert openalex_edge.attributes["selected_field_count"] == 2
        assert openalex_edge.attributes["enrichment_status"] == "success"

    def test_silver_metadata_bundle_keeps_metadata_and_fragment_aligned(
        self, coordinator: MetadataCoordinator
    ) -> None:
        input_data = SilverMetadataInput(
            table_path="/data/output/silver/chembl/activity",
            records=[{"id": 1, "_source_batch_id": "batch-001"}],
            primary_keys=["id"],
            mode=SilverWriteMode.MERGE,
            version_after=4,
            transform_steps=("normalize", "validate"),
        )

        bundle = coordinator.create_silver_metadata_bundle(input_data)

        assert isinstance(bundle, MetadataLineageBundleResult)
        assert bundle.metadata.lineage.source_batch_ids == ["batch-001"]
        assert bundle.metadata.lineage.transform_steps == ["normalize", "validate"]
        assert bundle.metadata.output.artifact_id == "silver:chembl.activity@4"
        assert (
            bundle.metadata.output.lineage_fragment_id
            == bundle.lineage_fragment.fragment_id
        )
        assert any(
            node.node_id == "silver:chembl.activity@4"
            for node in bundle.lineage_fragment.nodes
        )
        assert bundle.lineage_fragment.run_id == str(coordinator.run_context.run_id)

    def test_gold_metadata_bundle_keeps_schema_and_upstream_refs_aligned(
        self, coordinator: MetadataCoordinator
    ) -> None:
        input_data = GoldMetadataInput(
            table_path="/data/output/gold/chembl/activity",
            table_name="chembl.activity",
            records=[{"id": 1}],
            mode=GoldWriteMode.OVERWRITE,
            silver_refs=[
                SilverRef(
                    table_name="chembl.activity",
                    table_path="/data/output/silver/chembl/activity",
                    delta_version=12,
                )
            ],
            transform_steps=("merge",),
            gold_schema=self._FakeGoldSchema,
        )

        bundle = coordinator.create_gold_metadata_bundle(input_data)

        assert isinstance(bundle, MetadataLineageBundleResult)
        assert bundle.metadata.lineage.source_tables == {"chembl.activity": 12}
        assert bundle.metadata.lineage.transform_steps == ["merge"]
        assert bundle.metadata.output.artifact_id == "gold:chembl.activity"
        assert (
            bundle.metadata.output.lineage_fragment_id
            == bundle.lineage_fragment.fragment_id
        )
        assert any(
            edge.edge_type == LineageEdgeType.USED_SCHEMA
            for edge in bundle.lineage_fragment.edges
        )

    def test_bronze_metadata_bundle_sets_lineage_fragment_anchor(
        self, coordinator: MetadataCoordinator
    ) -> None:
        input_data = BronzeMetadataInput(
            batch_id=BatchID(deterministic_uuid_from_callsite("replay-sensitive")),
            record_count=10,
            compressed_size=512,
            output_path="v1/chembl/activity/2026-03-24/batch-1.jsonl.zst",
            started_at=_FIXED_TIME,
            completed_at=_FIXED_TIME,
        )

        bundle = coordinator.create_bronze_metadata_bundle(input_data)

        assert isinstance(bundle, MetadataLineageBundleResult)
        assert (
            bundle.metadata.output.artifact_id == f"bronze_batch:{input_data.batch_id}"
        )
        assert (
            bundle.metadata.output.lineage_fragment_id
            == bundle.lineage_fragment.fragment_id
        )
