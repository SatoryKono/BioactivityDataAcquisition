# pyright: reportArgumentType=false
"""Focused tests for CR stream residuals #8643/#8644/#8645."""

from __future__ import annotations

import math

import pytest

from bioetl.domain.behavior.staged_enforcement import (
    EnforcementPolicy,
    EnforcementStage,
)
from bioetl.domain.behavior.validation_helpers import validate_data
from bioetl.domain.behavior.value_validator import ValueValidator
from bioetl.domain.behavior._dq_serializer_html._renderers import (
    _render_raw_data_card,
    status_color_class,
)
from bioetl.domain.composite.result_enrichment import EnrichmentResult, EnrichmentStatus
from bioetl.domain.composite.result_merge import MergeResult
from bioetl.domain.composite.result_seed_dependency import DependencyResult, SeedResult
from bioetl.domain.config.base_provider import BaseProviderConfig
from bioetl.domain.value_objects import ActivityType

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
from bioetl.domain.composite.config_parsing import require_float
from bioetl.domain.config.dq import DQConfig
from bioetl.domain.config.enum_loader import _normalize_coordinate
from bioetl.domain.config.pipeline import FieldPolicyConfig
from bioetl.domain.config.runtime import RuntimeConfig
from bioetl.domain.config.validation_config import ValidationConfig
from bioetl.domain.config.validation_rules import FieldValidation
from bioetl.domain.contracts.gold.uniprot import UNIPROT_MAPPING_STATUS_VALUES
from bioetl.domain.immutability import FrozenDict
from bioetl.domain.types.dq_contracts import DQDisposition
from bioetl.domain.types import RunType

pytestmark = pytest.mark.unit


def test_enforcement_policy_defaults_keep_soft_fail_reachable() -> None:
    policy = EnforcementPolicy(
        check_name="x",
        current_stage=EnforcementStage.SOFT_FAIL,
    )
    assert policy.warning_threshold < policy.failure_threshold
    assert policy.get_effective_stage(0.0) == EnforcementStage.OBSERVE
    assert policy.get_effective_stage(0.6) == EnforcementStage.SOFT_FAIL
    assert policy.get_effective_stage(0.9) == EnforcementStage.HARD_FAIL


def test_enforcement_policy_rejects_inverted_thresholds() -> None:
    with pytest.raises(ValueError, match="warning_threshold must be strictly below"):
        EnforcementPolicy(
            check_name="x",
            current_stage=EnforcementStage.OBSERVE,
            failure_threshold=0.2,
            warning_threshold=0.5,
        )


def test_validate_data_rejects_empty_frozenset() -> None:
    with pytest.raises(ValueError, match="Data is empty"):
        validate_data(frozenset())


def test_value_validator_percent_inhibition_before_unit_path() -> None:
    validator = ValueValidator()
    ok, err = validator.validate_activity_value(
        50.0, ActivityType.PERCENT_INHIBITION, unit="nM"
    )
    assert ok is True
    assert err is None
    bad, err2 = validator.validate_activity_value(
        150.0, ActivityType.PERCENT_INHIBITION, unit="nM"
    )
    assert bad is False
    assert err2 is not None


def test_value_validator_rejects_non_finite_concentration_bounds() -> None:
    validator = ValueValidator()
    with pytest.raises(ValueError, match="finite"):
        validator.set_concentration_range("nM", math.nan, 10.0)
    with pytest.raises(ValueError, match="finite"):
        validator.set_concentration_range("nM", 0.0, math.inf)


def test_status_color_class_uses_warn_selector() -> None:
    assert status_color_class("warn") == "warn"
    assert status_color_class("warning") == "warn"


def test_render_raw_data_card_fail_soft_on_non_serializable() -> None:
    html = _render_raw_data_card({"value": {1, 2, 3}})
    assert "raw_data_not_serializable" in html or "Raw Report Data" in html


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


def test_require_float_rejects_non_finite() -> None:
    with pytest.raises(ValueError, match="finite"):
        require_float(math.nan, "x")
    with pytest.raises(ValueError, match="finite"):
        require_float(math.inf, "x")


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
