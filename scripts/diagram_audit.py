#!/usr/bin/env python3
"""Diagram inventory audit with CSV/Markdown export."""

from __future__ import annotations

import argparse
import csv
import subprocess  # nosec B404
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

DIAGRAM_SUFFIXES = {".mmd", ".mermaid", ".png", ".svg"}
VIEW_MARKERS = ("%% View:", "%% Parent source:", "%% Title:")
SOURCE_META_SUFFIXES = (".meta", ".source", ".md")


@dataclass(slots=True)
class DiagramRecord:
    path: str
    kind: str
    has_init_directive: bool
    has_view_metadata: bool
    has_source_policy: bool


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build inventory for Mermaid/diagram assets and export CSV/Markdown."
    )
    parser.add_argument("--docs", default="docs", help="Root docs directory to scan.")
    parser.add_argument("--out-csv", default="", help="Optional CSV output path.")
    parser.add_argument("--out-md", default="", help="Optional Markdown output path.")
    parser.add_argument(
        "--use-git",
        action="store_true",
        help="Use git tracked files under --docs instead of filesystem walk.",
    )
    return parser.parse_args()


def _tracked_files(docs_root: Path) -> list[Path]:
    result = subprocess.run(  # nosec B603,B607
        ["git", "ls-files", str(docs_root)],
        check=True,
        capture_output=True,
        text=True,
    )
    files: list[Path] = []
    for line in result.stdout.splitlines():
        candidate = Path(line.strip())
        if candidate.suffix.lower() in DIAGRAM_SUFFIXES:
            files.append(candidate)
    return sorted(files)


def _walk_files(docs_root: Path) -> list[Path]:
    items: list[Path] = []
    for suffix in DIAGRAM_SUFFIXES:
        items.extend(docs_root.rglob(f"*{suffix}"))
    return sorted(items)


def _read_text_safe(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return ""


def _has_source_policy(image_path: Path) -> bool:
    siblings = {p.name: p for p in image_path.parent.iterdir() if p.is_file()}
    stem = image_path.stem

    if f"{stem}.mmd" in siblings or f"{stem}.mermaid" in siblings:
        return True

    for suffix in SOURCE_META_SUFFIXES:
        file_name = f"{image_path.name}{suffix}"
        if file_name in siblings:
            return True

    for suffix in SOURCE_META_SUFFIXES:
        file_name = f"{stem}{suffix}"
        sidecar = siblings.get(file_name)
        if sidecar is None:
            continue
        content = _read_text_safe(sidecar).lower()
        if "source:" in content or "parent source:" in content:
            return True

    return False


def _record_for(path: Path) -> DiagramRecord:
    suffix = path.suffix.lower()
    text = _read_text_safe(path) if suffix in {".mmd", ".mermaid"} else ""

    has_init = "%%{init:" in text if text else False
    has_view_metadata = (
        any(marker in text for marker in VIEW_MARKERS) if text else False
    )
    has_source_policy = _has_source_policy(path) if suffix in {".png", ".svg"} else True

    return DiagramRecord(
        path=str(path),
        kind=suffix.lstrip("."),
        has_init_directive=has_init,
        has_view_metadata=has_view_metadata,
        has_source_policy=has_source_policy,
    )


def _write_csv(records: list[DiagramRecord], out_csv: Path) -> None:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "path",
                "kind",
                "has_init_directive",
                "has_view_metadata",
                "has_source_policy",
            ],
        )
        writer.writeheader()
        for item in records:
            writer.writerow(asdict(item))


def _write_markdown(records: list[DiagramRecord], out_md: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Diagram Audit Inventory",
        "",
        "| Path | Kind | Init directive | View metadata | Source policy |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in records:
        lines.append(
            "| {path} | {kind} | {init} | {view} | {source} |".format(
                path=item.path,
                kind=item.kind,
                init="yes" if item.has_init_directive else "no",
                view="yes" if item.has_view_metadata else "no",
                source="yes" if item.has_source_policy else "no",
            )
        )

    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = _parse_args()
    docs_root = Path(args.docs)

    if not docs_root.exists():
        raise SystemExit(f"Docs directory not found: {docs_root}")

    files = _tracked_files(docs_root) if args.use_git else _walk_files(docs_root)
    records = [_record_for(path) for path in files]

    if args.out_csv:
        _write_csv(records, Path(args.out_csv))
    if args.out_md:
        _write_markdown(records, Path(args.out_md))

    sys.stdout.write(f"Inventory size: {len(records)}\n")
    sys.stdout.write(
        f"Files with init directive: {sum(1 for r in records if r.has_init_directive)}\n"
    )
    sys.stdout.write(
        f"Files with view metadata: {sum(1 for r in records if r.has_view_metadata)}\n"
    )
    sys.stdout.write(
        f"Image files respecting source policy: {sum(1 for r in records if r.kind in {'png', 'svg'} and r.has_source_policy)}\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
