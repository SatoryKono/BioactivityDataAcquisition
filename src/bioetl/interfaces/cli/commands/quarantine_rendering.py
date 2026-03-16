"""Pure rendering helpers for quarantine CLI commands."""

from __future__ import annotations

from bioetl.domain.types import JsonDict

__all__ = [
    "build_purge_preview_lines",
    "build_quarantine_stats_lines",
    "build_replay_preview_lines",
]


def build_quarantine_stats_lines(stats: JsonDict, *, pipeline: str) -> list[str]:
    """Build human-readable quarantine statistics lines."""
    lines = [
        "",
        f"{'=' * 50}",
        f"  Quarantine Dashboard: {pipeline}",
        f"{'=' * 50}",
    ]

    total = stats.get("total_count", 0)
    lines.append(f"\n  Total Records: {total}")

    by_error = stats.get("by_error_code", {})
    if isinstance(by_error, dict) and by_error:
        lines.append("\n  By Error Code:")
        for code, count in sorted(by_error.items(), key=lambda item: -item[1]):
            pct = (count / total * 100) if total > 0 else 0
            lines.append(f"    - {code}: {count} ({pct:.1f}%)")

    by_status = stats.get("by_status", {})
    if isinstance(by_status, dict) and by_status:
        lines.append("\n  By Status:")
        for status, count in sorted(by_status.items()):
            pct = (count / total * 100) if total > 0 else 0
            lines.append(f"    - {status}: {count} ({pct:.1f}%)")

    lines.append(f"\n{'=' * 50}\n")
    return lines


def build_replay_preview_lines(records: list[JsonDict]) -> list[str]:
    """Build dry-run preview lines for quarantine replay."""
    lines = [f"\nWould replay {len(records)} record(s):\n"]
    for index, record in enumerate(records[:10], 1):
        payload_hash = record.get("payload_hash")
        hash_display = payload_hash[:16] if isinstance(payload_hash, str) else "—"
        lines.append(
            f"  {index}. Error: {record.get('error_code')} | Hash: {hash_display}..."
        )
    if len(records) > 10:
        lines.append(f"  ... and {len(records) - 10} more")
    return lines


def build_purge_preview_lines(
    *, older_than_days: int, total_count: object
) -> list[str]:
    """Build dry-run preview lines for quarantine purge."""
    return [
        f"\nWould purge records older than {older_than_days} days.",
        f"Current total in quarantine: {total_count}",
        "\nUse without --dry-run to actually purge.",
    ]
