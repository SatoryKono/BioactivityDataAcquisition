"""Shared branch cleanup policy for repository hygiene automation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final

DEFAULT_OWNER: Final[str] = "SatoryKono"
DEFAULT_REPO: Final[str] = "BioactivityDataAcquisition"
DEFAULT_CUTOFF_ISO: Final[str] = "2026-06-10T00:00:00+00:00"

PROTECTED_EXACT_BRANCHES: Final[frozenset[str]] = frozenset({"main", "master"})

PROTECTED_BRANCH_PREFIXES: Final[tuple[str, ...]] = (
    "master_202606",
    "master_202607",
    "main_202606",
    "main_202607",
)

PHASE1_GARBAGE_BRANCHES: Final[tuple[str, ...]] = (
    "1",
    "2",
    "a1",
    "tmp",
    "tmp01",
    "tmp2",
    "tmp-audit-noop-cleanup",
    "ьфыеук",
    "cleanup-backup",
)

STALE_DRAFT_BRANCH_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"^bolt(/|-)"),
    re.compile(r"^perf(/|-)"),
    re.compile(r"^performance-"),
    re.compile(r"^(test-swarm|py-test-swarm|py-review|swarm-)"),
    re.compile(r"^add-(py-test-swarm|py-review|review-reports)-"),
    re.compile(r"^(ai-code-review|ai-hierarchical-code-review)-"),
    re.compile(r"^(feat|feature)/(py-test-swarm|py-review|review)"),
    re.compile(r"^chore/(test-swarm|update-review-reports|generate-hierarchical)"),
    re.compile(r"^review/(hierarchical-code-review|orchestrator)"),
    re.compile(r"^docs-code-review-"),
    re.compile(r"^docs/arch-review-"),
)

CATEGORY_ORDER: Final[tuple[str, ...]] = (
    "protected-trunk",
    "protected-snapshot",
    "garbage",
    "agent-bolt",
    "agent-perf",
    "agent-reports",
    "agent-other",
    "dated-snapshot",
    "dependabot",
    "feature-fix",
    "other",
)


@dataclass(frozen=True)
class BranchRecord:
    """Normalized branch inventory row."""

    name: str
    sha: str
    committed_at: str
    category: str
    protected: bool
    phase1_garbage: bool
    phase2_stale_draft: bool
    open_pr_number: int | None
    open_pr_state: str | None
    open_pr_draft: bool | None
    open_pr_created_at: str | None
    open_pr_labels: tuple[str, ...]


def parse_cutoff(cutoff_iso: str) -> datetime:
    parsed = datetime.fromisoformat(cutoff_iso.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def is_protected_branch(name: str) -> bool:
    if name in PROTECTED_EXACT_BRANCHES:
        return True
    return any(name.startswith(prefix) for prefix in PROTECTED_BRANCH_PREFIXES)


def is_phase1_garbage_branch(name: str) -> bool:
    return name in PHASE1_GARBAGE_BRANCHES


def matches_stale_draft_branch_pattern(name: str) -> bool:
    return any(pattern.search(name) for pattern in STALE_DRAFT_BRANCH_PATTERNS)


def categorize_branch(name: str) -> str:
    if name in PROTECTED_EXACT_BRANCHES:
        return "protected-trunk"
    if any(name.startswith(prefix) for prefix in PROTECTED_BRANCH_PREFIXES):
        return "protected-snapshot"
    if is_phase1_garbage_branch(name):
        return "garbage"
    if name.startswith("bolt/") or name.startswith("bolt-") or name.startswith("bolt_"):
        return "agent-bolt"
    if (
        name.startswith("perf/")
        or name.startswith("perf-")
        or name.startswith("performance-")
    ):
        return "agent-perf"
    if matches_stale_draft_branch_pattern(name):
        return "agent-reports"
    if re.match(r"^(codex|claude|copilot|devin|jules|agent|ai-|fedor/)", name):
        return "agent-other"
    if re.match(r"^(main|master)[_-]20\d{6}", name) or re.match(
        r"^(main|master)-20\d{6}", name
    ):
        return "dated-snapshot"
    if name.startswith("dependabot/"):
        return "dependabot"
    if re.match(
        r"^(feat|fix|feature|chore|issue|docs|consolidate|security-fix)/", name
    ):
        return "feature-fix"
    return "other"


def is_stale_draft_pr_candidate(
    *,
    branch_name: str,
    created_at: str,
    is_draft: bool,
    labels: tuple[str, ...],
    cutoff: datetime,
) -> bool:
    if is_protected_branch(branch_name):
        return False
    if not is_draft:
        return False
    created = parse_cutoff(created_at)
    if created >= cutoff:
        return False
    if "stale" in labels:
        return True
    return matches_stale_draft_branch_pattern(branch_name)


def build_branch_record(
    *,
    name: str,
    sha: str,
    committed_at: str,
    cutoff: datetime,
    open_pr_number: int | None = None,
    open_pr_state: str | None = None,
    open_pr_draft: bool | None = None,
    open_pr_created_at: str | None = None,
    open_pr_labels: tuple[str, ...] = (),
) -> BranchRecord:
    protected = is_protected_branch(name)
    phase1 = is_phase1_garbage_branch(name)
    phase2 = False
    if (
        open_pr_number is not None
        and open_pr_created_at is not None
        and open_pr_draft is not None
    ):
        phase2 = is_stale_draft_pr_candidate(
            branch_name=name,
            created_at=open_pr_created_at,
            is_draft=open_pr_draft,
            labels=open_pr_labels,
            cutoff=cutoff,
        )
    return BranchRecord(
        name=name,
        sha=sha,
        committed_at=committed_at,
        category=categorize_branch(name),
        protected=protected,
        phase1_garbage=phase1 and not protected,
        phase2_stale_draft=phase2,
        open_pr_number=open_pr_number,
        open_pr_state=open_pr_state,
        open_pr_draft=open_pr_draft,
        open_pr_created_at=open_pr_created_at,
        open_pr_labels=open_pr_labels,
    )
