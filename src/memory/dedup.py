"""Stable semantic deduplication for memory record candidates."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum

_WHITESPACE_PATTERN = re.compile(r"\s+")


class DuplicateKind(StrEnum):
    """Whether duplicate candidates agree on their content."""

    EXACT = "exact"
    CONFLICTING = "conflicting"


@dataclass(frozen=True, slots=True)
class DedupCandidate:
    """Minimal record projection required for semantic deduplication."""

    record_id: str
    record_type: str
    title: str
    content_digest: str
    source_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DuplicateConflict:
    """One deterministic duplicate group."""

    semantic_key: str
    kind: DuplicateKind
    record_ids: tuple[str, ...]
    content_digests: tuple[str, ...]
    source_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DedupReport:
    """Deterministically ordered duplicate analysis."""

    candidate_count: int
    unique_key_count: int
    conflicts: tuple[DuplicateConflict, ...]

    @property
    def conflict_count(self) -> int:
        return len(self.conflicts)


def normalize_semantic_text(value: str) -> str:
    """Normalize human text without applying language-specific stemming."""
    normalized = unicodedata.normalize("NFKC", value).casefold().strip()
    return _WHITESPACE_PATTERN.sub(" ", normalized)


def semantic_key(*, record_type: str, title: str) -> str:
    """Build a stable opaque key for one semantic subject."""
    identity = {
        "record_type": normalize_semantic_text(record_type),
        "title": normalize_semantic_text(title),
    }
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def build_dedup_report(candidates: tuple[DedupCandidate, ...]) -> DedupReport:
    """Group candidates and report exact or conflicting duplicates."""
    groups: dict[str, list[DedupCandidate]] = {}
    for candidate in candidates:
        key = semantic_key(
            record_type=candidate.record_type,
            title=candidate.title,
        )
        groups.setdefault(key, []).append(candidate)

    conflicts: list[DuplicateConflict] = []
    for key, group in groups.items():
        if len(group) < 2:
            continue
        digests = tuple(sorted({candidate.content_digest for candidate in group}))
        conflicts.append(
            DuplicateConflict(
                semantic_key=key,
                kind=(
                    DuplicateKind.EXACT
                    if len(digests) == 1
                    else DuplicateKind.CONFLICTING
                ),
                record_ids=tuple(sorted(candidate.record_id for candidate in group)),
                content_digests=digests,
                source_refs=tuple(
                    sorted(
                        {
                            source_ref
                            for candidate in group
                            for source_ref in candidate.source_refs
                        }
                    )
                ),
            )
        )
    return DedupReport(
        candidate_count=len(candidates),
        unique_key_count=len(groups),
        conflicts=tuple(sorted(conflicts, key=lambda conflict: conflict.semantic_key)),
    )
