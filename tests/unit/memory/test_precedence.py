"""Tests for deterministic memory precedence."""

from __future__ import annotations

import pytest

from memory.precedence import (
    ConflictDomain,
    PrecedenceCandidate,
    SourceClass,
    UnresolvableConflictError,
    resolve_precedence,
)


def _candidate(
    candidate_id: str,
    source_class: SourceClass,
    value: object,
) -> PrecedenceCandidate:
    return PrecedenceCandidate(candidate_id, source_class, value)


def test_runtime_behavior_prefers_active_runtime_over_normative_docs() -> None:
    result = resolve_precedence(
        ConflictDomain.RUNTIME_BEHAVIOR,
        (
            _candidate("rules", SourceClass.PROJECT_RULES, "docs"),
            _candidate("codex", SourceClass.ACTIVE_RUNTIME, "runtime"),
        ),
    )

    assert result.winner.candidate_id == "codex"
    assert result.rejected[0].candidate_id == "rules"


def test_implementation_fact_prefers_active_repository() -> None:
    result = resolve_precedence(
        ConflictDomain.IMPLEMENTATION_FACT,
        (
            _candidate("memory", SourceClass.MACHINE_MEMORY, "old"),
            _candidate("code", SourceClass.ACTIVE_REPOSITORY, "current"),
        ),
    )

    assert result.winner.candidate_id == "code"


def test_same_rank_conflicting_values_are_not_silently_resolved() -> None:
    with pytest.raises(UnresolvableConflictError, match="share precedence rank"):
        resolve_precedence(
            ConflictDomain.RUNTIME_BEHAVIOR,
            (
                _candidate("a", SourceClass.ACTIVE_RUNTIME, "first"),
                _candidate("b", SourceClass.ACTIVE_RUNTIME, "second"),
            ),
        )


def test_same_rank_equal_values_use_stable_candidate_id() -> None:
    result = resolve_precedence(
        ConflictDomain.RUNTIME_BEHAVIOR,
        (
            _candidate("z", SourceClass.ACTIVE_RUNTIME, "same"),
            _candidate("a", SourceClass.ACTIVE_RUNTIME, "same"),
        ),
    )

    assert result.winner.candidate_id == "a"


def test_invalid_source_class_for_domain_is_rejected() -> None:
    with pytest.raises(UnresolvableConflictError, match="is not valid"):
        resolve_precedence(
            ConflictDomain.RUNTIME_BEHAVIOR,
            (_candidate("repo", SourceClass.ACTIVE_REPOSITORY, "fact"),),
        )
