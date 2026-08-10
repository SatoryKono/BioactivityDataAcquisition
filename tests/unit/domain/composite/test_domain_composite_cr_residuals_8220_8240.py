# pyright: reportArgumentType=false
"""Residual closeout coverage for domain/composite CR-FULL #8220-#8240."""

from __future__ import annotations
import pytest
from bioetl.domain.composite import (
    CompositeConfig,
    CompositeDQConfig,
    DependencyConfig,
    DQOverrideConfig,
    EnricherConfig,
    LineageConfig,
    MergeConfig,
    SeedConfig,
    DataSchemaConfig,
    LayerColumnConfig,
    composite_from_dict,
    composite_to_dict,
    require_non_empty,
    validate_composite_config,
    validate_positive,
)
from bioetl.domain.composite.field_groups_models import (
    FieldGroupDefinition,
    FieldGroupId,
    FieldMapping,
)
from bioetl.domain.composite.field_groups_registry import FieldGroupRegistry
from bioetl.domain.composite.result_composite import CompositeResult
from bioetl.domain.composite.result_enrichment import EnrichmentResult, EnrichmentStatus
from bioetl.domain.composite.result_merge import MergeResult
from bioetl.domain.composite.result_seed_dependency import DependencyResult, SeedResult
from bioetl.domain.composite.strategy import ConflictResolution, MergeStrategy
from bioetl.domain.immutability import FrozenDict

pytestmark = pytest.mark.unit


def _seed():
    return SeedResult(pipeline_name="seed", records_silver=10)


def _merge():
    return MergeResult(records_merged=5, records_enriched=3)


def test_lineage_config_freezes_nested_mappings():
    nested = {"chembl": {"id": "chembl_id"}}
    cfg = LineageConfig(
        provider_lookup_fields=nested, track_source_for_fields=["title", "doi"]
    )
    nested["chembl"]["id"] = "mutated"
    assert dict(cfg.provider_lookup_fields["chembl"])["id"] == "chembl_id"
    assert cfg.track_source_for_fields == ("title", "doi")
    with pytest.raises(TypeError):
        cfg.provider_lookup_fields["x"] = {}


def test_data_schema_empty_groups_exclude_all():
    schema = DataSchemaConfig(
        column_groups=(), gold=LayerColumnConfig(include_groups=())
    )
    assert schema.get_layer_groups("gold") == ()
    assert schema.should_include_group("gold", "any") is False
    unrestricted = DataSchemaConfig(gold=LayerColumnConfig())
    assert unrestricted.should_include_group("gold", "any") is True


def test_dq_effective_override_threshold_order():
    with pytest.raises(ValueError, match="effective soft"):
        CompositeDQConfig(
            soft_fail_threshold=0.1,
            hard_fail_threshold=0.5,
            enricher_overrides={"e1": DQOverrideConfig(soft_fail_threshold=0.6)},
        )
    ok = CompositeDQConfig(
        soft_fail_threshold=0.1,
        hard_fail_threshold=0.5,
        enricher_overrides={"e1": DQOverrideConfig(soft_fail_threshold=0.2)},
    )
    assert ok.get_enricher_soft_threshold("e1") == 0.2


def test_merge_result_freezes_mappings_and_payloads():
    coverage = {"title": 0.9}
    lineage = {"ok": 1}
    payload = {"id": "q1"}
    result = MergeResult(
        records_merged=1,
        field_coverage=coverage,
        lineage_summary=lineage,
        quarantine_payloads=(payload,),
    )
    coverage["title"] = 0.1
    lineage["ok"] = 9
    payload["id"] = "mut"
    assert result.field_coverage["title"] == 0.9
    assert result.lineage_summary["ok"] == 1
    assert result.quarantine_payloads[0]["id"] == "q1"


def test_composite_result_nominal_and_failure_paths():
    dep_ok = DependencyResult.success("dep", 1, 1)
    enr_ok = EnrichmentResult.success("enr", records_input=10, records_enriched=8)
    good = CompositeResult(
        composite_name="c",
        composite_run_id="r1",
        seed_result=_seed(),
        dependency_results={"dep": dep_ok},
        enrichment_results={"enr": enr_ok},
        merge_result=_merge(),
        _required_dependencies=frozenset({"dep"}),
        _required_enrichers=frozenset({"enr"}),
    )
    assert good.is_success is True
    missing = CompositeResult(
        composite_name="c",
        composite_run_id="r2",
        seed_result=_seed(),
        dependency_results={},
        enrichment_results={"enr": enr_ok},
        merge_result=_merge(),
        _required_dependencies=frozenset({"dep"}),
        _required_enrichers=frozenset({"enr"}),
    )
    assert missing.is_success is False


def test_composite_result_maps_are_immutable():
    source = {"dep": DependencyResult.success("dep", 1, 1)}
    result = CompositeResult(
        composite_name="c",
        composite_run_id="r",
        seed_result=_seed(),
        dependency_results=source,
        merge_result=_merge(),
    )
    source["other"] = DependencyResult.failed("other", "x")
    assert "other" not in result.dependency_results
    assert isinstance(result.dependency_results, FrozenDict)


def test_registry_uses_enclosing_group_id():
    mapping = FieldMapping(
        base_name="title",
        provider_columns=("chembl.publication.title",),
        group=FieldGroupId.TRASH,
    )
    group = FieldGroupDefinition(
        group_id=FieldGroupId.BIBLIOGRAPHY, display_name="Bib", fields=(mapping,)
    )
    registry = FieldGroupRegistry(groups=(group,))
    assert registry.get_group("chembl.publication.title") is FieldGroupId.BIBLIOGRAPHY


def test_public_validators_are_exported():
    require_non_empty("x", "field")
    validate_positive(1, "n")


def test_coerce_and_validate_composite_config():
    seed = SeedConfig(pipeline="s", output_keys=("k",), silver_table="t")
    merge = MergeConfig(
        strategy=MergeStrategy.LEFT_OUTER,
        conflict_resolution=ConflictResolution.SEED_PRIORITY,
        output_silver_path="silver/x",
        output_gold_path="gold/x",
    )
    config = CompositeConfig(
        name="c",
        version="1",
        seed=seed,
        enrichers=[EnricherConfig(pipeline="e", join_keys=("k",))],
        merge=merge,
        dependencies=[],
    )
    assert isinstance(config.enrichers, tuple)
    validate_composite_config(config)
    with pytest.raises(ValueError, match="Duplicate enricher"):
        CompositeConfig(
            name="c",
            version="1",
            seed=seed,
            enrichers=(
                EnricherConfig(pipeline="e", join_keys=("k",)),
                EnricherConfig(pipeline="e", join_keys=("k",)),
            ),
            merge=merge,
        )


def test_composite_to_dict_from_dict_roundtrip_preserves_options():
    config = CompositeConfig(
        name="c",
        version="1.0",
        seed=SeedConfig(pipeline="s", output_keys=("k",), silver_table="t", limit=5),
        dependencies=(
            DependencyConfig(
                pipeline="dep",
                join_keys=("k",),
                required=True,
                timeout_seconds=120,
                key_source="seed",
            ),
        ),
        enrichers=(
            EnricherConfig(
                pipeline="e",
                join_keys=("k",),
                required=True,
                timeout_seconds=90,
                limit=3,
            ),
        ),
        merge=MergeConfig(
            strategy=MergeStrategy.LEFT_OUTER,
            conflict_resolution=ConflictResolution.SEED_PRIORITY,
            output_silver_path="silver/x",
            output_gold_path="gold/x",
            field_priorities={"title": ("chembl", "crossref")},
            preserve_all_sources=True,
        ),
        dq=CompositeDQConfig(soft_fail_threshold=0.05, hard_fail_threshold=0.2),
        lineage=LineageConfig(track_source_for_fields=("title",)),
    )
    payload = composite_to_dict(config)
    restored = composite_from_dict(
        payload,
        composite_cls=CompositeConfig,
        seed_cls=SeedConfig,
        dependency_cls=DependencyConfig,
        enricher_cls=EnricherConfig,
        merge_cls=MergeConfig,
    )
    assert restored.seed.limit == 5
    assert restored.dependencies[0].timeout_seconds == 120
    assert restored.enrichers[0].limit == 3
    assert restored.merge.preserve_all_sources is True
    assert restored.dq.soft_fail_threshold == 0.05
    assert restored.lineage.track_source_for_fields == ("title",)


def test_enrichment_result_factories_and_rates():
    ok = EnrichmentResult.success(
        "e", records_input=10, records_enriched=8, records_not_found=2
    )
    assert ok.enrichment_rate == 0.8
    assert ok.is_success is True
    failed = EnrichmentResult.failed("e", "boom", records_input=1)
    assert failed.status is EnrichmentStatus.FAILED
