"""Unit tests for merger_collaborators — MergeCollaboratorGroup dataclass."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.application.composite.merger_collaborators import (
    MergeCollaboratorGroup,
)


def _mock_collaborator_group() -> MergeCollaboratorGroup:
    """Build a MergeCollaboratorGroup with all-mock fields."""
    return MergeCollaboratorGroup(
        deduplicator=MagicMock(),
        aggregator=MagicMock(),
        renamer=MagicMock(),
        order_service=MagicMock(),
        coalesce_policy=MagicMock(),
        conflict_resolver=MagicMock(),
        join_planner=MagicMock(),
    )


@pytest.mark.unit
class TestMergeCollaboratorGroup:
    """Test MergeCollaboratorGroup dataclass."""

    def test_all_fields_accessible(self) -> None:
        group = _mock_collaborator_group()
        assert group.deduplicator is not None
        assert group.aggregator is not None
        assert group.renamer is not None
        assert group.order_service is not None
        assert group.coalesce_policy is not None
        assert group.conflict_resolver is not None
        assert group.join_planner is not None

    def test_frozen(self) -> None:
        group = _mock_collaborator_group()
        with pytest.raises(AttributeError):
            group.renamer = MagicMock()  # type: ignore[misc]
