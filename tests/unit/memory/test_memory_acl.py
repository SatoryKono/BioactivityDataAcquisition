"""Fail-closed access-control tests for repository-owned memory."""

from __future__ import annotations

import pytest

from memory.access import (
    AccessAction,
    AccessContext,
    AccessDeniedError,
    require_access,
)

pytestmark = pytest.mark.unit


def test_access_requires_matching_principal_repository_and_explicit_grant() -> None:
    context = AccessContext(
        principal_id="user-a",
        repo_id="repo-a",
        grants=frozenset({AccessAction.EXPORT}),
    )

    assert (
        require_access(
            context,
            action=AccessAction.EXPORT,
            owner_id="user-a",
            repo_id="repo-a",
        )
        is None
    )


@pytest.mark.parametrize(
    ("context", "action", "message"),
    [
        (
            AccessContext(
                principal_id="user-b",
                repo_id="repo-a",
                grants=frozenset({AccessAction.EXPORT}),
            ),
            AccessAction.EXPORT,
            "principal scope mismatch",
        ),
        (
            AccessContext(
                principal_id="user-a",
                repo_id="repo-b",
                grants=frozenset({AccessAction.EXPORT}),
            ),
            AccessAction.EXPORT,
            "repository scope mismatch",
        ),
        (
            AccessContext(principal_id="user-a", repo_id="repo-a"),
            AccessAction.DELETE,
            "delete not granted",
        ),
    ],
)
def test_access_matrix_denies_unspecified_or_cross_scope_operations(
    context: AccessContext,
    action: AccessAction,
    message: str,
) -> None:
    with pytest.raises(AccessDeniedError, match=message):
        require_access(
            context,
            action=action,
            owner_id="user-a",
            repo_id="repo-a",
        )
