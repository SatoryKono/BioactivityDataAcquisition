"""Workflow-scoped immutable input binding for child target pipelines."""

from __future__ import annotations

import copy
from contextvars import ContextVar, Token

TARGET_CLASSIFICATION_DEPENDENCY_KEY = "target_classification_dependency"
_dependency: ContextVar[dict[str, object] | None] = ContextVar(
    "target_classification_dependency", default=None
)


def bind_target_classification_dependency(
    value: dict[str, object] | None,
) -> Token[dict[str, object] | None]:
    return _dependency.set(copy.deepcopy(value))


def reset_target_classification_dependency(
    token: Token[dict[str, object] | None],
) -> None:
    _dependency.reset(token)


def get_target_classification_dependency() -> dict[str, object] | None:
    return copy.deepcopy(_dependency.get())


__all__ = [
    "TARGET_CLASSIFICATION_DEPENDENCY_KEY",
    "bind_target_classification_dependency",
    "get_target_classification_dependency",
    "reset_target_classification_dependency",
]
