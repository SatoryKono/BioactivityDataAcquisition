"""Post-join target classification uses features that exist only after the join."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import polars as pl
from deltalake import DeltaTable
import pytest

from iuphar_target_class.bioetl_input import project_target_fields
from iuphar_target_class.identifier_roles import MATCHING_POLICY_VERSION

from bioetl.application.composite.coalesce_policy import CoalescePolicyService
from bioetl.application.composite.conflict_resolver import ConflictResolverService
from bioetl.application.composite.helpers.merger_post_join_persist import (
    persist_and_build_result,
)
from bioetl.application.composite.helpers.target_classification_values import (
    source_hashes,
)
from bioetl.application.composite.merger_post_join import (
    finalize_post_join_context,
)
from bioetl.application.composite.helpers.target_classification_bundle import (
    feature_bundle,
)
from bioetl.application.composite.helpers.target_classification_features import (
    project_gold_classification_frame,
)
from bioetl.application.composite.helpers.target_classification_stage import (
    CompositeTargetClassification,
    commit_joined_classification,
)
from bioetl.application.pipelines.chembl.target_protein_classification_summary import (
    agreed_chembl_release,
)
from bioetl.application.services.target_runtime.classification import (
    TargetClassificationRunState,
)
from bioetl.domain.config.target_classification import TARGET_CLASSIFICATION_FIELDS
from bioetl.domain.composite import MergeConfig
from bioetl.domain.composite.enriched_target_features import (
    COMPOSITE_CLASSIFICATION_OWNER,
    hierarchy_fields_are_equivalent,
)
from bioetl.domain.contracts.gold.composite import CompositeTargetGoldSchema
from bioetl.domain.entities.target_classification_boundary import (
    TargetClassificationArtifactReference,
    TargetClassificationResult,
)

from bioetl.domain.types.gold_contracts import GoldWriteCategory
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.storage.gold_writer import GoldWriter

pytestmark = pytest.mark.integration

_PROFILE = "a" * 64
_SOURCE_HASH = "b" * 64
_STARTED = datetime(2026, 11, 23, tzinfo=UTC)


class _Classifier:
    def __init__(self) -> None:
        self.seen: list[dict[str, object]] = []
        self.run_ids: list[str] = []
        self.profile_sha256 = _PROFILE
        self.snapshot_manifest_sha256 = "c" * 64
        self.snapshot_id = "snapshot"
        self.immutable_uri = "memory://snapshot"

    def classify_record(
        self,
        business_data: dict[str, object],
        *,
        input_row_id: str,
        run_id: str,
        run_started_at: str,
    ) -> TargetClassificationResult:
        del run_started_at
        self.run_ids.append(run_id)
        self.seen.append(dict(business_data))
        ec = business_data.get("target_ec_numbers")
        local = "Enzyme" if isinstance(ec, str) and "3.4.21.5" in ec else None
        projection = dict.fromkeys(TARGET_CLASSIFICATION_FIELDS)
        projection["iuphar_match_status"] = "not_found"
        projection["local_class"] = local
        projection["effective_class"] = local
        projection["effective_source"] = "local" if local else None
        projection["decision_status"] = "resolved" if local else None
        projection["target_class_profile_sha256"] = self.profile_sha256
        projection["local_status"] = "resolved" if local else None
        return TargetClassificationResult(input_row_id, projection)


class _Evidence:
    def __init__(self) -> None:
        self.events: list[tuple[object, ...]] = []

    def publish_result(
        self,
        result: TargetClassificationResult,
        *,
        run_id: str,
        batch_id: str,
    ) -> TargetClassificationArtifactReference:
        self.events.append(("publish", run_id, batch_id, result.input_row_id))
        return TargetClassificationArtifactReference("memory://row", "d" * 64)

    def finalize_run(
        self, *, run_id: str, expected_row_ids: tuple[str, ...]
    ) -> TargetClassificationArtifactReference:
        self.events.append(("finalize", run_id, expected_row_ids))
        return TargetClassificationArtifactReference("memory://run", "e" * 64)


def _stage(
    mode: str = "enrich",
    *,
    table_contract: str = "3.1.0",
) -> tuple[CompositeTargetClassification, _Classifier, _Evidence]:
    classifier = _Classifier()
    evidence = _Evidence()
    session = TargetClassificationRunState(
        classifier=classifier,  # type: ignore[arg-type]
        evidence=evidence,  # type: ignore[arg-type]
        mode=mode,  # type: ignore[arg-type]
        normalization_version="bioetl-iuphar-input-v1",
        rules_version="plan-v1-r8",
        classification_schema_version="3.1.0",
        matching_policy_version=MATCHING_POLICY_VERSION,
    )
    return (
        CompositeTargetClassification(session, table_contract=table_contract),
        classifier,
        evidence,
    )


def _resolver() -> ConflictResolverService:
    config = MergeConfig(
        strategy="left_outer",
        conflict_resolution="seed_priority",
        output_silver_path="silver/composite/target",
        output_gold_path="gold/composite/target",
    )
    return ConflictResolverService(
        config,
        MagicMock(),
        CoalescePolicyService(MagicMock()),
    )


def _host(stage: CompositeTargetClassification) -> MagicMock:
    host = MagicMock()
    resolver = _resolver()
    host._target_classification_stage = stage
    host.target_post_join_classifier.side_effect = AssertionError(
        "duplicate classification"
    )
    host._logger = MagicMock()
    host._conflict_resolver.resolve_conflicts.side_effect = (
        lambda df, _enricher_dfs, enrichers, seed_pipeline=None: (
            resolver.resolve_conflicts(
                df=df,
                _enricher_dfs=_enricher_dfs,
                enrichers=enrichers,
                seed_pipeline=seed_pipeline,
            )
        )
    )
    host._order_service.order_columns.side_effect = lambda df: df
    host._run_cross_validation.side_effect = lambda **kwargs: (
        kwargs["merged_df"],
        None,
        [],
    )
    host._apply_field_mappings.side_effect = lambda df: df
    host._add_lineage.side_effect = lambda df, **kwargs: df
    host._drop_excluded_fields.side_effect = lambda df: df
    host._count_enriched_records.return_value = 1
    host._write_outputs = AsyncMock()
    host._build_merge_result.return_value = MagicMock(records_merged=1)
    return host


def _joined_frame() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "target_id": ["CHEMBL1"],
            "chembl.target.target_type": ["SINGLE PROTEIN"],
            "chembl.target.pref_name": ["Thrombin"],
            "chembl.target.taxonomy_id": ["9606"],
            "chembl.target.organism": ["Homo sapiens"],
            "chembl.target.effective_class": ["Receptor"],
            "chembl.target_protein_classification.target_protein_class_name_L1": [
                "Enzyme"
            ],
            "uniprot.idmapping.uniprot_accession": ["P00734"],
            "uniprot.protein.protein_ec_numbers": ['["3.4.21.5"]'],
            "uniprot.protein.keywords": ['[{"id":"KW-0645","name":"Hydrolase"}]'],
        }
    )


def _seed_frame() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "target_id": ["CHEMBL1"],
            "chembl.target.target_type": ["SINGLE PROTEIN"],
            "chembl.target.pref_name": ["Thrombin"],
            "chembl.target.taxonomy_id": ["9606"],
            "chembl.target.organism": ["Homo sapiens"],
            "chembl.target.effective_class": ["Receptor"],
        }
    )


def test_joined_feature_is_used_and_survives_seed_priority() -> None:
    stage, classifier, _evidence = _stage()
    before, before_classifier, _before_evidence = _stage()
    before.apply(
        _seed_frame(),
        run_id="run-before",
        started_at=_STARTED,
        dependency_frames=None,
    )
    assert "target_ec_numbers" not in before_classifier.seen[0]
    before_origins = {
        item["feature_id"]: item
        for item in before_classifier.seen[0]["feature_origins"]
    }
    assert before_origins["ec"]["present"] is False

    dependencies = {
        "uniprot_protein": pl.DataFrame(
            {
                "uniprot_accession": ["P00734"],
                "content_hash": [_SOURCE_HASH],
            }
        )
    }
    ctx = finalize_post_join_context(
        _host(stage),
        merged_df=_joined_frame(),
        enrichers=(),
        enrichment_results={},
        effective_seed_pipeline="chembl_target",
        run_id="run-1",
        metadata_timestamp=_STARTED,
        sources_used=["seed"],
        dependency_results=None,
        enricher_dfs={},
        dependency_dfs=dependencies,
        classification_started_at=_STARTED,
    )
    row = ctx.merged_df.to_dicts()[0]
    payload = classifier.seen[0]
    assert payload["target_ec_numbers"] == '["3.4.21.5"]'
    assert "predicted_l1" not in payload
    assert "chembl.target.effective_class" not in payload
    assert payload["controlled_keyword_ids"] == ["KW-0645"]
    assert payload["hierarchy_field_mapping"][0]["equivalent_by_name"] is False
    origins = {item["feature_id"]: item for item in payload["feature_origins"]}
    assert origins["ec"]["present"] is True
    assert origins["ec"]["source_content_hash"] == _SOURCE_HASH
    assert "P00734" in (project_target_fields(payload, "9606")["uniprot"] or "")
    assert row["effective_class"] == "Enzyme"
    assert row["target_classification_owner"] == COMPOSITE_CLASSIFICATION_OWNER
    assert row["target_classification_completeness"] == "full"
    assert row["content_hash"]


def test_missing_optional_dependencies_stay_limited() -> None:
    stage, classifier, _evidence = _stage()
    result = stage.apply(
        _seed_frame(),
        run_id="run-limited",
        started_at=_STARTED,
    )
    row = result.to_dicts()[0]
    assert row["target_classification_completeness"] == "limited"
    assert "ec" in row["target_classification_absent_features"]
    assert "target_ec_numbers" not in classifier.seen[0]
    assert "controlled_keyword_ids" not in classifier.seen[0]
    assert "protein_hierarchy" not in classifier.seen[0]


def test_uncontrolled_keyword_text_is_not_passed() -> None:
    stage, classifier, _evidence = _stage()
    frame = _seed_frame().with_columns(
        pl.lit('[{"name":"kinase"}]').alias("uniprot.protein.keywords")
    )
    result = stage.apply(frame, run_id="run-keywords", started_at=_STARTED)
    assert "controlled_keyword_ids" not in classifier.seen[0]
    origins = {
        item["feature_id"]: item for item in classifier.seen[0]["feature_origins"]
    }
    assert origins["keywords"]["status"] == "uncontrolled_ignored"
    assert "ec" in result["target_classification_absent_features"][0]


def test_repeat_run_is_deterministic() -> None:
    first, _classifier, _evidence = _stage()
    second, _other, _other_evidence = _stage()
    kwargs = {
        "run_id": "run-repeat",
        "started_at": _STARTED,
        "dependency_frames": None,
    }
    left = first.apply(_joined_frame(), **kwargs).sort("target_id")
    right = second.apply(_joined_frame(), **kwargs).sort("target_id")
    assert left.to_dicts() == right.to_dicts()


@pytest.mark.asyncio
async def test_persistence_failure_does_not_publish_completion() -> None:
    stage, _classifier, evidence = _stage()
    host = _host(stage)
    host._write_outputs.side_effect = RuntimeError("disk full")
    frame = stage.apply(_joined_frame(), run_id="run-fail", started_at=_STARTED)
    with pytest.raises(RuntimeError, match="disk full"):
        await persist_and_build_result(
            host,
            merged_df=frame,
            enrichers=(),
            records_merged=1,
            records_from_seed=1,
            records_enriched=1,
            sources_used=["seed"],
            cv_stats=None,
            quarantine_payloads=[],
            metadata_timestamp=_STARTED,
            run_id="run-fail",
            started_at=_STARTED,
            started_monotonic=1.0,
        )
    assert evidence.events == []


@pytest.mark.asyncio
async def test_successful_write_publishes_then_finalizes() -> None:
    stage, _classifier, evidence = _stage()
    host = _host(stage)
    frame = stage.apply(_joined_frame(), run_id="run-ok", started_at=_STARTED)
    await persist_and_build_result(
        host,
        merged_df=frame,
        enrichers=(),
        records_merged=1,
        records_from_seed=1,
        records_enriched=1,
        sources_used=["seed"],
        cv_stats=None,
        quarantine_payloads=[],
        metadata_timestamp=_STARTED,
        run_id="run-ok",
        started_at=_STARTED,
        started_monotonic=1.0,
    )
    assert [event[0] for event in evidence.events] == ["publish", "finalize"]
    occurrence = "run-ok.composite-target-classification"
    assert evidence.events[0][1] == occurrence
    assert evidence.events[1][1] == occurrence
    assert _classifier.run_ids == [occurrence]
    assert evidence.events[1][2] == ("composite.target:CHEMBL1",)


def test_shadow_mode_keeps_seed_class_columns() -> None:
    stage, classifier, _evidence = _stage("shadow")
    frame = _joined_frame()
    result = stage.apply(frame, run_id="run-shadow", started_at=_STARTED)
    assert "effective_class" not in result.columns
    assert result["chembl.target.effective_class"][0] == "Receptor"
    assert result["target_classification_owner"][0] == COMPOSITE_CLASSIFICATION_OWNER
    assert classifier.run_ids == ["run-shadow.composite-target-classification"]


def test_invalid_keyword_json_is_not_invented() -> None:
    stage, classifier, _evidence = _stage()
    frame = _seed_frame().with_columns(
        pl.lit("[not-json").alias("uniprot.protein.keywords")
    )
    result = stage.apply(frame, run_id="run-bad-json", started_at=_STARTED)
    origins = {
        item["feature_id"]: item for item in classifier.seen[0]["feature_origins"]
    }
    assert origins["keywords"]["status"] == "uncontrolled_ignored"
    assert "controlled_keyword_ids" not in classifier.seen[0]
    assert result["target_classification_completeness"][0] == "limited"


def test_historical_l1_is_not_the_modern_chembl_field() -> None:
    assert (
        hierarchy_fields_are_equivalent(
            "L1",
            "chembl.target_protein_classification.target_protein_class_name_L1",
            chembl_release="ChEMBL_36",
        )
        is False
    )
    assert agreed_chembl_release(["ChEMBL_36", "ChEMBL_36"]) == (
        "ChEMBL_36",
        "unique",
    )
    assert agreed_chembl_release(["ChEMBL_35", "ChEMBL_36"]) == (None, "conflict")
    assert agreed_chembl_release([None, 36]) == (None, "unbound")


def test_null_classification_fields_are_not_restored_from_seed() -> None:
    stage, _classifier, _evidence = _stage()
    frame = _seed_frame().with_columns(
        pl.lit("123").alias("chembl.target.iuphar_target_id"),
        pl.lit("Receptor").alias("chembl.target.local_class"),
        pl.lit("matched").alias("chembl.target.iuphar_match_status"),
    )
    ctx = finalize_post_join_context(
        _host(stage),
        merged_df=frame,
        enrichers=(),
        enrichment_results={},
        effective_seed_pipeline="chembl_target",
        run_id="run-null",
        metadata_timestamp=_STARTED,
        sources_used=["seed"],
        dependency_results=None,
        enricher_dfs={},
    )
    row = ctx.merged_df.to_dicts()[0]
    assert row["iuphar_target_id"] is None
    assert row["local_class"] is None
    assert row["iuphar_match_status"] == "not_found"
    assert row["target_classification_owner"] == COMPOSITE_CLASSIFICATION_OWNER


def test_historical_replay_binding_skips_live_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bioetl.application.services.target_runtime.scope import (
        bind_target_classification_dependency,
        reset_target_classification_dependency,
    )
    from bioetl.composition.bootstrap.assembly.target_classification_runtime import (
        build_composite_target_classification_stage,
    )

    def fail(name: str) -> None:
        raise AssertionError(name)

    monkeypatch.setattr(
        "bioetl.composition.bootstrap.assembly.target_classification_runtime.load_pipeline_config",
        fail,
    )
    token = bind_target_classification_dependency({"replay_mode": "historical"})
    try:
        assert (
            build_composite_target_classification_stage(
                SimpleNamespace(name="composite_target")
            )
            is None
        )
    finally:
        reset_target_classification_dependency(token)


def test_gold_projection_keeps_unknown_columns_fail_closed() -> None:
    frame = pl.DataFrame(
        {
            "chembl.target.target_id": ["CHEMBL1"],
            **{column: ["value"] for column in TARGET_CLASSIFICATION_FIELDS},
            "target_class_profile_sha256": [_PROFILE],
            "target_classification_owner": [COMPOSITE_CLASSIFICATION_OWNER],
            "other": ["keep"],
        }
    )

    schema = CompositeTargetGoldSchema.to_schema()
    projected = project_gold_classification_frame(frame, CompositeTargetGoldSchema)

    assert "target_classification_owner" not in projected.columns
    assert projected["target_id"][0] == "CHEMBL1"
    assert projected.select(TARGET_CLASSIFICATION_FIELDS).equals(
        frame.select(TARGET_CLASSIFICATION_FIELDS)
    )
    assert all(
        schema.columns[column].nullable and not schema.columns[column].required
        for column in TARGET_CLASSIFICATION_FIELDS
    )
    assert schema.strict
    assert projected["other"][0] == "keep"


@pytest.mark.asyncio
@pytest.mark.parametrize("classified", [False, True])
async def test_composite_gold_persists_target_and_nullable_classification(
    tmp_path: Path, classified: bool
) -> None:
    classification = (
        dict.fromkeys(TARGET_CLASSIFICATION_FIELDS, "value") if classified else {}
    )
    if classified:
        classification["target_class_profile_sha256"] = _PROFILE
    row = {
        "entity_id": "chembl:CHEMBL1",
        "chembl.target.target_id": "CHEMBL1",
        "_source_providers": '["chembl"]',
        "_enrichment_status": "complete",
        **classification,
    }
    schema = CompositeTargetGoldSchema.to_schema()
    projected = project_gold_classification_frame(pl.DataFrame([row]), schema)
    writer = GoldWriter(base_path=tmp_path, logger=NoOpLogger())

    receipt = await writer.write_gold_merged(
        "composite/target", projected.to_dicts(), schema=schema
    )

    assert receipt.category == GoldWriteCategory.COMPLETE
    assert receipt.contract_version == "1.1.0"
    persisted = (
        DeltaTable(str(tmp_path / "composite/target")).to_pyarrow_table().to_pylist()
    )
    assert len(persisted) == 1
    assert persisted[0]["target_id"] == "CHEMBL1"
    assert {field: persisted[0][field] for field in TARGET_CLASSIFICATION_FIELDS} == {
        field: classification.get(field) for field in TARGET_CLASSIFICATION_FIELDS
    }


@pytest.mark.parametrize("empty_ec", [[], "[]", '["  ", "unknown"]'])
def test_ec_fallback_uses_seed_provenance_and_keeps_synonyms(empty_ec: object) -> None:
    seed_hash, protein_hash = "a" * 64, "b" * 64
    bundle = feature_bundle(
        {
            "target_id": "CHEMBL1",
            "uniprot_accession": "P00734",
            "uniprot.protein.protein_ec_numbers": empty_ec,
            "chembl.target.target_ec_numbers": ["3.4.21.5"],
            "chembl.target.target_protein_synonyms": "Protein alias",
            "chembl.target.target_gene_synonyms": "Gene alias",
        },
        {
            ("chembl_target", "CHEMBL1"): seed_hash,
            ("uniprot_protein", "P00734"): protein_hash,
        },
    )
    business = bundle["business"]
    assert (
        project_target_fields(business, None)["synonyms"] == "Protein alias|Gene alias"
    )
    assert project_target_fields(business, None)["ec"] == "3.4.21.5"
    ec = next(
        origin for origin in business["feature_origins"] if origin["feature_id"] == "ec"
    )
    assert ec["qualified_column"] == "chembl.target.target_ec_numbers"
    assert ec["source_pipeline"] == "chembl_target"
    assert ec["source_content_hash"] == seed_hash


@pytest.mark.parametrize(
    "xref_column",
    ["target_xref_uniprot_ids", "chembl.target.target_xref_uniprot_ids"],
)
def test_seed_auxiliary_xrefs_remain_diagnostic_after_join(xref_column: str) -> None:
    from iuphar_target_class.matching import CatalogTarget
    from iuphar_target_class.models import RawTargetRow, RunProvenance
    from iuphar_target_class.pipeline import IndexedSnapshot, classify_batch

    bundle = feature_bundle(
        {
            "target_id": "CHEMBL1",
            "chembl.target.component_accessions": ["P11111"],
            xref_column: ["P11111", "Q88888"],
        },
        {},
    )
    fields = project_target_fields(bundle["business"], "9606")
    snapshot = IndexedSnapshot.build(
        snapshot_id="fixture",
        mapping_version="fixture-release",
        complete=True,
        catalog=(
            CatalogTarget("1", ("P11111",), None, None, "9606", (), ()),
            CatalogTarget("2", ("Q88888",), None, None, "9606", (), ()),
        ),
        annotations={},
        family_nodes=(),
        type_to_class={},
        family_to_class={},
    )
    result = (
        classify_batch(
            (RawTargetRow("joined", fields, "protein"),),
            snapshot=snapshot,
            provenance=RunProvenance("fixture", "base", "rules", "schema", "t", "t"),
            run_id="fixture",
        )
        .rows[0]
        .result
    )
    assert result.match_status == "matched"
    assert result.matched_target_id == "1"
    assert "auxiliary_uniprot_divergence" in {
        entry.code for entry in result.diagnostics
    }
    assert fields["uniprot_equivalent"] == "P11111"
    assert fields["uniprot"] == "P11111"


@pytest.mark.parametrize(
    "column", ["target_xref_hgnc_ids", "chembl.target.target_xref_hgnc_ids"]
)
def test_seed_hgnc_remains_an_identity_anchor_after_join(column: str) -> None:
    from iuphar_target_class.identifier_roles import ANCHOR_PRIORITY_POLICY_VERSION
    from iuphar_target_class.matching import CatalogTarget
    from iuphar_target_class.models import RawTargetRow, RunProvenance
    from iuphar_target_class.pipeline import IndexedSnapshot, classify_batch

    bundle = feature_bundle(
        {
            "target_id": "CHEMBL1",
            "chembl.target.taxonomy_id": "9606",
            column: "HGNC:101",
        },
        {},
    )
    fields = project_target_fields(bundle["business"], "9606")
    snapshot = IndexedSnapshot.build(
        snapshot_id="fixture",
        mapping_version="fixture-release",
        complete=True,
        catalog=(
            CatalogTarget("1", (), None, None, "9606", (), (), hgnc_ids=("101",)),
        ),
        annotations={},
        family_nodes=(),
        type_to_class={},
        family_to_class={},
    )
    provenance = RunProvenance(
        "fixture",
        "base",
        "rules",
        "schema",
        "t",
        "t",
        matching_policy_version=ANCHOR_PRIORITY_POLICY_VERSION,
    )
    row = classify_batch(
        (RawTargetRow("joined", fields, "protein"),),
        snapshot=snapshot,
        provenance=provenance,
        run_id="fixture",
    ).rows[0]
    assert row.result.match_status == "matched"
    assert row.result.matched_target_id == "1"
    assert row.match_methods == ("hgnc",)


def test_hierarchy_origins_use_level_columns_and_all_relation_hashes() -> None:
    pipeline = "chembl_target_protein_classification"
    frame = pl.DataFrame(
        {"target_id": ["CHEMBL1", "CHEMBL1"], "content_hash": ["a" * 64, "b" * 64]}
    )
    hashes = source_hashes({pipeline: frame})
    assert hashes == source_hashes({pipeline: frame.reverse()})
    assert hashes[(pipeline, "CHEMBL1")] not in ("a" * 64, "b" * 64)
    prefix = "chembl.target_protein_classification.target_protein_class_"
    columns = {prefix + "id_L2": "21", prefix + "desc_L2": "Class label"}
    business = feature_bundle({"target_id": "CHEMBL1", **columns}, hashes)["business"]
    hierarchy = [
        origin
        for origin in business["feature_origins"]
        if origin["feature_id"] == "protein_hierarchy"
    ]
    assert {origin["qualified_column"] for origin in hierarchy} == set(columns)
    assert {origin["source_content_hash"] for origin in hierarchy} == {
        hashes[(pipeline, "CHEMBL1")]
    }


def test_enrich_v32_seals_detail_values_and_nulls() -> None:
    stage, _classifier, _evidence = _stage(table_contract="3.2.0")
    result = stage.apply(_joined_frame(), run_id="run-v32", started_at=_STARTED)
    coalesced = result.with_columns(
        pl.lit("seed-status").alias("local_status"),
        pl.lit('["seed-rule"]').alias("local_rule_ids"),
    )
    sealed = stage.seal_decision(coalesced).row(0, named=True)
    assert sealed["local_status"] == "resolved"
    assert sealed["local_rule_ids"] is None


@pytest.mark.asyncio
async def test_evidence_publication_failure_keeps_failed_and_pending_rows() -> None:
    stage, _classifier, evidence = _stage()
    frame = pl.DataFrame({"target_id": ["CHEMBL1", "CHEMBL2", "CHEMBL3"]})
    stage.apply(frame, run_id="partial", started_at=_STARTED)
    original = evidence.publish_result

    def fail_second(result: TargetClassificationResult, **kwargs: str):
        if result.input_row_id == "composite.target:CHEMBL2":
            raise OSError("evidence write error")
        return original(result, **kwargs)

    evidence.publish_result = fail_second
    write = AsyncMock()
    with pytest.raises(OSError, match="evidence write error"):
        await commit_joined_classification(stage, "partial", write)
    evidence.publish_result = original
    stage.commit("partial")
    write.assert_awaited_once()
    assert [event[3] for event in evidence.events if event[0] == "publish"] == [
        "composite.target:CHEMBL1",
        "composite.target:CHEMBL2",
        "composite.target:CHEMBL3",
    ]


def test_finalization_failure_discards_detached_evidence() -> None:
    stage, _classifier, evidence = _stage()
    host = _host(stage)
    host._apply_field_mappings.side_effect = RuntimeError("finalization failed")
    with pytest.raises(RuntimeError, match="finalization failed"):
        finalize_post_join_context(
            host,
            merged_df=_joined_frame(),
            enrichers=(),
            enrichment_results={},
            effective_seed_pipeline="chembl_target",
            run_id="pre-write",
            metadata_timestamp=_STARTED,
            sources_used=[],
            dependency_results={},
            enricher_dfs={},
        )
    stage.commit("pre-write")
    assert [event for event in evidence.events if event[0] == "publish"] == []


def test_pinned_replay_classification_uses_supplied_settings(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    from bioetl.application.services.target_runtime.scope import (
        bind_target_classification_dependency,
        reset_target_classification_dependency,
    )
    from bioetl.composition.bootstrap.assembly import (
        target_classification_runtime as runtime,
    )
    from bioetl.infrastructure.config.settings_api import Settings

    stage, _classifier, _evidence = _stage()
    settings = Settings(data_dir=tmp_path / "replay")
    yaml_config = SimpleNamespace(
        target_classification=SimpleNamespace(
            mode="enrich", to_domain=lambda: SimpleNamespace(contract_version="3.2.0")
        )
    )
    monkeypatch.setattr(runtime, "hydrate_target_runtime_config", lambda _: yaml_config)
    monkeypatch.setattr(
        runtime,
        "resolve_target_classification_profile",
        lambda _: SimpleNamespace(resolved_yaml_config=yaml_config),
    )
    monkeypatch.setattr(
        runtime,
        "get_settings",
        MagicMock(side_effect=AssertionError("global settings")),
    )
    session = MagicMock(return_value=stage._session)
    monkeypatch.setattr(runtime, "build_target_classification_session", session)
    token = bind_target_classification_dependency(
        {"target_config": {"pipeline_name": "chembl_target"}}
    )
    try:
        assert (
            runtime.build_composite_target_classification_stage(
                SimpleNamespace(name="composite_target"), settings=settings
            )
            is not None
        )
    finally:
        reset_target_classification_dependency(token)
    session.assert_called_once_with(yaml_config, settings)
