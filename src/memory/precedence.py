"""Deterministic precedence rules for memory-backed agent decisions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum


class ConflictDomain(StrEnum):
    """Fact domain selecting the applicable precedence order."""

    RUNTIME_BEHAVIOR = "runtime_behavior"
    IMPLEMENTATION_FACT = "implementation_fact"


class SourceClass(StrEnum):
    """Classes of repository and runtime evidence."""

    PLATFORM_INSTRUCTION = "platform_instruction"
    ACTIVE_RUNTIME = "active_runtime"
    ACTIVE_REPOSITORY = "active_repository"
    NORMATIVE_INDEX = "normative_index"
    PROJECT_RULES = "project_rules"
    REQUIREMENTS = "requirements"
    ACCEPTED_ADR = "accepted_adr"
    MEMORY_GUIDANCE = "memory_guidance"
    MACHINE_MEMORY = "machine_memory"


class UnresolvableConflictError(ValueError):
    """Raised when precedence cannot select one candidate safely."""


@dataclass(frozen=True, slots=True)
class PrecedenceCandidate:
    """One claim participating in deterministic conflict resolution."""

    candidate_id: str
    source_class: SourceClass
    value: object


@dataclass(frozen=True, slots=True)
class PrecedenceResolution:
    """Auditable result of resolving a set of competing claims."""

    domain: ConflictDomain
    winner: PrecedenceCandidate
    rejected: tuple[PrecedenceCandidate, ...]
    winning_rank: int


_RUNTIME_ORDER = (
    SourceClass.PLATFORM_INSTRUCTION,
    SourceClass.ACTIVE_RUNTIME,
    SourceClass.NORMATIVE_INDEX,
    SourceClass.PROJECT_RULES,
    SourceClass.REQUIREMENTS,
    SourceClass.ACCEPTED_ADR,
    SourceClass.MEMORY_GUIDANCE,
    SourceClass.MACHINE_MEMORY,
)

_IMPLEMENTATION_ORDER = (
    SourceClass.ACTIVE_REPOSITORY,
    SourceClass.NORMATIVE_INDEX,
    SourceClass.PROJECT_RULES,
    SourceClass.REQUIREMENTS,
    SourceClass.ACCEPTED_ADR,
    SourceClass.ACTIVE_RUNTIME,
    SourceClass.MEMORY_GUIDANCE,
    SourceClass.MACHINE_MEMORY,
)

_ORDERS = {
    ConflictDomain.RUNTIME_BEHAVIOR: _RUNTIME_ORDER,
    ConflictDomain.IMPLEMENTATION_FACT: _IMPLEMENTATION_ORDER,
}


def _rank(domain: ConflictDomain, source_class: SourceClass) -> int:
    try:
        return _ORDERS[domain].index(source_class)
    except ValueError as exc:
        raise UnresolvableConflictError(
            f"{source_class.value} is not valid for {domain.value}"
        ) from exc


def _value_identity(value: object) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError):
        return repr(value)


def resolve_precedence(
    domain: ConflictDomain,
    candidates: tuple[PrecedenceCandidate, ...],
) -> PrecedenceResolution:
    """Resolve candidates or reject ambiguous claims at the same rank."""
    if not candidates:
        raise UnresolvableConflictError("at least one candidate is required")
    ranked = sorted(
        candidates, key=lambda candidate: _rank(domain, candidate.source_class)
    )
    winning_rank = _rank(domain, ranked[0].source_class)
    top_ranked = tuple(
        candidate
        for candidate in ranked
        if _rank(domain, candidate.source_class) == winning_rank
    )
    top_values = {_value_identity(candidate.value) for candidate in top_ranked}
    if len(top_values) > 1:
        ids = ", ".join(candidate.candidate_id for candidate in top_ranked)
        raise UnresolvableConflictError(
            f"conflicting candidates share precedence rank {winning_rank}: {ids}"
        )
    winner = min(top_ranked, key=lambda candidate: candidate.candidate_id)
    rejected = tuple(candidate for candidate in ranked if candidate != winner)
    return PrecedenceResolution(domain, winner, rejected, winning_rank)
