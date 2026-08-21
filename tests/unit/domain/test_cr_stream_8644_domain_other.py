# pyright: reportArgumentType=false
"""Focused unit tests for CR Stream C / #8644 domain-other residuals."""

from __future__ import annotations

import math

import pytest

from bioetl.domain.composite import (
    AggregationConfig,
    AggregationFieldSpec,
    AggregationFunction,
    CompositeDQConfig,
    CompositeLineageMetadata,
    ConflictResolution,
    DQOverrideConfig,
    DataSchemaConfig,
    LayerColumnConfig,
    MergeConfig,
    MergeStrategy,
)
from bioetl.domain.composite.result_enrichment import EnrichmentResult, EnrichmentStatus
from bioetl.domain.composite.result_merge import MergeResult
from bioetl.domain.composite.result_seed_dependency import (
    DependencyResult,
    DependencyStatus,
    SeedResult,
)
from bioetl.domain.config.base_provider import BaseProviderConfig
from bioetl.domain.config.dq import DQConfig
from bioetl.domain.config.enum_loader import _normalize_coordinate
from bioetl.domain.config.pipeline import FieldPolicyConfig
from bioetl.domain.config.runtime import RuntimeConfig
from bioetl.domain.config.validation_config import ValidationConfig
from bioetl.domain.config.validation_rules import FieldValidation
from bioetl.domain.contracts.gold.uniprot import UNIPROT_MAPPING_STATUS_VALUES
from bioetl.domain.immutability import FrozenDict
from bioetl.domain.types import RunType
from bioetl.domain.types.dq_contracts import DQDisposition

pytestmark = pytest.mark.unit


def test_base_provider_config_hides_api_key_in_repr() -> None:
    cfg = BaseProviderConfig(base_url="https://example.com", api_key="secret-key")
    text = repr(cfg)
    assert "secret-key" not in text


def test_seed_and_dependency_results_reject_negative_counters() -> None:
    with pytest.raises(ValueError, match="records_extracted"):
        SeedResult(pipeline_name="p", records_extracted=-1)
    with pytest.raises(ValueError, match="duration_seconds"):
        DependencyResult(pipeline_name="p", duration_seconds=math.nan)


def test_merge_result_rejects_negative_and_inconsistent_counts() -> None:
    with pytest.raises(ValueError, match="records_merged"):
        MergeResult(records_merged=-1)
    with pytest.raises(ValueError, match="records_fully_enriched"):
        MergeResult(records_merged=1, records_enriched=1, records_fully_enriched=2)


def test_enrichment_result_bounds_errored_and_finite_duration() -> None:
    with pytest.raises(ValueError, match="records_errored"):
        EnrichmentResult(
            enricher_name="p",
            status=EnrichmentStatus.SUCCESS,
            records_input=1,
            records_errored=2,
        )
    with pytest.raises(ValueError, match="duration_seconds"):
        EnrichmentResult(
            enricher_name="p",
            status=EnrichmentStatus.SUCCESS,
            records_input=1,
            duration_seconds=math.inf,
        )
    with pytest.raises(ValueError, match="combined terminal counters"):
        EnrichmentResult(
            enricher_name="p",
            status=EnrichmentStatus.SUCCESS,
            records_input=2,
            records_enriched=1,
            records_not_found=1,
            records_errored=1,
        )


def test_merge_result_rejects_non_finite_duration() -> None:
    with pytest.raises(ValueError, match="duration_seconds must be finite"):
        MergeResult(records_merged=1, duration_seconds=math.nan)
    with pytest.raises(ValueError, match="duration_seconds must be finite"):
        MergeResult(records_merged=1, duration_seconds=math.inf)


def test_dependency_timeout_rejects_non_finite_timeout_seconds() -> None:
    with pytest.raises(ValueError, match="timeout_seconds"):
        DependencyResult.timeout(pipeline_name="dep", timeout_seconds=math.nan)
    with pytest.raises(ValueError, match="timeout_seconds"):
        DependencyResult.timeout(pipeline_name="dep", timeout_seconds=-1.0)


def test_layer_column_config_freezes_rename_fields() -> None:
    owned = {"a": "b"}
    cfg = LayerColumnConfig(columns=("x",), rename_fields=owned)
    owned["a"] = "mutated"
    assert cfg.rename_fields["a"] == "b"
    assert isinstance(cfg.rename_fields, FrozenDict)
    with pytest.raises(TypeError):
        cfg.rename_fields["c"] = "d"  # type: ignore[index]


def test_data_schema_rejects_unknown_layer() -> None:
    schema = DataSchemaConfig()
    with pytest.raises(ValueError, match="unsupported layer"):
        schema.get_layer_groups("bronze")


def test_composite_dq_and_merge_freeze_mappings() -> None:
    overrides = {
        "chembl": DQOverrideConfig(soft_fail_threshold=0.1, hard_fail_threshold=0.5)
    }
    dq = CompositeDQConfig(enricher_overrides=overrides)
    overrides["other"] = DQOverrideConfig()
    assert "other" not in dq.enricher_overrides
    with pytest.raises(TypeError):
        dq.enricher_overrides["x"] = DQOverrideConfig()  # type: ignore[index]

    priorities = {"title": ["chembl", "crossref"]}
    merge = MergeConfig(
        strategy=MergeStrategy.LEFT_OUTER,
        conflict_resolution=ConflictResolution.SEED_PRIORITY,
        output_silver_path="silver/x",
        output_gold_path="gold/x",
        field_priorities=priorities,
        field_mappings={"a": "b"},
        normalization_compatibility_overrides={"k": "v"},
    )
    priorities["title"] = ["mutated"]
    assert merge.field_priorities["title"] == ("chembl", "crossref")
    with pytest.raises(TypeError):
        merge.field_mappings["z"] = "y"  # type: ignore[index]


def test_aggregation_rejects_rhs_operators_and_bad_fields_type() -> None:
    with pytest.raises(ValueError, match="additional operators"):
        AggregationFieldSpec(
            source_field="term",
            agg_function=AggregationFunction.FIRST,
            filter_condition="term_type == a AND b",
        )
    with pytest.raises(ValueError, match="sequence"):
        AggregationConfig(
            group_by="id",
            fields="not-a-sequence",  # type: ignore[arg-type]
        )


def test_lineage_requires_identity_and_preserves_zero_seed() -> None:
    with pytest.raises(ValueError, match="_composite_run_id"):
        CompositeLineageMetadata.from_dict({"_composite_name": "n"})
    meta = CompositeLineageMetadata.from_dict(
        {
            "_composite_run_id": "run-1",
            "_composite_name": "pub",
            "_seed_record_id": 0,
        }
    )
    assert meta.seed_record_id == "0"
    with pytest.raises(TypeError):
        meta.enrichment_status["x"] = "y"  # type: ignore[index]


def test_field_validation_variant_parameters() -> None:
    with pytest.raises(ValueError, match="min_value"):
        FieldValidation(field="x", validation_type="range")
    with pytest.raises(ValueError, match="pattern"):
        FieldValidation(field="x", validation_type="pattern")
    with pytest.raises(ValueError, match="allowed"):
        FieldValidation(field="x", validation_type="enum")
    ok = FieldValidation(field="x", validation_type="range", min_value=0, max_value=1)
    assert ok.min_value == 0


def test_disposition_overrides_stored_as_tuple() -> None:
    cfg = DQConfig(disposition_overrides={"rule.a": DQDisposition.FAIL})
    assert cfg.disposition_overrides == (("rule.a", DQDisposition.FAIL),)
    assert isinstance(cfg.disposition_overrides, tuple)


def test_runtime_lock_ttl_and_debug_export_normalize() -> None:
    with pytest.raises(ValueError, match="lock_ttl"):
        RuntimeConfig(run_type=RunType.REBUILD, lock_ttl=0)
    cfg = RuntimeConfig(
        run_type=RunType.REBUILD,
        debug_export_formats=(" CSV ", "XLSX"),
    )
    assert cfg.debug_export_formats == ("csv", "xlsx")


def test_field_policy_freezes_boolean_vocab() -> None:
    true_vals = ["YES", "Y"]
    cfg = FieldPolicyConfig(
        field="flag",
        boolean_true_values=true_vals,
        boolean_false_values=("no",),
    )
    true_vals.append("mutated")
    assert cfg.boolean_true_values == ("yes", "y")


def test_enum_loader_blank_raises_value_error() -> None:
    with pytest.raises(ValueError, match="blank"):
        _normalize_coordinate("   ", label="name")


def test_validation_config_positive_bounds() -> None:
    with pytest.raises(ValueError, match="publication year"):
        ValidationConfig(min_publication_year=0, max_publication_year=2020)
    with pytest.raises(ValueError, match="max_pmid"):
        ValidationConfig(max_pmid=0)


def test_uniprot_mapping_status_values() -> None:
    assert set(UNIPROT_MAPPING_STATUS_VALUES) == {
        "found",
        "not_found",
        "error",
        "multiple",
    }


def test_runtime_lock_ttl_positive() -> None:
    with pytest.raises(ValueError, match="lock_ttl"):
        RuntimeConfig(run_type=RunType.REBUILD, lock_ttl=0)


def test_merge_result_duration_and_enriched_bounds() -> None:
    with pytest.raises(ValueError, match="duration_seconds"):
        MergeResult(records_merged=1, duration_seconds=-1.0)
    with pytest.raises(ValueError, match="records_enriched cannot exceed"):
        MergeResult(records_merged=1, records_enriched=2, records_fully_enriched=0)


def test_validation_config_positive_identifiers() -> None:
    with pytest.raises(ValueError, match="publication year"):
        ValidationConfig(min_publication_year=0, max_publication_year=2020)
    with pytest.raises(ValueError, match="max_pmid"):
        ValidationConfig(max_pmid=0)
    with pytest.raises(ValueError, match="max_taxonomy_id"):
        ValidationConfig(max_taxonomy_id=-5)


def test_field_group_registry_rejects_duplicate_base_and_column() -> None:
    from bioetl.domain.composite.field_groups_models import (
        FieldGroupDefinition,
        FieldGroupId,
        FieldMapping,
    )
    from bioetl.domain.composite.field_groups_registry import FieldGroupRegistry

    g0, g1 = list(FieldGroupId)[0], list(FieldGroupId)[1]
    fm_a = FieldMapping(base_name="title", provider_columns=("p_title",), group=g0)
    fm_b = FieldMapping(base_name="title", provider_columns=("q_title",), group=g1)
    with pytest.raises(ValueError, match="Duplicate field-group base_name"):
        FieldGroupRegistry(
            groups=(
                FieldGroupDefinition(
                    group_id=g0, display_name="A", include_in_gold=True, fields=(fm_a,)
                ),
                FieldGroupDefinition(
                    group_id=g1, display_name="B", include_in_gold=True, fields=(fm_b,)
                ),
            )
        )
    fm_c = FieldMapping(
        base_name="abstract", provider_columns=("shared_col",), group=g0
    )
    fm_d = FieldMapping(
        base_name="keywords", provider_columns=("shared_col",), group=g1
    )
    with pytest.raises(ValueError, match="Duplicate provider column"):
        FieldGroupRegistry(
            groups=(
                FieldGroupDefinition(
                    group_id=g0, display_name="A", include_in_gold=True, fields=(fm_c,)
                ),
                FieldGroupDefinition(
                    group_id=g1, display_name="B", include_in_gold=True, fields=(fm_d,)
                ),
            )
        )


def test_lineage_requires_identity_fields() -> None:
    from bioetl.domain.composite.lineage import CompositeLineageMetadata

    with pytest.raises(ValueError, match="_composite_run_id"):
        CompositeLineageMetadata.from_dict({"_composite_name": "c"})
    with pytest.raises(ValueError, match="_composite_name"):
        CompositeLineageMetadata.from_dict({"_composite_run_id": "r"})
    meta = CompositeLineageMetadata.from_dict(
        {
            "_composite_run_id": "run-1",
            "_composite_name": "composite",
            "_source_providers": ["chembl"],
            "_field_sources": {"title": "chembl"},
        }
    )
    assert meta.composite_run_id == "run-1"
    payload = meta.to_dict()
    assert payload["_field_sources"]["title"] == "chembl"


def test_seed_dependency_extra_counter_bounds() -> None:
    with pytest.raises(ValueError, match="records_silver"):
        SeedResult(pipeline_name="p", records_silver=-1)
    with pytest.raises(ValueError, match="keys_generated"):
        SeedResult(pipeline_name="p", keys_generated=-2)
    with pytest.raises(ValueError, match="records_silver"):
        DependencyResult(pipeline_name="p", records_silver=-1)


def test_dependency_result_factories_and_success() -> None:
    ok = DependencyResult.success(
        pipeline_name="dep",
        records_extracted=2,
        records_silver=2,
        duration_seconds=1.5,
    )
    assert ok.is_success is True
    assert ok.status is DependencyStatus.SUCCESS
    failed = DependencyResult.failed(pipeline_name="dep", error_message="boom")
    assert failed.is_success is False
    skipped = DependencyResult.skipped(pipeline_name="dep", reason="done")
    assert skipped.is_success is True
    timed = DependencyResult.timeout(pipeline_name="dep", timeout_seconds=3.0)
    assert timed.status is DependencyStatus.TIMEOUT
    assert timed.duration_seconds == 3.0
    with pytest.raises(ValueError, match="duration_seconds"):
        DependencyResult.timeout(
            pipeline_name="dep",
            timeout_seconds=1.0,
            duration_seconds=math.nan,
        )


def test_seed_result_success_and_duration_bounds() -> None:
    seed = SeedResult(pipeline_name="seed", records_silver=0, resumed=True)
    assert seed.is_success is True
    with pytest.raises(ValueError, match="duration_seconds"):
        SeedResult(pipeline_name="seed", duration_seconds=-0.1)


def test_composite_merge_column_groups_optional_via_public_decoder() -> None:
    """Exercise merge.column_groups None/empty/list paths without private imports."""
    from bioetl.domain.composite.config import (
        CompositeConfig,
        DependencyConfig,
        EnricherConfig,
        MergeConfig,
        SeedConfig,
        composite_from_dict,
    )

    base: dict[str, object] = {
        "name": "c",
        "version": "1",
        "seed": {"pipeline": "seed", "output_keys": ["id"], "silver_table": "s"},
        "dependencies": [
            {"pipeline": "dep", "join_keys": ["id"], "timeout_seconds": 1}
        ],
        "enrichers": [],
        "merge": {
            "strategy": "left_outer",
            "conflict_resolution": "seed_priority",
            "output_silver_path": "silver/c",
            "output_gold_path": "gold/c",
        },
    }

    def _load(payload: dict[str, object]) -> CompositeConfig:
        return composite_from_dict(
            payload,
            composite_cls=CompositeConfig,
            seed_cls=SeedConfig,
            dependency_cls=DependencyConfig,
            enricher_cls=EnricherConfig,
            merge_cls=MergeConfig,
        )

    cfg_missing = _load(base)
    assert cfg_missing.merge.column_groups == ()

    with_empty = dict(base)
    with_empty["merge"] = {**base["merge"], "column_groups": []}  # type: ignore[index]
    cfg_empty = _load(with_empty)
    assert cfg_empty.merge.column_groups == ()

    with_groups = dict(base)
    with_groups["merge"] = {
        **base["merge"],  # type: ignore[dict-item]
        "column_groups": [{"name": "ids", "fields": ["id"]}],
    }
    cfg_groups = _load(with_groups)
    assert len(cfg_groups.merge.column_groups) == 1
