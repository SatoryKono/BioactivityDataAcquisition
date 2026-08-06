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
"""Focused unit coverage for low-coverage composite helper modules."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import polars as pl
import pytest

pytestmark = pytest.mark.unit

from bioetl.application.composite import dependency_join_support
from bioetl.application.composite._preflight_orchestration import (
    PreflightSchemaOrchestrationMixin,
)
from bioetl.application.composite._preflight_schema_registry import (
    find_schema_class,
)
from bioetl.application.composite.aggregator import EnricherAggregator
from bioetl.application.composite.column_priority_orderer import (
    collect_priority_field_columns,
    order_priority_columns,
    resolve_by_column_scan,
    resolve_seed_column,
)
from bioetl.application.composite.cross_validator_helpers import (
    _build_enricher_detail,
    _combine_cv_details,
    _compare_field,
    _count_mismatches_vectorized,
)
from bioetl.domain.composite.aggregation import (
    AggregationConfig,
    AggregationFieldSpec,
    AggregationFunction,
)
from bioetl.domain.composite.config import EnricherConfig
from bioetl.domain.composite.cross_validation import (
    ComparisonMethod,
    EnricherFieldPairing,
    FieldComparisonSpec,
)


class _DummyPreflight(PreflightSchemaOrchestrationMixin):
    _logger = MagicMock()


class ExportedSchema:
    @staticmethod
    def to_schema() -> object:
        return object()


class _SchemaFromVars:
    class LocalSchema:
        @staticmethod
        def to_schema() -> object:
            return object()


_SchemaFromAll = SimpleNamespace(
    __all__=["ExportedSchema"], ExportedSchema=ExportedSchema
)


def test_dependency_join_support_exports_stay_bound_to_canonical_helpers() -> None:
    assert "execute_dependency_join" in dependency_join_support.__all__
    assert dependency_join_support.resolve_left_pipeline is not None
    assert dependency_join_support.CompositeJoinContext is not None


def test_column_priority_helpers_cover_seed_scan_and_fallback_paths() -> None:
    assert (
        resolve_seed_column(
            field="title", seed_provider="chembl", seed_entity="activity"
        )
        == "chembl.activity.title"
    )
    assert (
        resolve_seed_column(field="title", seed_provider=None, seed_entity="activity")
        is None
    )
    assert (
        resolve_by_column_scan(
            provider="crossref",
            field="title",
            columns_set={"crossref.publication.title", "pubmed.publication.title"},
        )
        == "crossref.publication.title"
    )

    enrichers = (
        EnricherConfig(pipeline="crossref_publication", join_keys=("doi",)),
        EnricherConfig(pipeline="legacycrossref", join_keys=("doi",)),
    )
    columns, used_fallback = collect_priority_field_columns(
        field="title",
        enrichers=enrichers,
        available_columns={
            "chembl.activity.title",
            "crossref.publication.title",
            "legacycrossref_title",
        },
        seed_pipeline="invalid-seed",
    )

    assert columns == ["crossref.publication.title", "legacycrossref_title"]
    assert used_fallback is True

    ordered, parse_fallback = order_priority_columns(
        field="title",
        columns=["crossref.publication.title", "chembl.activity.title"],
        priorities=("seed", "crossref"),
        seed_pipeline="chembl_activity",
    )
    assert ordered == ["chembl.activity.title", "crossref.publication.title"]
    assert parse_fallback is False


def test_preflight_orchestration_helpers_cover_schema_lookup_aliases_and_annotations() -> (
    None
):
    helper = _DummyPreflight()
    result: dict[str, dict[str, object]] = {}
    fields = {
        "doi": SimpleNamespace(
            name="doi", dtype="str", nullable=True, source="chembl.activity"
        )
    }

    helper._register_source_aliases(  # type: ignore[arg-type]
        result,
        pipeline_name="chembl_activity",
        fields=fields,
        is_seed=True,
    )
    assert helper._parse_pipeline_identity("chembl_activity") == ("chembl", "activity")
    assert helper._parse_pipeline_identity("broken") is None
    assert result["seed"] is fields
    assert result["chembl"] is fields
    assert result["chembl_activity"] is fields
    assert result["chembl.activity"] is fields

    class SchemaWithAnnotations:
        __annotations__ = {"title": "Series[String]", "_dq_warn": "Series[boolean]"}

    extracted = helper._extract_fields_from_annotations(
        SchemaWithAnnotations, "chembl.activity"
    )
    assert extracted["title"].dtype == "str"
    assert extracted["_dq_warn"].dtype == "bool"
    assert helper._extract_dtype_from_annotation("Series[Int64]") == "int"
    assert helper._simplify_dtype("datetime64[ns]") == "datetime"

    assert find_schema_class(_SchemaFromAll) is ExportedSchema
    found = find_schema_class(_SchemaFromVars)
    assert found is _SchemaFromVars.LocalSchema


def test_cross_validator_helper_functions_cover_details_and_numeric_comparison() -> (
    None
):
    logger = MagicMock()
    pairing = EnricherFieldPairing(
        enricher_pipeline="crossref_publication",
        fields=(
            FieldComparisonSpec(field_name="title", method=ComparisonMethod.EXACT),
            FieldComparisonSpec(
                field_name="score",
                method=ComparisonMethod.NUMERIC_TOLERANCE,
                threshold=0.1,
            ),
            FieldComparisonSpec(field_name="skip_me", method=ComparisonMethod.SKIP),
        ),
    )
    df = pl.DataFrame(
        {
            "chembl.publication.title": ["same", "left"],
            "crossref.publication.title": ["same", "right"],
            "chembl.publication.score": [100.0, 100.0],
            "crossref.publication.score": [105.0, 130.0],
        }
    )

    mismatch_total, compared_total, mismatch_counts, mismatch_bools = (
        _count_mismatches_vectorized(
            df,
            pairing,
            "chembl",
            "publication",
            "crossref",
            "publication",
            logger=logger,
        )
    )

    assert mismatch_total.to_list() == [0, 2]
    assert compared_total.to_list() == [2, 2]
    assert mismatch_counts["title"] == 1
    assert mismatch_counts["score"] == 1
    detail = _build_enricher_detail(
        "crossref_publication", mismatch_bools, mismatch_total
    )
    combined = _combine_cv_details([detail], len(df))
    assert combined.to_list()[0] is None
    assert "crossref_publication" in combined.to_list()[1]
    numeric = _compare_field(
        df,
        "chembl.publication.score",
        "crossref.publication.score",
        ComparisonMethod.NUMERIC_TOLERANCE,
        0.1,
    )
    assert numeric.to_list() == [True, False]


def test_aggregator_helpers_cover_sort_resolution_and_filter_parsing() -> None:
    logger = MagicMock()
    aggregator = EnricherAggregator(logger)
    config = AggregationConfig(
        group_by="doc_id",
        fields=(
            AggregationFieldSpec(
                source_field="ranked_term",
                agg_function=AggregationFunction.COLLECT_LIST,
            ),
            AggregationFieldSpec(
                source_field="status",
                agg_function=AggregationFunction.CONCAT_STR,
                filter_condition="status IS NOT NULL",
            ),
        ),
    )
    assert aggregator._resolve_sort_columns(config) == [
        "doc_id",
        "ranked_term",
        "status",
    ]
    assert aggregator._parse_filter_condition("status IS NOT NULL") is not None
    assert aggregator._parse_filter_condition("status IS NULL") is not None
    assert aggregator._parse_filter_condition("status == 'ok'") is not None
    assert aggregator._parse_filter_condition("status != 'bad'") is not None
    assert aggregator._parse_filter_condition("unparseable condition") is None
    logger.warning.assert_called_once()

    df = pl.DataFrame(
        {"doc_id": ["D1", "D1"], "ranked_term": ["b", "a"], "status": ["ok", None]}
    )
    result = aggregator.aggregate(df, config, "crossref_publication")
    assert result["ranked_term"].to_list()[0] == ["a", "b"]
    assert result["status"].to_list()[0] == "ok"
