"""Migrate generated passport Markdown paths from underscores to hyphens."""

from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path

PASSPORT_GROUPS = ("pipelines", "workflows")
DEFAULT_ROOT = Path(__file__).resolve().parents[3]
PASSPORT_ROOT = Path("docs/04-reference/passports")


@dataclass(frozen=True, slots=True)
class RenamePlan:
    """One passport path migration."""

    source: Path
    target: Path


def build_plan(root: Path) -> tuple[RenamePlan, ...]:
    """Return deterministic underscore-to-hyphen passport rename operations."""
    plans: list[RenamePlan] = []
    for group in PASSPORT_GROUPS:
        directory = root / PASSPORT_ROOT / group
        for source in sorted(directory.glob("*_*.md")):
            target = source.with_name(source.name.replace("_", "-"))
            if target.exists() and target != source:
                raise FileExistsError(
                    f"Cannot rename {source.relative_to(root).as_posix()}: "
                    f"target exists: {target.relative_to(root).as_posix()}"
                )
            plans.append(RenamePlan(source=source, target=target))
    return tuple(plans)


def _tracked_files(root: Path) -> tuple[Path, ...]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    return tuple(
        root / item.decode("utf-8")
        for item in result.stdout.split(b"\0")
        if item
    )


def _replacement_pairs(root: Path, plans: tuple[RenamePlan, ...]) -> tuple[tuple[str, str], ...]:
    pairs: set[tuple[str, str]] = set()
    for plan in plans:
        source = plan.source.relative_to(root).as_posix()
        target = plan.target.relative_to(root).as_posix()
        pairs.add((source, target))
        pairs.add(
            (
                source.removeprefix(f"{PASSPORT_ROOT.as_posix()}/"),
                target.removeprefix(f"{PASSPORT_ROOT.as_posix()}/"),
            )
        )
    return tuple(sorted(pairs, key=lambda item: (-len(item[0]), item[0])))


def referenced_files(
    root: Path,
    plans: tuple[RenamePlan, ...],
) -> tuple[Path, ...]:
    """Return tracked UTF-8 files containing paths that the migration updates."""
    pairs = _replacement_pairs(root, plans)
    matches: list[Path] = []
    for path in _tracked_files(root):
        if not path.is_file() or path in {plan.source for plan in plans}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if any(source in text for source, _ in pairs):
            matches.append(path)
    return tuple(matches)


def apply_plan(root: Path, plans: tuple[RenamePlan, ...]) -> tuple[Path, ...]:
    """Rename passports and update every tracked textual reference."""
    pairs = _replacement_pairs(root, plans)
    references = referenced_files(root, plans)
    for plan in plans:
        plan.source.rename(plan.target)
    for path in references:
        text = path.read_text(encoding="utf-8")
        updated = text
        for source, target in pairs:
            updated = updated.replace(source, target)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
    return references


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Rename generated pipeline/workflow passport Markdown files to "
            "kebab-case and update tracked repository references."
        )
    )
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--apply",
        action="store_true",
        help="Apply the reported renames and reference updates.",
    )
    mode.add_argument(
        "--check",
        action="store_true",
        help="Fail if underscore passport paths remain.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run dry-run (default), apply, or CI check mode."""
    args = _parser().parse_args(argv)
    root = args.root.resolve()
    plans = build_plan(root)
    references = referenced_files(root, plans)
    if not plans:
        print("Passport Markdown paths already use kebab-case.")
        return 0
    for plan in plans:
        source = plan.source.relative_to(root).as_posix()
        target = plan.target.relative_to(root).as_posix()
        print(f"rename: {source} -> {target}")
    for path in references:
        print(f"update-reference: {path.relative_to(root).as_posix()}")
    if args.check:
        print(f"Found {len(plans)} non-canonical passport path(s).")
        return 1
    if not args.apply:
        print("Dry run only; pass --apply to update the repository.")
        return 0
    apply_plan(root, plans)
    print(
        f"Renamed {len(plans)} passport(s); "
        f"updated {len(references)} referenced file(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
