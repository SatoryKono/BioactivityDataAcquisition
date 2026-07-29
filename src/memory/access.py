"""Fail-closed authorization primitives for repository-owned memory."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AccessAction(StrEnum):
    """Explicit operations supported by repository-owned user memory."""

    ENUMERATE = "enumerate"
    EXPORT = "export"
    CORRECT = "correct"
    TOMBSTONE = "tombstone"
    DELETE = "delete"


class AccessDeniedError(PermissionError):
    """Raised when a caller is outside the record scope or lacks a grant."""


@dataclass(frozen=True, slots=True)
class AccessContext:
    """Authenticated caller scope and explicitly granted operations."""

    principal_id: str
    repo_id: str
    grants: frozenset[AccessAction] = frozenset()


def require_access(
    context: AccessContext,
    *,
    action: AccessAction,
    owner_id: str,
    repo_id: str,
) -> None:
    """Authorize one operation, denying every unspecified case."""
    if not context.principal_id or context.principal_id != owner_id:
        raise AccessDeniedError("memory access denied: principal scope mismatch")
    if not context.repo_id or context.repo_id != repo_id:
        raise AccessDeniedError("memory access denied: repository scope mismatch")
    if action not in context.grants:
        raise AccessDeniedError(f"memory access denied: {action.value} not granted")
