"""Required dependency joins cannot proceed without mapping or join-key proof."""

from __future__ import annotations

from unittest.mock import Mock

import polars as pl
import pytest

from bioetl.application.composite.dependency_joiner import DependencyJoinerService
from bioetl.application.composite.helpers import dependency_join_apply_ops
from bioetl.application.composite.join_execution import RequiredJoinKeyError
from bioetl.domain.composite import DependencyConfig

pytestmark = pytest.mark.unit


def _collaborators():
    return {
        "deduplicator": Mock(),
        "join_key_resolver": Mock(),
        "renamer": Mock(),
        "logger": Mock(),
        "field_alias_resolver": Mock(),
        "conflict_resolver": Mock(),
        "join_executor": Mock(),
    }


@pytest.mark.parametrize("service_boundary", [True, False])
def test_target_classification_dependency_requires_explicit_mapping(service_boundary):
    dep = DependencyConfig(
        pipeline="chembl_target_protein_classification", join_keys=("target_id",)
    )
    frame = pl.DataFrame({"target_id": ["CHEMBL1"]})
    ports = _collaborators()
    arguments = {
        "merged_df": frame,
        "dependency_dfs": {dep.pipeline: frame},
        "dep": dep,
        "seed_pipeline": None,
    }
    with pytest.raises(RuntimeError, match="explicit mapping"):
        if service_boundary:
            service = DependencyJoinerService(
                **ports, system_columns_to_drop=frozenset()
            )
            service._apply_loaded_dependency_join(**arguments)
        else:
            dependency_join_apply_ops.apply_loaded_dependency_join(
                **ports, drop_system_columns=lambda data: data, **arguments
            )
    ports["join_executor"].execute_composite_key_join.assert_not_called()


def test_required_composite_dependency_does_not_execute_without_resolved_keys(
    monkeypatch,
):
    dep = DependencyConfig(
        pipeline="provider_entity", join_keys=("first", "second"), required=True
    )
    frame = pl.DataFrame({"first": [1]})
    ports = _collaborators()
    monkeypatch.setattr(
        dependency_join_apply_ops,
        "prepare_dependency_join_context",
        lambda **kwargs: object(),
    )
    monkeypatch.setattr(
        dependency_join_apply_ops,
        "resolve_composite_join_context_for_service",
        lambda **kwargs: None,
    )
    with pytest.raises(
        RequiredJoinKeyError, match="missing composite join key columns"
    ):
        dependency_join_apply_ops.apply_composite_key_dependency_join(
            **ports,
            drop_system_columns=lambda data: data,
            merged_df=frame,
            dep_df=frame,
            dep=dep,
            seed_pipeline=None,
        )
    ports["join_executor"].execute_composite_key_join.assert_not_called()
