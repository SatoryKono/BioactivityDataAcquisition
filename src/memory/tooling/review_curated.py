"""Review active curated memory notes for freshness and quality drift."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from memory.notes import normalize_text_key, parse_markdown_note
from memory.resources import discover_memory_root, load_yaml_resource


@dataclass(frozen=True, slots=True)
class CuratedReviewRecord:
    """One review record for an active curated note."""

    path: str
    note_id: str
    title: str
    kind: str
    last_verified: str
    days_since_verified: int | None
    review_status: str
    recommendation: str
    source_ref_count: int
    promoted_from: str | None
    review_reasons: list[str]


def _curated_root() -> Path:
    return discover_memory_root() / "curated"


def _review_every_days() -> int:
    memory_root = discover_memory_root()
    retention = load_yaml_resource(memory_root / "policy" / "retention.yaml")
    return int(retention["artifact_classes"]["curated_note"]["review_every_days"])


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _iter_active_curated_notes(root: Path) -> list[Path]:
    notes: list[Path] = []
    if not root.exists():
        return notes
    for family in ("decisions", "incidents", "lessons", "domain_knowledge"):
        family_dir = root / family
        if not family_dir.exists():
            continue
        for path in sorted(family_dir.glob("*.md")):
            if path.name == "README.md":
                continue
            notes.append(path)
    return notes


def review_curated_notes(
    root: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build a review report for active curated memory."""
    current_time = now or datetime.now(UTC)
    review_every_days = _review_every_days()
    notes_root = root or _curated_root()
    records: list[CuratedReviewRecord] = []

    normalized_titles: dict[str, list[Path]] = {}
    ids: dict[str, list[Path]] = {}
    raw_notes: list[tuple[Path, dict[str, Any]]] = []
    for path in _iter_active_curated_notes(notes_root):
        note = parse_markdown_note(path)
        raw_notes.append((path, note.metadata))
        title = str(note.metadata.get("title") or path.stem)
        note_id = str(note.metadata.get("id") or path.stem)
        normalized_titles.setdefault(normalize_text_key(title), []).append(path)
        ids.setdefault(note_id, []).append(path)

    for path, metadata in raw_notes:
        title = str(metadata.get("title") or path.stem)
        note_id = str(metadata.get("id") or path.stem)
        kind = str(metadata.get("kind") or "unknown")
        last_verified_raw = metadata.get("last_verified")
        parsed_last_verified = _parse_iso_datetime(
            last_verified_raw if isinstance(last_verified_raw, str) else None
        )
        days_since_verified: int | None = None
        review_status = "unknown"
        recommendation = "review"
        reasons: list[str] = []

        if parsed_last_verified is not None:
            days_since_verified = max(0, (current_time - parsed_last_verified).days)
            if days_since_verified >= review_every_days * 2:
                review_status = "stale"
                recommendation = "review_or_archive"
                reasons.append("verification:stale")
            elif days_since_verified >= review_every_days:
                review_status = "due"
                recommendation = "review"
                reasons.append("verification:due")
            else:
                review_status = "current"
                recommendation = "keep"
                reasons.append("verification:current")
        else:
            reasons.append("verification:missing")

        normalized_title = normalize_text_key(title)
        if len(normalized_titles.get(normalized_title, [])) > 1:
            reasons.append("duplicate:title")
            if recommendation == "keep":
                recommendation = "review"

        if len(ids.get(note_id, [])) > 1:
            reasons.append("duplicate:id")
            if recommendation == "keep":
                recommendation = "review"

        source_refs = metadata.get("source_refs")
        source_ref_count = len(source_refs) if isinstance(source_refs, list) else 0
        if source_ref_count < 2:
            reasons.append("source_refs:thin")

        summary = str(metadata.get("summary") or "")
        if len(summary.split()) < 6:
            reasons.append("summary:brief")

        promoted_from = metadata.get("promoted_from")
        records.append(
            CuratedReviewRecord(
                path=str(path),
                note_id=note_id,
                title=title,
                kind=kind,
                last_verified=str(last_verified_raw or ""),
                days_since_verified=days_since_verified,
                review_status=review_status,
                recommendation=recommendation,
                source_ref_count=source_ref_count,
                promoted_from=str(promoted_from)
                if isinstance(promoted_from, str)
                else None,
                review_reasons=reasons,
            )
        )

    summary = {
        "note_count": len(records),
        "current_count": sum(record.review_status == "current" for record in records),
        "due_count": sum(record.review_status == "due" for record in records),
        "stale_count": sum(record.review_status == "stale" for record in records),
        "review_every_days": review_every_days,
        "review_candidates": sum(record.recommendation != "keep" for record in records),
    }
    return {
        "ok": True,
        "kind": "curated_review",
        "summary": summary,
        "records": [asdict(record) for record in records],
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Review active curated memory notes for freshness and quality drift."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=_curated_root(),
        help="Curated memory root to review.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the review report as JSON.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    report = review_curated_notes(args.root.resolve())
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    summary = report["summary"]
    print("Curated memory review:")
    print(f"- notes: {summary['note_count']}")
    print(f"- current: {summary['current_count']}")
    print(f"- due: {summary['due_count']}")
    print(f"- stale: {summary['stale_count']}")
    print(f"- review candidates: {summary['review_candidates']}")
    for record in report["records"]:
        if record["recommendation"] == "keep":
            continue
        reasons = ", ".join(record["review_reasons"])
        print(
            f"- {record['path']} [{record['recommendation']}] "
            f"(status={record['review_status']}, reasons={reasons})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
