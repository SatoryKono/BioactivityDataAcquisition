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
