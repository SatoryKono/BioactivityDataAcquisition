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
"""Branch-depth unit tests for coalesce policy support helpers (T-01)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import polars as pl
import pytest

from bioetl.application.composite._coalesce_policy_support import (
    apply_field_priority,
    can_coalesce,
    coalesce_and_drop,
    compatible_columns,
    extract_field_from_qualified,
    resolve_priority_provider,
    seed_prefix,
    sort_columns,
)
from bioetl.application.composite._coalesce_timestamp_support import (
    build_latest_timestamp_row_fields,
    coalesce_by_latest_timestamp,
    count_timestamp_companions,
    drop_coalesced_columns,
    pick_latest_timestamp_value,
    resolve_row_timestamp_key,
    resolve_timestamp_companion,
    should_replace_latest_candidate,
    timestamp_sort_key,
    update_fallback_candidate,
)

pytestmark = pytest.mark.unit


def test_extract_and_seed_prefix_edge_branches() -> None:
    assert extract_field_from_qualified("a.b.c") == "c"
    assert extract_field_from_qualified("plain") == "plain"
    assert seed_prefix(None) is None
    assert seed_prefix("chembl_activity") == "chembl.activity."
    assert seed_prefix("not-a-pipeline") is None


def test_can_coalesce_and_compatible_columns_cover_type_branches() -> None:
    df = pl.DataFrame(
        {
            "a": [1],
            "b": [2],
            "n": [None],
            "la": [[1]],
            "lb": [[2]],
            "s": ["x"],
        }
    )
    assert can_coalesce(df, "a", "b") is True
    assert can_coalesce(df, "a", "n") is True
    assert can_coalesce(df, "la", "lb") is True
    assert can_coalesce(df, "la", "s") is False
    # Non-list scalar dtype mismatches currently coalesce (both non-list).
    assert can_coalesce(df, "a", "s") is True
    assert compatible_columns(df, []) == []
    assert compatible_columns(df, ["a", "b", "s"]) == ["a", "b", "s"]
    assert compatible_columns(df, ["la", "s"]) == ["la"]


def test_sort_columns_seed_and_enricher_strategies() -> None:
    cols = ["chembl.activity.title", "pubchem.compound.title", "other"]
    seed_first = sort_columns(cols, "chembl.activity.", prefer_seed=True)
    assert seed_first[0].startswith("chembl.activity.")
    enricher_first = sort_columns(cols, "chembl.activity.", prefer_seed=False)
    assert enricher_first[0] != "chembl.activity.title" or len(enricher_first) == 1


def test_coalesce_and_drop_and_drop_helpers() -> None:
    df = pl.DataFrame({"a": [None, 1], "b": [2, None]})
    assert coalesce_and_drop(df, ["a"]).columns == ["a", "b"]
    merged = coalesce_and_drop(df, ["a", "b"])
    assert "b" not in merged.columns
    assert "a" in merged.columns
    dropped = drop_coalesced_columns(df, ["a", "b"])
    assert "b" not in dropped.columns
    assert drop_coalesced_columns(df, ["a"]).columns == df.columns


def test_resolve_priority_provider_prefers_order_service() -> None:
    order_service = MagicMock(name="order_service")
    priority = MagicMock(name="priority")
    assert resolve_priority_provider(priority, order_service) is order_service
    assert resolve_priority_provider(priority, None) is priority


def test_apply_field_priority_short_circuits_and_coalesces() -> None:
    df = pl.DataFrame(
        {
            "chembl.activity.title": [None, "a"],
            "pubchem.compound.title": ["b", None],
        }
    )
    provider = SimpleNamespace(
        collect_field_columns=MagicMock(return_value=["chembl.activity.title"]),
        order_columns_by_priority=MagicMock(),
        filter_compatible_columns=MagicMock(),
    )
    out = apply_field_priority(
        df,
        provider=provider,
        field="title",
        priorities=("chembl",),
        enrichers=(),
        available_columns=set(df.columns),
        seed_pipeline="chembl_activity",
        can_coalesce_fn=can_coalesce,
    )
    assert out is df
    provider.order_columns_by_priority.assert_not_called()

    provider.collect_field_columns.return_value = list(df.columns)
    provider.order_columns_by_priority.return_value = list(df.columns)
    provider.filter_compatible_columns.return_value = (list(df.columns), [])
    coalesced = apply_field_priority(
        df,
        provider=provider,
        field="title",
        priorities=("chembl", "pubchem"),
        enrichers=(),
        available_columns=set(df.columns),
        seed_pipeline="chembl_activity",
        can_coalesce_fn=can_coalesce,
    )
    assert "pubchem.compound.title" not in coalesced.columns


def test_timestamp_helpers_cover_ranking_and_fallback_branches() -> None:
    assert resolve_timestamp_companion("x", {"x"}) is None
    assert (
        resolve_timestamp_companion(
            "chembl.activity.value",
            {"chembl.activity.value", "chembl.activity.updated_at"},
        )
        == "chembl.activity.updated_at"
    )
    assert timestamp_sort_key(datetime(2026, 1, 1, tzinfo=UTC))[0] == 3
    assert timestamp_sort_key(date(2026, 1, 1))[0] == 3
    assert timestamp_sort_key(10)[0] == 2
    assert timestamp_sort_key("2026")[0] == 1
    assert timestamp_sort_key(object())[0] == 0

    value, rank = update_fallback_candidate(
        value="a", rank=1, fallback_value=None, fallback_rank=None
    )
    assert (value, rank) == ("a", 1)
    value, rank = update_fallback_candidate(
        value="b", rank=5, fallback_value="a", fallback_rank=1
    )
    assert (value, rank) == ("a", 1)

    row = {
        "chembl.activity.value": 1,
        "chembl.activity.updated_at": datetime(2026, 1, 2, tzinfo=UTC),
        "pubchem.compound.value": 9,
        "pubchem.compound.updated_at": datetime(2026, 1, 1, tzinfo=UTC),
    }
    ts_cols = {
        "chembl.activity.value": "chembl.activity.updated_at",
        "pubchem.compound.value": "pubchem.compound.updated_at",
    }
    assert (
        resolve_row_timestamp_key(
            row=row,
            column="missing",
            timestamp_columns=ts_cols,
        )
        is None
    )
    assert should_replace_latest_candidate(
        current_timestamp_key=(3, 2.0),
        rank=0,
        best_timestamp_key=None,
        best_rank=None,
    )
    assert should_replace_latest_candidate(
        current_timestamp_key=(3, 2.0),
        rank=0,
        best_timestamp_key=(3, 2.0),
        best_rank=1,
    )
    picked = pick_latest_timestamp_value(
        row=row,
        compatible_cols=["chembl.activity.value", "pubchem.compound.value"],
        timestamp_columns=ts_cols,
        priority_rank={
            "chembl.activity.value": 0,
            "pubchem.compound.value": 1,
        },
    )
    assert picked == 1
    assert count_timestamp_companions(ts_cols) == 2
    assert build_latest_timestamp_row_fields(
        ["chembl.activity.value"],
        {"chembl.activity.value": "chembl.activity.updated_at"},
    ) == ["chembl.activity.value", "chembl.activity.updated_at"]


def test_coalesce_by_latest_timestamp_falls_back_without_enough_companions() -> None:
    df = pl.DataFrame(
        {
            "chembl.activity.value": [None, 1],
            "pubchem.compound.value": [2, None],
        }
    )
    out = coalesce_by_latest_timestamp(
        df,
        ordered_cols=["chembl.activity.value", "pubchem.compound.value"],
    )
    assert "pubchem.compound.value" not in out.columns
