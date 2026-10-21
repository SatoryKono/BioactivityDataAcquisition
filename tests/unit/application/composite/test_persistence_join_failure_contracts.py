"""Composite persistence and join edges reject unbound input identities."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import polars as pl
import pytest

from bioetl.application.composite.checkpoint._state_support import (
    synchronize_manifest_successors,
)
from bioetl.application.composite.checkpoint.persistence_service import (
    CompositeCheckpointPersistenceParams,
    CompositeCheckpointPersistenceService,
)
from bioetl.application.composite.checkpoint.state import CompositeCheckpointState
from bioetl.application.composite.conflict_resolver import ConflictResolverService
from bioetl.application.composite.join_execution import JoinExecutorService
from bioetl.application.composite.runner_pkg.runner_completion_helpers import (
    build_legacy_completed_execution_context,
)
from bioetl.domain.exceptions import CheckpointConflictError

pytestmark = pytest.mark.unit


def test_successor_from_another_run_cannot_rebind_checkpoint():
    state = CompositeCheckpointState("pipeline", "run", manifest_id="before")
    assert (
        synchronize_manifest_successors(
            state, {"before": SimpleNamespace(run_id="other")}
        )
        is state
    )


@pytest.mark.parametrize("component", ["composite_name", "run_id", "manifest_id"])
def test_unsafe_checkpoint_history_identity_never_writes_outside_storage(component):
    from dataclasses import replace

    storage = Mock()
    service = CompositeCheckpointPersistenceService(
        CompositeCheckpointPersistenceParams(
            "pipeline", "checkpoint.json", "*.json", storage, Mock()
        )
    )
    state = replace(
        CompositeCheckpointState("pipeline", "run", manifest_id="manifest"),
        **{component: "../escape"},
    )
    with pytest.raises(CheckpointConflictError, match="history identity") as caught:
        service.save(state)
    assert isinstance(caught.value.__cause__, ValueError)
    storage.write_atomic.assert_not_called()


def test_optional_composite_join_with_missing_key_preserves_seed_frame():
    seed = pl.DataFrame({"id": [1]})
    right = pl.DataFrame({"other": [2]})
    executor = JoinExecutorService(logger=Mock(), join_type_resolver=lambda: "left")
    result = executor.execute_composite_key_join(
        seed,
        right,
        ["id", "missing"],
        ["other", "missing"],
        "provider_entity",
        required=False,
    )
    assert result.equals(seed)


def test_legacy_completion_without_seed_proof_cannot_resume_finalization():
    state = CompositeCheckpointState(
        "pipeline", "run", merge_completed=True, merge_result={"records_merged": 1}
    )
    with pytest.raises(CheckpointConflictError, match="completed seed result"):
        build_legacy_completed_execution_context(state)


@pytest.mark.parametrize("empty_group", [True, False])
def test_unusable_coalesce_metadata_preserves_qualified_source_columns(
    monkeypatch, empty_group
):
    from bioetl.application.composite import _coalesce_policy_support

    frame = pl.DataFrame({"provider.entity.title": ["source title"]})
    if empty_group:
        monkeypatch.setattr(
            _coalesce_policy_support, "build_field_groups", lambda df: {"title": []}
        )
    else:
        monkeypatch.setattr(
            _coalesce_policy_support, "compatible_columns", lambda df, columns: []
        )
    resolver = ConflictResolverService(Mock(), Mock(), Mock())
    assert resolver._materialize_canonical_fields(frame, None).equals(frame)
