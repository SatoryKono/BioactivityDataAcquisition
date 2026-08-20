"""Migrate generated passport Markdown paths from underscores to hyphens."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

_SAFE_RELATIVE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_./-]*$")

PASSPORT_GROUPS = ("pipelines", "workflows")
DEFAULT_ROOT = Path(__file__).resolve().parents[3]
PASSPORT_ROOT = Path("docs/04-reference/passports")
_TEXT_SUFFIXES = {".md", ".py", ".yml", ".yaml", ".json", ".toml", ".txt", ".rst"}
_SEARCH_DIRS = ("docs", ".github", "scripts", "tests", "src", "configs")
_SEARCH_FILES = ("mkdocs.yml", "README.md", "CHANGELOG.md")


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


def _iter_text_files(root: Path) -> tuple[Path, ...]:
    """Walk hardcoded repository trees. Paths are not taken from subprocess output."""
    found: list[Path] = []
    for dirname in _SEARCH_DIRS:
        base = root / dirname
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix.lower() in _TEXT_SUFFIXES:
                found.append(path)
    for name in _SEARCH_FILES:
        path = root / name
        if path.is_file():
            found.append(path)
    return tuple(found)


def _files_with_references(
    root: Path,
    pairs: tuple[tuple[str, str], ...],
) -> tuple[Path, ...]:
    if not pairs:
        return ()
    matches: list[Path] = []
    for path in _iter_text_files(root):
        text = path.read_text(encoding="utf-8")
        if any(source in text for source, _ in pairs):
            matches.append(path)
    return tuple(matches)


def _replacement_pairs(
    root: Path,
    plans: tuple[RenamePlan, ...],
) -> tuple[tuple[str, str], ...]:
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
    for group in PASSPORT_GROUPS:
        directory = root / PASSPORT_ROOT / group
        for target_path in sorted(directory.glob("*-*.md")):
            target = target_path.relative_to(root).as_posix()
            source = (
                target_path.with_name(target_path.name.replace("-", "_"))
                .relative_to(root)
                .as_posix()
            )
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
    for path in _files_with_references(root, pairs):
        if not path.is_file() or path in {plan.source for plan in plans}:
            continue
        text = path.read_text(encoding="utf-8")
        if any(source in text for source, _ in pairs):
            matches.append(path)
    return tuple(matches)


def _materialize_repo_file(root: Path, relative_posix: str) -> Path:
    """Rebuild a repo file path from a sanitized relative POSIX string."""
    if not _SAFE_RELATIVE.fullmatch(relative_posix) or ".." in relative_posix.split("/"):
        raise ValueError(f"refusing path outside {root}: {relative_posix}")
    materialized = root.joinpath(*relative_posix.split("/"))
    resolved_root = root.resolve()
    resolved = materialized.resolve()
    if not resolved.is_relative_to(resolved_root):
        raise ValueError(f"refusing path outside {root}: {relative_posix}")
    return materialized


def _replace_pairs(text: str, pairs: tuple[tuple[str, str], ...]) -> str:
    """Apply deterministic path-token replacements to a UTF-8 document."""
    updated = text
    for source, target in pairs:
        updated = updated.replace(source, target)
    return updated


def apply_plan(root: Path, plans: tuple[RenamePlan, ...]) -> tuple[Path, ...]:
    """Rename passports and update constant textual reference files."""
    pairs = _replacement_pairs(root, plans)
    for plan in plans:
        plan.source.rename(plan.target)
    updated_paths: list[Path] = []
    mkdocs = root / "mkdocs.yml"
    if mkdocs.is_file():
        current = mkdocs.read_text(encoding="utf-8")
        rewritten = _replace_pairs(current, pairs)
        if rewritten != current:
            mkdocs.write_text(rewritten, encoding="utf-8")
            updated_paths.append(mkdocs)
    readme = root / "README.md"
    if readme.is_file():
        current = readme.read_text(encoding="utf-8")
        rewritten = _replace_pairs(current, pairs)
        if rewritten != current:
            readme.write_text(rewritten, encoding="utf-8")
            updated_paths.append(readme)
    changelog = root / "CHANGELOG.md"
    if changelog.is_file():
        current = changelog.read_text(encoding="utf-8")
        rewritten = _replace_pairs(current, pairs)
        if rewritten != current:
            changelog.write_text(rewritten, encoding="utf-8")
            updated_paths.append(changelog)
    index = root / "docs" / "04-reference" / "passports" / "index.md"
    if index.is_file():
        current = index.read_text(encoding="utf-8")
        rewritten = _replace_pairs(current, pairs)
        if rewritten != current:
            index.write_text(rewritten, encoding="utf-8")
            updated_paths.append(index)
    return tuple(updated_paths)


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
    if not plans and not references:
        print("Passport Markdown paths already use kebab-case.")
        return 0
    for plan in plans:
        source = plan.source.relative_to(root).as_posix()
        target = plan.target.relative_to(root).as_posix()
        print(f"rename: {source} -> {target}")
    for path in references:
        print(f"update-reference: {path.relative_to(root).as_posix()}")
    if args.check:
        print(
            f"Found {len(plans)} non-canonical passport path(s) and "
            f"{len(references)} file(s) with stale references."
        )
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
