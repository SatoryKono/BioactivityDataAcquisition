#!/usr/bin/env python3
"""Migrate extensionless VCR cassettes to canonical .yaml names."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
VCR_ROOT = ROOT / "tests" / "fixtures" / "vcr"
ALLOWLIST_FILE = ROOT / ".github" / "vcr-noext-allowlist.txt"

ALLOWLIST_HEADER = [
    "# Legacy VCR cassette files without .yaml extension.",
    "# Policy: no new extensionless VCR files should be added.",
    "# Existing entries are allowlisted for gradual migration.",
]


def _collect_extensionless() -> list[Path]:
    if not VCR_ROOT.exists():
        return []
    return sorted(
        path
        for path in VCR_ROOT.rglob("*")
        if path.is_file() and path.name != ".gitkeep" and "." not in path.name
    )


def _rewrite_allowlist(extensionless_files: list[Path]) -> None:
    lines = [*ALLOWLIST_HEADER]
    lines.extend(path.relative_to(ROOT).as_posix() for path in extensionless_files)
    ALLOWLIST_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Migrate extensionless VCR cassette names to *.yaml where missing. "
            "By default runs as dry-run."
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply file renames (default is dry-run).",
    )
    parser.add_argument(
        "--sync-allowlist",
        action="store_true",
        help="Rewrite .github/vcr-noext-allowlist.txt based on current extensionless files.",
    )
    parser.add_argument(
        "--drop-paired",
        action="store_true",
        help=(
            "When used with --apply, delete extensionless files that already have "
            "a sibling *.yaml file."
        ),
    )
    return parser.parse_args()


def _partition_extensionless(
    extensionless: list[Path],
) -> tuple[list[tuple[Path, Path]], list[tuple[Path, Path]]]:
    pairs: list[tuple[Path, Path]] = []
    solo: list[tuple[Path, Path]] = []
    for path in extensionless:
        yaml_path = path.with_name(f"{path.name}.yaml")
        if yaml_path.exists():
            pairs.append((path, yaml_path))
        else:
            solo.append((path, yaml_path))
    return pairs, solo


def _print_inventory(
    extensionless: list[Path],
    pairs: list[tuple[Path, Path]],
    solo: list[tuple[Path, Path]],
) -> None:
    sys.stdout.write(
        "VCR migration inventory: "
        f"extensionless={len(extensionless)} paired={len(pairs)} solo={len(solo)}\n"
    )
    if not solo:
        return

    sys.stdout.write("Solo files (can be migrated safely):\n")
    for source, target in solo:
        sys.stdout.write(
            f"  - {source.relative_to(ROOT)} -> {target.relative_to(ROOT)}\n"
        )


def _apply_migration(
    solo: list[tuple[Path, Path]],
    pairs: list[tuple[Path, Path]],
    *,
    drop_paired: bool,
) -> tuple[int, int]:
    migrated = 0
    dropped_paired = 0
    for source, target in solo:
        source.rename(target)
        migrated += 1

    if not drop_paired:
        return migrated, dropped_paired

    for source, _ in pairs:
        source.unlink()
        dropped_paired += 1
    return migrated, dropped_paired


def _print_migration_summary(
    *,
    updated_extensionless: list[Path],
    migrated: int,
    dropped_paired: int,
    had_pairs: bool,
    drop_paired: bool,
) -> None:
    sys.stdout.write(
        "Migration complete: "
        f"migrated={migrated}, dropped_paired={dropped_paired}, "
        f"remaining_extensionless={len(updated_extensionless)}\n"
    )
    if had_pairs and not drop_paired:
        sys.stdout.write(
            "NOTE: paired files were preserved (manual review required before deletion).\n"
        )


def _maybe_sync_allowlist(
    extensionless_files: list[Path],
    *,
    sync_allowlist: bool,
    dry_run: bool,
) -> None:
    if not sync_allowlist:
        return
    _rewrite_allowlist(extensionless_files)
    if dry_run:
        sys.stdout.write("Allowlist synchronized (dry-run mode for file renames).\n")


def _run_dry_mode(extensionless: list[Path], *, sync_allowlist: bool) -> None:
    _maybe_sync_allowlist(extensionless, sync_allowlist=sync_allowlist, dry_run=True)


def _run_apply_mode(
    solo: list[tuple[Path, Path]],
    pairs: list[tuple[Path, Path]],
    *,
    sync_allowlist: bool,
    drop_paired: bool,
) -> None:
    migrated, dropped_paired = _apply_migration(
        solo,
        pairs,
        drop_paired=drop_paired,
    )
    updated_extensionless = _collect_extensionless()
    _maybe_sync_allowlist(
        updated_extensionless,
        sync_allowlist=sync_allowlist,
        dry_run=False,
    )
    _print_migration_summary(
        updated_extensionless=updated_extensionless,
        migrated=migrated,
        dropped_paired=dropped_paired,
        had_pairs=bool(pairs),
        drop_paired=drop_paired,
    )


def main() -> None:
    args = _parse_args()
    extensionless = _collect_extensionless()
    pairs, solo = _partition_extensionless(extensionless)
    _print_inventory(extensionless, pairs, solo)

    if not args.apply:
        _run_dry_mode(extensionless, sync_allowlist=args.sync_allowlist)
        return

    _run_apply_mode(
        solo,
        pairs,
        sync_allowlist=args.sync_allowlist,
        drop_paired=args.drop_paired,
    )


if __name__ == "__main__":
    main()
