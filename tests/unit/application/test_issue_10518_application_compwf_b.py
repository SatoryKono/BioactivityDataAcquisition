"""Behavior tests closing #10518 residuals: composite+workflow area (part B)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from bioetl.application.composite.column_service import ColumnOrderService
from bioetl.application.composite.helpers.join_planner_identity import (
    extract_base_column,
    infer_pipeline_from_table,
    infer_silver_table,
    parse_pipeline_name,
    resolve_field_aliases_from_registry,
    table_path_to_name,
    try_parse_pipeline_identity,
)
from bioetl.application.composite.helpers.preflight_type_and_aggregation import (
    check_type_compatibility,
    dtype_in_group,
    validate_aggregation_ordering,
)
from bioetl.application.composite.join_key_normalization import (
    build_join_key_normalization_expr,
    iter_configured_join_keys,
    normalize_join_key_dataframe_columns,
    validate_join_key_normalization_policies,
)
from bioetl.application.composite.runner_pkg.runner_stage_mixin import (
    CompositeRunnerStageMixin,
)
from bioetl.domain.composite import CompositeConfig, DependencyConfig
from bioetl.domain.composite.aggregation import (
    AggregationConfig,
    AggregationFieldSpec,
    AggregationFunction,
    EnricherCardinality,
)
from bioetl.domain.composite.config_models import EnricherConfig, SeedConfig
from bioetl.domain.composite.config_schema import LayerColumnConfig
from bioetl.domain.composite.strategy import ConflictResolution, MergeStrategy
from bioetl.domain.exceptions import BioETLError
from bioetl.domain.normalization.join_keys import JoinKeyNormalizationPolicy

pytestmark = pytest.mark.unit


def _logger() -> MagicMock:
    return MagicMock()


# --- column_service ---

def test_order_column_names_empty_returns_empty() -> None:
    svc = ColumnOrderService(logger=_logger())
    assert svc.order_column_names([]) == []


def test_order_column_names_yaml_groups_branch() -> None:
    from bioetl.domain.composite import ColumnGroupConfig

    svc = ColumnOrderService(
        logger=_logger(),
        column_groups=(ColumnGroupConfig(name="g", fields=("title",)),),
    )
    with patch(
        "bioetl.application.composite.column_service.order_by_yaml_groups",
        return_value=["title"],
    ) as fn:
        assert svc.order_column_names(["title"]) == ["title"]
        fn.assert_called_once()


def test_order_column_names_semantic_branch() -> None:
    svc = ColumnOrderService(logger=_logger())
    with patch(
        "bioetl.application.composite.column_service.get_ordered_columns",
        return_value=["a", "b"],
    ):
        assert svc.order_column_names(["b", "a"]) == ["a", "b"]


def test_column_service_static_delegates() -> None:
    assert ColumnOrderService._apply_renames(["a"], {"a": "b"}) == ["b"]
    assert ColumnOrderService._apply_renames_stage(["a"], {"a": "b"}) == ["b"]
    assert ColumnOrderService.get_enricher_prefix("chembl_activity") == "chembl.activity."
    assert ColumnOrderService.get_enricher_prefix("badname") == "badname_"
    assert ColumnOrderService._parse_pipeline_name("chembl_activity") == (
        "chembl",
        "activity",
    )


def test_filter_by_layer_config_delegates() -> None:
    svc = ColumnOrderService(logger=_logger())
    cfg = LayerColumnConfig(columns=("a", "b"))
    assert svc.filter_by_layer_config(["a", "b", "c"], cfg) == ["a", "b"]


# --- join_planner_identity ---

def test_try_parse_identity_invalid() -> None:
    assert try_parse_pipeline_identity("badname") is None


def test_try_parse_identity_valid() -> None:
    rec = try_parse_pipeline_identity("chembl_activity_extra")
    assert rec is not None and rec.provider == "chembl"


def test_resolve_aliases_no_identity_returns_none() -> None:
    assert resolve_field_aliases_from_registry("badname") is None


def test_resolve_aliases_empty_map_returns_none() -> None:
    with patch(
        "bioetl.application.composite.helpers.join_planner_identity.get_alias_map_for_provider",
        return_value={},
    ):
        assert resolve_field_aliases_from_registry("chembl_activity") is None


def test_resolve_aliases_returns_map() -> None:
    with patch(
        "bioetl.application.composite.helpers.join_planner_identity.get_alias_map_for_provider",
        return_value={"a": "b"},
    ):
        assert resolve_field_aliases_from_registry("chembl_activity") == {"a": "b"}


def test_parse_pipeline_name_raises_without_separator() -> None:
    with pytest.raises(ValueError, match="provider_entity"):
        parse_pipeline_name("badname")


def test_table_path_to_name_layers_and_passthrough() -> None:
    assert table_path_to_name("x/silver/chembl/activity") == "chembl/activity"
    assert table_path_to_name("x/gold/a/b") == "a/b"
    assert table_path_to_name("x/bronze/a") == "a"
    assert table_path_to_name("plain") == "plain"
    assert table_path_to_name("a\\silver\\b\\c") == "b/c"


def test_infer_silver_table_both_branches() -> None:
    assert infer_silver_table("chembl_activity") == "silver/chembl/activity"
    assert infer_silver_table("badname") == "silver/badname"


def test_infer_pipeline_from_table_branches() -> None:
    assert infer_pipeline_from_table("weird/path") is None
    assert infer_pipeline_from_table("silver/chembl/activity") == "chembl_activity"
    assert infer_pipeline_from_table("silver/only") is None


def test_extract_base_column() -> None:
    assert extract_base_column("chembl.title", "chembl.") == "title"
    assert extract_base_column("title", "chembl.") is None


# --- preflight_type_and_aggregation ---

def test_dtype_in_group_case_insensitive() -> None:
    assert dtype_in_group("STR", frozenset({"str"})) is True
    assert dtype_in_group("int", frozenset({"str"})) is False


def test_check_type_compatibility_branches() -> None:
    assert check_type_compatibility("f", {"a": "int", "b": "float"}) is None
    issue = check_type_compatibility("f", {"a": "str", "b": "int"})
    assert issue is not None
    assert issue.severity == "error" and issue.field == "f"


def _agg_config(**kw: Any) -> CompositeConfig:
    merge = SimpleNamespace(
        field_priorities={}, normalization_compatibility_overrides={}
    )
    seed = SimpleNamespace(pipeline="chembl_activity")
    enrichers = kw.pop("enrichers", ())
    return SimpleNamespace(
        enrichers=enrichers, merge=merge, seed=seed, dependencies=()
    )


def _many_to_one_enricher(**kw: Any) -> SimpleNamespace:
    agg = kw.pop("aggregation", None)
    pipeline = kw.pop("pipeline", "e1")
    return SimpleNamespace(
        pipeline=pipeline, is_many_to_one=True, aggregation=agg, **kw
    )


def test_validate_aggregation_no_enrichers() -> None:
    assert validate_aggregation_ordering(_agg_config()) == []  # type: ignore[arg-type]


def test_validate_aggregation_skips_one_to_one_and_missing() -> None:
    one_to_one = SimpleNamespace(
        pipeline="e", is_many_to_one=False, aggregation=None
    )
    missing_agg = SimpleNamespace(
        pipeline="e", is_many_to_one=True, aggregation=None
    )
    config = _agg_config(enrichers=(one_to_one, missing_agg))
    assert validate_aggregation_ordering(config) == []  # type: ignore[arg-type]


def test_validate_aggregation_flags_order_sensitive_without_order() -> None:
    agg = AggregationConfig(
        group_by="molecule_id",
        fields=(AggregationFieldSpec(
            source_field="term", agg_function=AggregationFunction.COLLECT_LIST
        ),),
    )
    config = _agg_config(enrichers=(_many_to_one_enricher(aggregation=agg),))
    issues = validate_aggregation_ordering(config)  # type: ignore[arg-type]
    assert len(issues) == 1
    assert issues[0].issue_type == "missing_deterministic_order"


def test_validate_aggregation_ok_with_order_by_or_insensitive() -> None:
    agg_ordered = AggregationConfig(
        group_by="molecule_id",
        fields=(AggregationFieldSpec(
            source_field="term", agg_function=AggregationFunction.COLLECT_LIST
        ),),
        order_by=("term",),
    )
    agg_count = AggregationConfig(
        group_by="molecule_id",
        fields=(AggregationFieldSpec(
            source_field="n", agg_function=AggregationFunction.COUNT
        ),),
    )
    config = _agg_config(
        enrichers=(
            _many_to_one_enricher(aggregation=agg_ordered),
            _many_to_one_enricher(pipeline="e2", aggregation=agg_count),
        )
    )
    assert validate_aggregation_ordering(config) == []  # type: ignore[arg-type]


def test_real_aggregation_models_cover_branches() -> None:
    enricher = EnricherConfig(
        pipeline="e_agg",
        join_keys=("molecule_id",),
        cardinality=EnricherCardinality.MANY_TO_ONE,
        aggregation={
            "group_by": "molecule_id",
            "fields": [{"source_field": "t", "agg_function": "first"}],
        },
    )
    assert enricher.is_many_to_one is True
    assert enricher.aggregation is not None
    assert enricher.aggregation.fields[0].effective_output_field == "t"


# --- join_key_normalization ---

def _join_config() -> CompositeConfig:
    seed = SeedConfig(
        pipeline="chembl_activity",
        output_keys=("molecule_id", "doi", "pmid"),
        silver_table="silver/chembl/activity",
    )
    from bioetl.domain.composite.config_models import MergeConfig

    merge = MergeConfig(
        strategy=MergeStrategy.LEFT_OUTER,
        conflict_resolution=ConflictResolution.SEED_PRIORITY,
        output_silver_path="s",
        output_gold_path="g",
    )
    return CompositeConfig(
        name="c",
        version="1",
        seed=seed,
        enrichers=(
            EnricherConfig(pipeline="e1_x", join_keys=("doi",)),
        ),
        dependencies=(
            DependencyConfig(pipeline="d1_y", join_keys=("pmid",)),
        ),
        merge=merge,
    )


def test_iter_configured_join_keys() -> None:
    assert set(iter_configured_join_keys(_join_config())) == {"doi", "pmid"}


def test_validate_policies_ok_and_missing() -> None:
    validate_join_key_normalization_policies(_join_config())
    bad = _join_config()
    object.__setattr__(
        bad.enrichers[0], "join_keys", ("no_such_key_xyz",)
    )
    with pytest.raises(ValueError, match="without normalization policy"):
        validate_join_key_normalization_policies(bad)


def test_build_expr_none_for_unknown_and_noop() -> None:
    assert build_join_key_normalization_expr(column="c", key="no_such_key_xyz") is None
    assert build_join_key_normalization_expr(column="c", key="molecule_id") is None


def test_build_expr_trim_only_and_canonicalizer() -> None:
    expr = build_join_key_normalization_expr(column="canonical_smiles", key="canonical_smiles")
    assert expr is not None
    expr2 = build_join_key_normalization_expr(column="doi", key="doi")
    assert expr2 is not None
    df = pl.DataFrame({"doi": ["  HTTPS://DOI.ORG/10.1/X  "]})
    out = normalize_join_key_dataframe_columns(
        df=df, join_keys=["doi"]
    )
    assert out["doi"][0] != "  HTTPS://DOI.ORG/10.1/X  "


def test_build_expr_lowercase_branch_without_canonicalizer() -> None:
    policies = {"mykey": JoinKeyNormalizationPolicy(trim=True, lowercase=True)}
    expr = build_join_key_normalization_expr(
        column="mykey", key="mykey", normalization_policies=policies
    )
    assert expr is not None
    df = pl.DataFrame({"mykey": ["  AbC  "]})
    out = normalize_join_key_dataframe_columns(
        df=df, join_keys=["mykey"], normalization_policies=policies
    )
    assert out["mykey"][0] == "abc"


def test_normalize_passthrough_when_no_expressions() -> None:
    df = pl.DataFrame({"molecule_id": [1]})
    out = normalize_join_key_dataframe_columns(df=df, join_keys=["molecule_id"])
    assert out.equals(df)
    out2 = normalize_join_key_dataframe_columns(df=df, join_keys=["absent_key"])
    assert out2.equals(df)


# --- runner_stage_mixin ---

class _Host(CompositeRunnerStageMixin):
    pass


def _host(**attrs: Any) -> _Host:
    host = _Host.__new__(_Host)
    for key, value in attrs.items():
        setattr(host, key, value)
    return host


async def test_skip_dependencies_phase_returns_state() -> None:
    host = _host()
    state = MagicMock()
    out_state, results = await host._skip_dependencies_phase(state)
    assert out_state is state and results == {}


async def test_execute_dependencies_phase_skips_when_unconfigured() -> None:
    host = _host()
    state = MagicMock()
    host._has_dependencies_configured = MagicMock(return_value=False)  # type: ignore[attr-defined]
    host._skip_dependencies_phase = AsyncMock(return_value=(state, {}))  # type: ignore[method-assign]
    out = await host._execute_dependencies_phase(state, pl.DataFrame({"a": [1]}))
    assert out == (state, {})
    host._skip_dependencies_phase.assert_awaited_once_with(state)


async def test_execute_dependencies_phase_full_flow() -> None:
    host = _host()
    state, context, keys = MagicMock(), MagicMock(), pl.DataFrame({"a": [1]})
    host._has_dependencies_configured = MagicMock(return_value=True)  # type: ignore[attr-defined]
    host._prepare_dependencies_run_context = MagicMock(return_value=context)  # type: ignore[method-assign]
    host._start_dependencies_phase = AsyncMock(return_value=state)  # type: ignore[method-assign]
    host._execute_started_dependencies_phase = AsyncMock(  # type: ignore[method-assign]
        return_value=(state, {"d": 1})
    )
    out = await host._execute_dependencies_phase(state, keys)
    assert out == (state, {"d": 1})


async def test_execute_started_phase_success_and_error() -> None:
    host = _host()
    state, context = MagicMock(), MagicMock()
    host._run_dependencies = AsyncMock(return_value={"d": 1})  # type: ignore[method-assign]
    host._postprocess_dependency_results = AsyncMock(  # type: ignore[method-assign]
        return_value=(state, {"d": 1})
    )
    out = await host._execute_started_dependencies_phase(
        state, context=context, keys_df=pl.DataFrame({"a": [1]})
    )
    assert out == (state, {"d": 1})

    boom = BioETLError("fail")
    host2 = _host()
    host2._run_dependencies = AsyncMock(side_effect=boom)  # type: ignore[method-assign]
    host2._handle_dependencies_phase_exception = AsyncMock()  # type: ignore[method-assign]
    with pytest.raises(BioETLError):
        await host2._execute_started_dependencies_phase(
            state, context=context, keys_df=pl.DataFrame({"a": [1]})
        )
    host2._handle_dependencies_phase_exception.assert_awaited_once_with(state, boom)


async def test_handle_dependencies_phase_exception_delegates() -> None:
    host = _host()
    state, err = MagicMock(), ValueError("x")
    with patch(
        "bioetl.application.composite.runner_pkg.runner_stage_mixin.handle_dependencies_phase_exception",
        new=AsyncMock(),
    ) as fn:
        await host._handle_dependencies_phase_exception(state, err)
        fn.assert_awaited_once_with(host, state, err)
