#!/usr/bin/env python3
"""Report &nbsp; density in Mermaid source files."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

try:
    from scripts.diagrams.core.diagram_paths import DIAGRAM_ROOT
except ImportError:  # pragma: no cover - direct script execution
    from scripts.diagrams.core.diagram_paths import DIAGRAM_ROOT


SUPPORTED_SUFFIXES = {".mmd", ".mermaid"}
DEFAULT_ROOTS = [
    DIAGRAM_ROOT,
    Path("docs/02-architecture/diagrams/mermaid"),
]


@dataclass
class FilePaddingStat:
    path: Path
    nbsp_count: int
    line_count: int
    lines_with_nbsp: int

    @property
    def nbps_per_line(self) -> float:
        if self.line_count == 0:
            return 0.0
        return self.nbsp_count / self.line_count


def collect_files(roots: list[Path]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        if root.is_file() and root.suffix in SUPPORTED_SUFFIXES:
            files.append(root)
            continue
        if not root.exists():
            continue
        files.extend(
            p
            for p in root.rglob("*")
            if p.is_file()
            and p.suffix in SUPPORTED_SUFFIXES
            and not p.name.startswith("_")
            and "99-archive" not in p.parts
        )
    return sorted(set(files))


def analyze_file(path: Path) -> FilePaddingStat:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    nbsp_count = text.count("&nbsp;")
    lines_with_nbsp = sum(1 for line in lines if "&nbsp;" in line)
    return FilePaddingStat(
        path=path,
        nbsp_count=nbsp_count,
        line_count=len(lines),
        lines_with_nbsp=lines_with_nbsp,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Report top Mermaid files by &nbsp; usage."
    )
    parser.add_argument(
        "--top",
        type=int,
        default=25,
        help="Number of top files to print (default: 25)",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Optional files/dirs to scan (default: canonical diagram roots)",
    )
    args = parser.parse_args()

    roots = [Path(p) for p in args.paths] if args.paths else DEFAULT_ROOTS
    files = collect_files(roots)
    if not files:
        print("No Mermaid files found.")
        return

    stats = [analyze_file(path) for path in files]
    stats.sort(key=lambda item: item.nbsp_count, reverse=True)

    total_nbsp = sum(item.nbsp_count for item in stats)
    total_files = len(stats)
    with_nbsp = sum(1 for item in stats if item.nbsp_count > 0)

    print(
        f"Scanned {total_files} file(s); "
        f"{with_nbsp} contain &nbsp;; total &nbsp;={total_nbsp}"
    )
    print("")
    print("Top files by &nbsp; count:")
    print("count  lines_with_nbsp  nbps/line  path")
    for item in stats[: max(args.top, 0)]:
        if item.nbsp_count == 0:
            break
        print(
            f"{item.nbsp_count:5d}  "
            f"{item.lines_with_nbsp:15d}  "
            f"{item.nbps_per_line:9.2f}  "
            f"{item.path.as_posix()}"
        )


if __name__ == "__main__":
    main()
