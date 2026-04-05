"""Pure rendering helpers for quarantine CLI commands."""

from __future__ import annotations

from bioetl.domain.types import JsonDict

__all__ = [
    "build_purge_preview_lines",
    "build_quarantine_grouped_lines",
    "build_quarantine_stats_lines",
    "build_replay_preview_lines",
]


_GROUP_BY_TITLES = {
    "reason-code": "Reason Code",
    "field": "Field",
    "rule-type": "Rule Type",
    "operator": "Operator",
    "reason-code-field": "Reason Code + Field",
    "reason-signature": "Stable Signature",
}

_GROUP_BY_KEYS = {
    "reason-code": "by_reason_code",
    "field": "by_field",
    "rule-type": "by_rule_type",
    "operator": "by_operator",
    "reason-code-field": "by_reason_code_field",
    "reason-signature": "by_reason_signature",
}


def _append_group_lines(
    lines: list[str],
    *,
    values: dict[str, int],
    total: int,
    title: str,
    top: int,
) -> None:
    """Append one ranked grouping block to the output lines."""
    if not values:
        return
    lines.append(f"\n  {title}:")
    for label, count in sorted(
        values.items(),
        key=lambda item: (-item[1], item[0]),
    )[:top]:
        pct = (count / total * 100) if total > 0 else 0
        lines.append(f"    - {label}: {count} ({pct:.1f}%)")


def build_quarantine_stats_lines(stats: JsonDict, *, pipeline: str) -> list[str]:
    """Build human-readable quarantine statistics lines."""
    return build_quarantine_grouped_lines(stats, pipeline=pipeline, top=10)


def build_quarantine_grouped_lines(
    stats: JsonDict,
    *,
    pipeline: str,
    top: int,
    group_by: str | None = None,
) -> list[str]:
    """Build quarantine statistics with optional focused Silver reject grouping."""
    lines = [
        "",
        f"{'=' * 50}",
        f"  Quarantine Dashboard: {pipeline}",
        f"{'=' * 50}",
    ]

    total = stats.get("total_count", stats.get("total_records", 0))
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

    silver_filter_stats = stats.get("silver_filter_rejects", {})
    if isinstance(silver_filter_stats, dict):
        silver_total = silver_filter_stats.get("total_count", 0)
        if isinstance(silver_total, int) and silver_total > 0:
            pct = (silver_total / total * 100) if total > 0 else 0
            lines.append(
                f"\n  Silver Filter Rejects: {silver_total} ({pct:.1f}% of quarantine)"
            )
            if group_by is None:
                for title, key in (
                    ("By Reason Code", "by_reason_code"),
                    ("By Field", "by_field"),
                    ("By Rule Type", "by_rule_type"),
                    ("By Operator", "by_operator"),
                    ("By Reason Code + Field", "by_reason_code_field"),
                ):
                    values = silver_filter_stats.get(key, {})
                    if not isinstance(values, dict):
                        continue
                    _append_group_lines(
                        lines,
                        values=values,
                        total=silver_total,
                        title=title,
                        top=top,
                    )
            else:
                values = silver_filter_stats.get(_GROUP_BY_KEYS[group_by], {})
                if isinstance(values, dict) and values:
                    lines.append(
                        "\n  Focused Silver Reject Grouping:"
                    )
                    _append_group_lines(
                        lines,
                        values=values,
                        total=silver_total,
                        title=_GROUP_BY_TITLES[group_by],
                        top=top,
                    )
                else:
                    lines.append(
                        "\n  Focused Silver Reject Grouping: no structured values available."
                    )

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
