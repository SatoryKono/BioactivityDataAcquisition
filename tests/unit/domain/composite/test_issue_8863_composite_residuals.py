"""Regression tests for confirmed composite/config residuals in issue #8863."""

from __future__ import annotations

from collections.abc import Callable, Mapping

import pytest

from bioetl.domain.composite.aggregation import (
    AggregationConfig,
    AggregationFieldSpec,
    AggregationFunction,
)
from bioetl.domain.composite.aggregation_filters import (
    _validate_aggregation_filter_condition,
)
from bioetl.domain.composite.config_composite_decoder import (
    _attach_optional_section,
    _optional_column_groups,
    _parse_field_priorities,
)
from bioetl.domain.composite.config_composite_section_decoders import (
    build_cross_validation_config,
    build_execution_config,
    build_lineage_config,
)
from bioetl.domain.composite.result_merge import MergeResult
from bioetl.domain.config.table import IdempotencyContract, TableConfig

pytestmark = pytest.mark.unit


def test_field_priorities_reject_non_string_members() -> None:
    with pytest.raises(ValueError, match="must contain non-empty strings"):
        _parse_field_priorities({"title": ["chembl", 7]})


def test_optional_column_groups_preserve_empty_sequence_and_reject_false() -> None:
    assert _optional_column_groups(None) == ()
    assert _optional_column_groups(()) == ()
    with pytest.raises(ValueError, match="must be a list"):
        _optional_column_groups(False)


@pytest.mark.parametrize(
    ("builder", "field"),
    [
        (build_execution_config, "checkpoint_enabled"),
        (build_lineage_config, "track_field_sources"),
        (build_lineage_config, "track_timestamps"),
        (build_lineage_config, "track_status"),
        (build_cross_validation_config, "enabled"),
    ],
)
def test_composite_boolean_decoders_fail_closed_on_string_false(
    builder: Callable[[Mapping[str, object]], object],
    field: str,
) -> None:
    with pytest.raises(ValueError, match="must be a boolean"):
        builder({field: "false"})


def test_quoted_literal_cannot_hide_nested_operator() -> None:
    with pytest.raises(ValueError, match="additional operators"):
        _validate_aggregation_filter_condition("status == 'ok' OR 'fallback'")

    _validate_aggregation_filter_condition(r"status == 'it\'s valid'")


def test_present_malformed_optional_section_is_not_silently_dropped() -> None:
    kwargs: dict[str, object] = {}
    with pytest.raises(ValueError, match="execution must be a dictionary"):
        _attach_optional_section(
            kwargs,
            {"execution": None},
            "execution",
            build_execution_config,
        )


@pytest.mark.parametrize(
    "condition",
    ["field IS NULL trailing", "field IS NOT NULL OR other IS NULL"],
)
def test_null_filter_rejects_trailing_text(condition: str) -> None:
    with pytest.raises(ValueError, match="must not contain trailing text"):
        _validate_aggregation_filter_condition(condition)


def test_output_field_is_trimmed_and_whitespace_only_is_rejected() -> None:
    spec = AggregationFieldSpec(
        source_field="source",
        agg_function=AggregationFunction.FIRST,
        output_field="  normalized  ",
    )

    assert spec.output_field == "normalized"
    assert spec.effective_output_field == "normalized"
    with pytest.raises(ValueError, match="output_field cannot be empty"):
        AggregationFieldSpec(
            source_field="source",
            agg_function=AggregationFunction.FIRST,
            output_field="   ",
        )


def test_aggregation_config_rejects_duplicate_effective_output_fields() -> None:
    with pytest.raises(ValueError, match="duplicate output field: title"):
        AggregationConfig(
            group_by="entity_id",
            fields=(
                AggregationFieldSpec(
                    source_field="title",
                    agg_function=AggregationFunction.FIRST,
                ),
                AggregationFieldSpec(
                    source_field="alternate_title",
                    agg_function=AggregationFunction.FIRST,
                    output_field="title",
                ),
            ),
        )


def test_cross_validation_decoder_uses_strict_numeric_parsers() -> None:
    with pytest.raises(ValueError, match="warning_threshold must be an integer"):
        build_cross_validation_config({"warning_threshold": 1.5})
    with pytest.raises(ValueError, match="fuzzy_threshold must be a number"):
        build_cross_validation_config({"fuzzy_threshold": object()})

    restored = build_cross_validation_config(
        {"enabled": None, "warning_threshold": None, "fuzzy_threshold": "0.75"}
    )
    assert restored.enabled is True
    assert restored.warning_threshold == 1
    assert restored.fuzzy_threshold == pytest.approx(0.75)


def test_merge_result_rejects_enrichment_when_no_records_were_merged() -> None:
    with pytest.raises(ValueError, match="records_enriched cannot exceed"):
        MergeResult(records_merged=0, records_enriched=1)


@pytest.mark.parametrize(
    "contract_field",
    ["silver_idempotency_contract", "gold_idempotency_contract"],
)
def test_partition_append_contract_requires_partition_columns(
    contract_field: str,
) -> None:
    with pytest.raises(ValueError, match="partition_cols must be non-empty"):
        TableConfig(
            **{
                contract_field: (
                    IdempotencyContract.PARTITION_APPEND_WITH_STABLE_PARTITION_KEY
                )
            }
        )

    config = TableConfig(
        partition_cols=("publication_year",),
        **{
            contract_field: (
                IdempotencyContract.PARTITION_APPEND_WITH_STABLE_PARTITION_KEY
            )
        },
    )
    assert config.partition_cols == ("publication_year",)
