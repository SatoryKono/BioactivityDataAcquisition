"""Prune expiring episodic memory artifacts."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from memory.resources import POLICY_DIR, load_yaml_resource

EPISODIC_ROOT = Path(__file__).resolve().parents[1] / "episodic"
SUPPORTED_NOTE_EXTENSIONS = {".json", ".yaml", ".yml", ".md"}


@dataclass(frozen=True, slots=True)
class PruneCandidate:
    """Represents one episodic artifact eligible for pruning."""

    path: str
    created_at: str
    ttl_days: int
    expires_at: str


def _default_ttl_days() -> int:
    retention = load_yaml_resource(POLICY_DIR / "retention.yaml")
    return int(retention["artifact_classes"]["episodic_note"]["ttl_days"])


def _parse_iso_datetime(value: str) -> datetime | None:
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _coerce_created_at(value: object) -> datetime | None:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
    if isinstance(value, str):
        return _parse_iso_datetime(value)
    return None


def _extract_metadata(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        return json.loads(text)
    if path.suffix in {".yaml", ".yml"}:
        return yaml.safe_load(text) or {}
    if path.suffix == ".md" and text.startswith("---\n"):
        parts = text.split("\n---\n", 1)
        if len(parts) == 2:
            return yaml.safe_load(parts[0][4:]) or {}
    return {}


def find_prunable_episodic_notes(
    root: Path = EPISODIC_ROOT,
    *,
    now: datetime | None = None,
) -> list[PruneCandidate]:
    """Find episodic notes whose TTL has expired."""
    current_time = now or datetime.now(UTC)
    default_ttl = _default_ttl_days()
    candidates: list[PruneCandidate] = []

    if not root.exists():
        return candidates

    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in SUPPORTED_NOTE_EXTENSIONS:
            continue
        if path.name == "README.md":
            continue
        metadata = _extract_metadata(path)
        created_at = _coerce_created_at(metadata.get("created_at"))
        if created_at is None:
            created_at = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
        ttl_days = int(metadata.get("ttl_days", default_ttl))
        expires_at = created_at + timedelta(days=ttl_days)
        if expires_at <= current_time:
            candidates.append(
                PruneCandidate(
                    path=str(path),
                    created_at=created_at.isoformat(),
                    ttl_days=ttl_days,
                    expires_at=expires_at.isoformat(),
                )
            )
    return candidates


def prune_episodic_notes(
    root: Path = EPISODIC_ROOT,
    *,
    apply: bool = False,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Report or prune expired episodic notes."""
    candidates = find_prunable_episodic_notes(root, now=now)
    removed_paths: list[str] = []
    if apply:
        for candidate in candidates:
            candidate_path = Path(candidate.path)
            if candidate_path.exists():
                candidate_path.unlink()
                removed_paths.append(candidate.path)
    return {
        "apply": apply,
        "candidate_count": len(candidates),
        "removed_count": len(removed_paths),
        "candidates": [asdict(candidate) for candidate in candidates],
        "removed_paths": removed_paths,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prune episodic memory artifacts that exceeded TTL."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=EPISODIC_ROOT,
        help="Episodic memory root to scan.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Delete expired notes. Default mode is report-only.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit prune report as JSON.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    report = prune_episodic_notes(args.root.resolve(), apply=args.apply)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        mode = "apply" if args.apply else "dry-run"
        print(f"Episodic prune {mode}: {report['candidate_count']} candidate(s)")
        if args.apply:
            print(f"Removed: {report['removed_count']}")
        for candidate in report["candidates"]:
            print(
                f"- {candidate['path']} (created_at={candidate['created_at']}, "
                f"expires_at={candidate['expires_at']})"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
