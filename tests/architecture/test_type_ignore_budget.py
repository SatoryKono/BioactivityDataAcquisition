"""Architecture guard: typed ``# type: ignore[...]`` debt budget.

Tracks category budgets for the highest-risk ignore groups and prevents
regressions over time.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

SRC_ROOT = Path("src/bioetl")
IGNORE_RE = re.compile(r"type:\s*ignore(?:\[([^\]]+)\])?")

# RF-008 (2026-03-04): post-cleanup baseline for key categories.
CATEGORY_BUDGETS: dict[str, int] = {
    "arg-type": 9,
    "assignment": 2,
    "misc": 1,  # MRO-specific mixin conflict in SilverWriter
    "import-untyped": 0,
    "override": 1,
}
TOTAL_BUDGET = 36


def _collect_ignore_counts() -> Counter[str]:
    counts: Counter[str] = Counter()
    for path in sorted(SRC_ROOT.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            match = IGNORE_RE.search(line)
            if match is None:
                continue
            codes = match.group(1)
            if codes is None:
                counts["bare"] += 1
                continue
            for code in codes.split(","):
                counts[code.strip()] += 1
    return counts


def test_type_ignore_category_budgets() -> None:
    """Selected type-ignore categories must stay within agreed budgets."""
    counts = _collect_ignore_counts()
    violations = [
        f"{category}: {counts[category]} > {budget}"
        for category, budget in CATEGORY_BUDGETS.items()
        if counts[category] > budget
    ]

    assert not violations, "Type-ignore category budget exceeded:\n" + "\n".join(
        violations
    )


def test_type_ignore_total_budget() -> None:
    """Total type-ignore count must not exceed the ratcheted budget."""
    counts = _collect_ignore_counts()
    total = sum(counts.values())
    assert total <= TOTAL_BUDGET, (
        f"Total # type: ignore budget exceeded: {total} > {TOTAL_BUDGET}. "
        "Refactor typing or tighten per-file overrides before adding new ignores."
    )
