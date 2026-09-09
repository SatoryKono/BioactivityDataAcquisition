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
KNOWN_INTEGRATION_BRANCHES: Final[frozenset[str]] = frozenset({"develop"})

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

PROPOSED_ACTIONS: Final[tuple[str, ...]] = ("keep", "tag", "delete", "review")

# Dated snapshots include separator forms (`master_20260910`, `master-20260910`)
# and the live no-separator form (`master20260910`). Protected prefixes stay keep.
DATED_SNAPSHOT_NAME: Final[re.Pattern[str]] = re.compile(
    r"^(?:main|master)(?:[_-]20\d{6}|20\d{6})(?:[-_.].*)?$"
)
COMPLIANT_TYPE_NAME: Final[re.Pattern[str]] = re.compile(
    r"^(?:feat|fix|refactor|docs|test|chore|ci)/[a-z0-9]+(?:[.-][a-z0-9]+)*$"
)
AUTOMATION_NAME: Final[re.Pattern[str]] = re.compile(
    r"^(?:dependabot|renovate|devin|bolt|copilot|codex)/.+"
)
NUMERIC_ONLY_NAME: Final[re.Pattern[str]] = re.compile(r"^\d+$")
TEMP_BRANCH_NAME: Final[re.Pattern[str]] = re.compile(
    r"^(?:temp-branch|temp/.+|tmp(?:[-_].*)?)$"
)
CODEX_FIX_MAIN_NAME: Final[re.Pattern[str]] = re.compile(
    r"^codex/fix-main(?:[-_].*)?$"
)
JULES_BARE_NAME: Final[re.Pattern[str]] = re.compile(r"^jules(?:[-_].+)?$")

STALE_DRAFT_BRANCH_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"^bolt[/-]"),
    re.compile(r"^perf[/-]"),
    re.compile(r"^performance-"),
    re.compile(r"^(?:test-swarm|py-test-swarm|py-review|swarm-)"),
    re.compile(r"^add-(?:py-test-swarm|py-review|review-reports)-"),
    re.compile(r"^(?:ai-code-review|ai-hierarchical-code-review)-"),
    re.compile(r"^(?:feat|feature)/(?:py-test-swarm|py-review|review)"),
    re.compile(r"^chore/(?:test-swarm|update-review-reports|generate-hierarchical)"),
    re.compile(r"^review/(?:hierarchical-code-review|orchestrator)"),
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
    name_compliant: bool
    proposed_action: str


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


def is_dated_snapshot_name(name: str) -> bool:
    return DATED_SNAPSHOT_NAME.fullmatch(name) is not None


def is_inventory_name_compliant(name: str) -> bool:
    """Return whether a remote name matches the published naming policy.

    Dated snapshots and opaque names are non-compliant even when the PR-head
    workflow still accepts a historical ``master[0-9-]+`` pattern.
    """
    if name in PROTECTED_EXACT_BRANCHES or name in KNOWN_INTEGRATION_BRANCHES:
        return True
    if any(name.startswith(prefix) for prefix in PROTECTED_BRANCH_PREFIXES):
        return True
    if CODEX_FIX_MAIN_NAME.fullmatch(name) is not None:
        return False
    if JULES_BARE_NAME.fullmatch(name) is not None:
        return False
    if TEMP_BRANCH_NAME.fullmatch(name) is not None:
        return False
    if NUMERIC_ONLY_NAME.fullmatch(name) is not None:
        return False
    if is_dated_snapshot_name(name):
        return False
    if COMPLIANT_TYPE_NAME.fullmatch(name) is not None:
        return True
    return AUTOMATION_NAME.fullmatch(name) is not None


def propose_owner_action(
    *,
    name: str,
    protected: bool,
    open_pr_number: int | None,
    category: str,
) -> str:
    """Dry-run owner decision. Callers MUST NOT apply ``delete`` automatically."""
    if (
        protected
        or name in PROTECTED_EXACT_BRANCHES
        or name in KNOWN_INTEGRATION_BRANCHES
    ):
        return "keep"
    if open_pr_number is not None:
        return "keep"
    if category == "dated-snapshot" or is_dated_snapshot_name(name):
        return "tag"
    if category == "garbage" or NUMERIC_ONLY_NAME.fullmatch(name) is not None:
        return "delete"
    if not is_inventory_name_compliant(name):
        return "review"
    return "keep"


def propose_worktree_action(
    *,
    branch: str | None,
    detached: bool,
    locked: bool,
    prunable: bool,
) -> tuple[str, str]:
    """Classify a local worktree without pruning or unlocking it."""
    if locked:
        return "keep", "locked; confirm a live agent before unlock"
    if prunable:
        return "review", "prunable; operator may prune after confirming no live use"
    if detached:
        return "review", "detached HEAD; do not rebase into main"
    if branch is not None and is_dated_snapshot_name(branch):
        return "review", "dated master/main snapshot; do not rebase into origin/main"
    return "keep", "checked out; keep until the worktree is abandoned"


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
    if is_dated_snapshot_name(name):
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
    category = categorize_branch(name)
    return BranchRecord(
        name=name,
        sha=sha,
        committed_at=committed_at,
        category=category,
        protected=protected,
        phase1_garbage=phase1 and not protected,
        phase2_stale_draft=phase2,
        open_pr_number=open_pr_number,
        open_pr_state=open_pr_state,
        open_pr_draft=open_pr_draft,
        open_pr_created_at=open_pr_created_at,
        open_pr_labels=open_pr_labels,
        name_compliant=is_inventory_name_compliant(name),
        proposed_action=propose_owner_action(
            name=name,
            protected=protected,
            open_pr_number=open_pr_number,
            category=category,
        ),
    )
