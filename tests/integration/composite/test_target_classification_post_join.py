"""Post-join target classification uses features that exist only after the join."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import polars as pl
import pytest

from iuphar_target_class.bioetl_input import project_target_fields
from iuphar_target_class.identifier_roles import MATCHING_POLICY_VERSION

from bioetl.application.composite.coalesce_policy import CoalescePolicyService
from bioetl.application.composite.conflict_resolver import ConflictResolverService
from bioetl.application.composite.helpers.merger_post_join_persist import (
    persist_and_build_result,
)
from bioetl.application.composite.merger_post_join import (
    finalize_post_join_context,
)
from bioetl.application.composite.helpers.target_classification_features import (
    project_gold_classification_frame,
)
from bioetl.application.composite.helpers.target_classification_stage import (
    CompositeTargetClassification,
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
from bioetl.domain.entities.target_classification_boundary import (
    TargetClassificationArtifactReference,
    TargetClassificationResult,
)

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
    return CompositeTargetClassification(session), classifier, evidence


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
            "target_id": ["CHEMBL1"],
            "effective_class": ["Enzyme"],
            "target_classification_owner": [COMPOSITE_CLASSIFICATION_OWNER],
            "other": ["keep"],
        }
    )

    schema = SimpleNamespace(
        columns={"target_id": object(), "effective_class": object()}
    )
    schema.to_schema = lambda: schema
    projected = project_gold_classification_frame(frame, schema)
    assert "target_classification_owner" not in projected.columns
    assert projected["effective_class"][0] == "Enzyme"
    assert projected["other"][0] == "keep"
