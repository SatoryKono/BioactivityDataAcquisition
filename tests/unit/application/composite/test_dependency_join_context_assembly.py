"""Dependency joins preserve upstream ownership and asymmetric key mappings."""

from __future__ import annotations

import pytest

from bioetl.application.composite.dependency_join_context_assembly import (
    build_composite_join_metadata,
    build_single_key_join_metadata,
)
from bioetl.domain.composite import DependencyConfig

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("key_source", "seed", "expected_left"),
    [
        (None, "chembl_activity", "chembl_activity"),
        ("seed", "chembl_activity", "chembl_activity"),
        ("chembl_target", "chembl_activity", "chembl_target"),
        (None, None, None),
    ],
)
def test_composite_join_keeps_key_order_and_upstream_owner(
    key_source: str | None, seed: str | None, expected_left: str | None
) -> None:
    dependency = DependencyConfig(
        pipeline="chembl_target_component",
        join_keys=("target_id", "component_id"),
        key_source=key_source,
    )

    context = build_composite_join_metadata(dep=dependency, seed_pipeline=seed)

    assert context.join_keys_list == ["target_id", "component_id"]
    assert context.left_pipeline == expected_left


@pytest.mark.parametrize("filter_field", [None, "parent_target_id"])
def test_single_key_join_maps_only_right_side_filter_field(
    filter_field: str | None,
) -> None:
    dependency = DependencyConfig(
        pipeline="chembl_target",
        join_keys=("target_id",),
        filter_field=filter_field,
    )

    context = build_single_key_join_metadata(
        dep=dependency, seed_pipeline="chembl_activity"
    )

    assert context.join_keys_list == ["target_id"]
    assert context.primary_key == "target_id"
    assert context.right_key == (filter_field or "target_id")
    assert context.right_keys_list == [filter_field or "target_id"]
    assert context.left_pipeline == "chembl_activity"
