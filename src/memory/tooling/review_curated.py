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


def _minimum_source_refs() -> int:
    memory_root = discover_memory_root()
    retention = load_yaml_resource(memory_root / "policy" / "retention.yaml")
    return int(retention["artifact_classes"]["curated_note"].get("min_source_refs", 2))


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


def _collect_curated_note_indexes(
    notes_root: Path,
) -> tuple[
    list[tuple[Path, dict[str, Any]]],
    dict[str, list[Path]],
    dict[str, list[Path]],
]:
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
    return raw_notes, normalized_titles, ids


def _freshness_review(
    *,
    last_verified_raw: object,
    current_time: datetime,
    review_every_days: int,
) -> tuple[int | None, str, str, list[str]]:
    parsed_last_verified = _parse_iso_datetime(
        last_verified_raw if isinstance(last_verified_raw, str) else None
    )
    if parsed_last_verified is None:
        return None, "unknown", "review", ["verification:missing"]

    days_since_verified = max(0, (current_time - parsed_last_verified).days)
    if days_since_verified >= review_every_days * 2:
        return (
            days_since_verified,
            "stale",
            "review_or_archive",
            ["verification:stale"],
        )
    if days_since_verified >= review_every_days:
        return days_since_verified, "due", "review", ["verification:due"]
    return days_since_verified, "current", "keep", ["verification:current"]


def _duplicate_reasons(
    *,
    title: str,
    note_id: str,
    normalized_titles: dict[str, list[Path]],
    ids: dict[str, list[Path]],
) -> list[str]:
    reasons: list[str] = []
    if len(normalized_titles.get(normalize_text_key(title), [])) > 1:
        reasons.append("duplicate:title")
    if len(ids.get(note_id, [])) > 1:
        reasons.append("duplicate:id")
    return reasons


def _quality_reasons(
    metadata: dict[str, Any],
    *,
    minimum_source_refs: int,
) -> tuple[int, list[str]]:
    reasons: list[str] = []
    source_refs = metadata.get("source_refs")
    source_ref_count = len(source_refs) if isinstance(source_refs, list) else 0
    if source_ref_count < minimum_source_refs:
        reasons.append("source_refs:thin")

    summary = str(metadata.get("summary") or "")
    if len(summary.split()) < 6:
        reasons.append("summary:brief")
    return source_ref_count, reasons


def _review_recommendation(current: str, reasons: list[str]) -> str:
    if "verification:stale" in reasons:
        return "review_or_archive"
    review_prefixes = ("duplicate:", "source_refs:", "summary:")
    if current == "keep" and any(
        reason.startswith(review_prefixes) for reason in reasons
    ):
        return "review"
    return current


def _build_review_record(
    path: Path,
    metadata: dict[str, Any],
    *,
    current_time: datetime,
    review_every_days: int,
    minimum_source_refs: int,
    normalized_titles: dict[str, list[Path]],
    ids: dict[str, list[Path]],
) -> CuratedReviewRecord:
    title = str(metadata.get("title") or path.stem)
    note_id = str(metadata.get("id") or path.stem)
    kind = str(metadata.get("kind") or "unknown")
    days_since_verified, review_status, recommendation, reasons = _freshness_review(
        last_verified_raw=metadata.get("last_verified"),
        current_time=current_time,
        review_every_days=review_every_days,
    )
    reasons.extend(
        _duplicate_reasons(
            title=title,
            note_id=note_id,
            normalized_titles=normalized_titles,
            ids=ids,
        )
    )
    source_ref_count, quality_reasons = _quality_reasons(
        metadata,
        minimum_source_refs=minimum_source_refs,
    )
    reasons.extend(quality_reasons)
    recommendation = _review_recommendation(recommendation, reasons)

    promoted_from = metadata.get("promoted_from")
    return CuratedReviewRecord(
        path=str(path),
        note_id=note_id,
        title=title,
        kind=kind,
        last_verified=str(metadata.get("last_verified") or ""),
        days_since_verified=days_since_verified,
        review_status=review_status,
        recommendation=recommendation,
        source_ref_count=source_ref_count,
        promoted_from=str(promoted_from) if isinstance(promoted_from, str) else None,
        review_reasons=reasons,
    )


def _review_summary(
    records: list[CuratedReviewRecord],
    *,
    review_every_days: int,
) -> dict[str, int]:
    return {
        "note_count": len(records),
        "current_count": sum(record.review_status == "current" for record in records),
        "due_count": sum(record.review_status == "due" for record in records),
        "stale_count": sum(record.review_status == "stale" for record in records),
        "review_every_days": review_every_days,
        "review_candidates": sum(record.recommendation != "keep" for record in records),
    }


def review_curated_notes(
    root: Path | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build a review report for active curated memory."""
    current_time = now or datetime.now(UTC)
    review_every_days = _review_every_days()
    minimum_source_refs = _minimum_source_refs()
    notes_root = root or _curated_root()
    raw_notes, normalized_titles, ids = _collect_curated_note_indexes(notes_root)
    records = [
        _build_review_record(
            path,
            metadata,
            current_time=current_time,
            review_every_days=review_every_days,
            minimum_source_refs=minimum_source_refs,
            normalized_titles=normalized_titles,
            ids=ids,
        )
        for path, metadata in raw_notes
    ]
    return {
        "ok": True,
        "kind": "curated_review",
        "summary": _review_summary(records, review_every_days=review_every_days),
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
    parser.add_argument(
        "--fail-on-review-candidates",
        action="store_true",
        help="Exit non-zero when due, stale, duplicate, or thin curated notes need review.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    report = review_curated_notes(args.root.resolve())
    has_review_candidates = bool(report["summary"]["review_candidates"])
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 1 if args.fail_on_review_candidates and has_review_candidates else 0

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
    return 1 if args.fail_on_review_candidates and has_review_candidates else 0


if __name__ == "__main__":
    raise SystemExit(main())
