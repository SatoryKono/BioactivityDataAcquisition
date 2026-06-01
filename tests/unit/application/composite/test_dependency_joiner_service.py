"""Focused tests for DependencyJoinerService routing decisions."""

from __future__ import annotations

from unittest.mock import MagicMock

import polars as pl
import pytest

from bioetl.application.composite.dependency_joiner import DependencyJoinerService


def _no_field_aliases(_pipeline: str) -> None:
    return None


def _make_service() -> DependencyJoinerService:
    return DependencyJoinerService(
        logger=MagicMock(),
        deduplicator=MagicMock(),
        renamer=MagicMock(),
        conflict_resolver=MagicMock(),
        field_alias_resolver=_no_field_aliases,
        join_key_resolver=MagicMock(),
        join_executor=MagicMock(),
        system_columns_to_drop=frozenset(),
    )


def _make_dependency(
    pipeline: str,
    *,
    is_multi_field_filter: bool,
) -> MagicMock:
    dependency = MagicMock()
    dependency.pipeline = pipeline
    dependency.is_multi_field_filter = is_multi_field_filter
    return dependency


@pytest.mark.unit
def test_apply_dependency_joins_skips_missing_dependency_frames() -> None:
    service = _make_service()
    merged_df = pl.DataFrame({"id": [1]})
    dependency = _make_dependency("pubmed_publication", is_multi_field_filter=False)

    result = service.apply_dependency_joins(
        merged_df=merged_df,
        dependency_dfs={},
        dependencies=(dependency,),
        seed_pipeline="chembl_publication",
    )

    assert result.equals(merged_df)


@pytest.mark.unit
def test_apply_dependency_joins_routes_multi_field_dependencies_to_composite_join() -> (
    None
):
    service = _make_service()
    merged_df = pl.DataFrame({"id": [1]})
    dep_df = pl.DataFrame({"id": [1]})
    dependency = _make_dependency("pubmed_publication", is_multi_field_filter=True)
    expected = pl.DataFrame({"joined": [1]})
    service.apply_composite_key_dependency_join = MagicMock(return_value=expected)
    service._apply_single_key_dependency_join = MagicMock(return_value=merged_df)

    result = service.apply_dependency_joins(
        merged_df=merged_df,
        dependency_dfs={dependency.pipeline: dep_df},
        dependencies=(dependency,),
        seed_pipeline="chembl_publication",
    )

    assert result.equals(expected)
    service.apply_composite_key_dependency_join.assert_called_once()
    service._apply_single_key_dependency_join.assert_not_called()


@pytest.mark.unit
def test_apply_dependency_joins_routes_single_key_dependencies_to_single_key_join() -> (
    None
):
    service = _make_service()
    merged_df = pl.DataFrame({"id": [1]})
    dep_df = pl.DataFrame({"id": [1]})
    dependency = _make_dependency("pubmed_publication", is_multi_field_filter=False)
    expected = pl.DataFrame({"joined": [1]})
    service.apply_composite_key_dependency_join = MagicMock(return_value=merged_df)
    service._apply_single_key_dependency_join = MagicMock(return_value=expected)

    result = service.apply_dependency_joins(
        merged_df=merged_df,
        dependency_dfs={dependency.pipeline: dep_df},
        dependencies=(dependency,),
        seed_pipeline="chembl_publication",
    )

    assert result.equals(expected)
    service._apply_single_key_dependency_join.assert_called_once()
    service.apply_composite_key_dependency_join.assert_not_called()


@pytest.mark.unit
def test_apply_dependency_joins_summarizes_target_classification_dependency() -> None:
    service = _make_service()
    merged_df = pl.DataFrame({"target_id": ["CHEMBL1"]})
    dep_df = pl.DataFrame(
        {
            "target_id": ["CHEMBL1", "CHEMBL1"],
            "hierarchy_index": [0, 1],
            "leaf_id": [100, 200],
            "l1_id": [1, 2],
            "l1_name": ["Enzyme", "Transporter"],
            "classification_status": ["resolved", "resolved"],
        }
    )
    dependency = _make_dependency(
        "chembl_target_protein_classification",
        is_multi_field_filter=False,
    )
    expected = pl.DataFrame({"joined": [1]})
    service._apply_single_key_dependency_join = MagicMock(return_value=expected)

    result = service.apply_dependency_joins(
        merged_df=merged_df,
        dependency_dfs={dependency.pipeline: dep_df},
        dependencies=(dependency,),
        seed_pipeline="chembl_target",
    )

    assert result.equals(expected)
    called_df = service._apply_single_key_dependency_join.call_args.kwargs["dep_df"]
    assert called_df.height == 1
    row = called_df.to_dicts()[0]
    assert row["target_protein_class_name_L1"] == "Multifunctional target"
    assert row["target_protein_class_id_L1"] is None
