"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from collections.abc import Iterable

__all__ = [
    "__all__",
    "_critical_diff_issues",
]


def _critical_diff_issues(
    rows: object,
    critical_names: Iterable[str],
    *,
    kind: str,
) -> list[str]:
    issues: list[str] = []
    if not isinstance(rows, list):
        return issues
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = row.get("name")
        delta = row.get("delta")
        if isinstance(name, str) and name in critical_names and delta:
            issues.append(
                f"{kind} `{name}` expected {row.get('snapshot')}, live managed {row.get('live_managed')}"
            )
    return issues


__all__ = [name for name in globals() if not name.startswith("__")]
