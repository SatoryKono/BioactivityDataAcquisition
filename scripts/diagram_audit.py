#!/usr/bin/env python3
"""Inventory diagram assets in docs/ and export CSV + Markdown reports."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

SUPPORTED_EXTENSIONS = {".mmd", ".mermaid", ".puml", ".d2", ".svg", ".png"}
TEXT_EXTENSIONS = {".mmd", ".mermaid", ".puml", ".d2"}
SOURCE_EXTENSIONS = {".mmd", ".mermaid", ".puml", ".d2", ".meta"}

MERMAID_EDGE_PATTERN = re.compile(r"-->|-\.->|==>|-.->|---")
PLANTUML_EDGE_PATTERN = re.compile(r"-->|<--|<\.|\.>|\*--|o--|--")
D2_EDGE_PATTERN = re.compile(r"\s->\s|\s<->\s|\s--\s")
NODE_ID_PATTERN = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\b")


@dataclass(frozen=True)
class DiagramRow:
    path: str
    name: str
    diag_type: str
    format: str
    nodes_count: int
    edges_count: int
    size_kb: float
    last_modified: str
    status: str
    has_init: bool
    has_view_meta: bool
    parent: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit docs diagrams and export reports"
    )
    parser.add_argument("--docs-root", type=Path, default=Path("docs"))
    parser.add_argument(
        "--csv-out",
        type=Path,
        default=Path("docs/02-architecture/mmd-diagrams/diagram-audit.csv"),
    )
    parser.add_argument(
        "--md-out",
        type=Path,
        default=Path("docs/02-architecture/mmd-diagrams/diagram-audit.md"),
    )
    return parser.parse_args()


def iter_diagram_files(docs_root: Path) -> list[Path]:
    files: list[Path] = []
    for path in docs_root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        files.append(path)
    return sorted(files)


def detect_diag_type(path: Path, content: str) -> str:
    ext = path.suffix.lower()
    if ext in {".svg", ".png"}:
        return "image"

    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("%%") or line.startswith("'"):
            continue
        if line.startswith("graph") or line.startswith("flowchart"):
            return "flowchart"
        if line.startswith("sequenceDiagram"):
            return "sequence"
        if line.startswith("classDiagram"):
            return "class"
        if line.startswith("stateDiagram"):
            return "state"
        if line.startswith("erDiagram"):
            return "er"
        if line.startswith("mindmap"):
            return "mindmap"
        if line.startswith("@startuml"):
            return "plantuml"
        break

    return ext.lstrip(".")


def count_nodes_edges(path: Path, content: str) -> tuple[int, int]:
    ext = path.suffix.lower()
    if ext not in TEXT_EXTENSIONS:
        return 0, 0

    lines = [ln.strip() for ln in content.splitlines() if ln.strip()]

    if ext in {".mmd", ".mermaid"}:
        edges = sum(
            1
            for line in lines
            if MERMAID_EDGE_PATTERN.search(line) and not line.startswith("%%")
        )
        nodes: set[str] = set()
        for line in lines:
            if line.startswith("%%"):
                continue
            if "[" in line or "(" in line or "{" in line:
                for token in NODE_ID_PATTERN.findall(line.split("[")[0]):
                    if token not in {
                        "graph",
                        "flowchart",
                        "classDef",
                        "style",
                        "subgraph",
                        "end",
                    }:
                        nodes.add(token)
            if MERMAID_EDGE_PATTERN.search(line):
                left = line.split("-")[0]
                for token in NODE_ID_PATTERN.findall(left):
                    if token not in {
                        "graph",
                        "flowchart",
                        "classDef",
                        "style",
                        "subgraph",
                        "end",
                    }:
                        nodes.add(token)
        return len(nodes), edges

    if ext == ".puml":
        edges = sum(1 for line in lines if PLANTUML_EDGE_PATTERN.search(line))
        nodes = {
            token
            for line in lines
            if not line.startswith("'")
            for token in NODE_ID_PATTERN.findall(line)
            if token.lower() not in {"startuml", "enduml", "title", "skinparam"}
        }
        return len(nodes), edges

    edges = sum(1 for line in lines if D2_EDGE_PATTERN.search(line))
    nodes = {
        line.split(":", maxsplit=1)[0].strip()
        for line in lines
        if ":" in line and not line.startswith("#")
    }
    return len({n for n in nodes if n}), edges


def has_source_for_image(path: Path) -> bool:
    stem = path.stem
    candidates = [path.with_suffix(ext) for ext in SOURCE_EXTENSIONS]
    candidates.extend((path.parent / f"{stem}{ext}") for ext in SOURCE_EXTENSIONS)
    if path.parent.name in {"svg", "png"}:
        parent = path.parent.parent
        candidates.extend((parent / f"{stem}{ext}") for ext in SOURCE_EXTENSIONS)
    return any(candidate.exists() for candidate in candidates)


def build_row(root: Path, path: Path) -> DiagramRow:
    content = ""
    if path.suffix.lower() in TEXT_EXTENSIONS:
        content = path.read_text(encoding="utf-8")

    nodes_count, edges_count = count_nodes_edges(path, content)
    has_init = "%%{init" in content if content else False
    has_view_meta = "%% View:" in content if content else False

    status = "ok"
    if path.suffix.lower() in {".svg", ".png"} and not has_source_for_image(path):
        status = "missing-source"

    rel_path = path.relative_to(root)
    size_kb = round(path.stat().st_size / 1024, 2)
    last_modified = datetime.fromtimestamp(path.stat().st_mtime).isoformat(
        timespec="seconds"
    )

    return DiagramRow(
        path=str(rel_path),
        name=path.name,
        diag_type=detect_diag_type(path, content),
        format=path.suffix.lower().lstrip("."),
        nodes_count=nodes_count,
        edges_count=edges_count,
        size_kb=size_kb,
        last_modified=last_modified,
        status=status,
        has_init=has_init,
        has_view_meta=has_view_meta,
        parent=str(rel_path.parent),
    )


def write_csv(rows: list[DiagramRow], target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(DiagramRow.__dataclass_fields__.keys())
    with target.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)


def write_markdown(rows: list[DiagramRow], target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    headers = list(DiagramRow.__dataclass_fields__.keys())
    with target.open("w", encoding="utf-8") as fp:
        fp.write("# Diagram audit\n\n")
        fp.write(f"Total files: **{len(rows)}**\n\n")
        fp.write("| " + " | ".join(headers) + " |\n")
        fp.write("|" + "|".join(["---"] * len(headers)) + "|\n")
        for row in rows:
            values = [str(getattr(row, key)) for key in headers]
            fp.write("| " + " | ".join(values) + " |\n")


def main() -> int:
    args = parse_args()
    docs_root = args.docs_root
    if not docs_root.exists():
        raise FileNotFoundError(f"docs root not found: {docs_root}")

    files = iter_diagram_files(docs_root)
    rows = [build_row(docs_root, path) for path in files]

    write_csv(rows, args.csv_out)
    write_markdown(rows, args.md_out)
    sys.stdout.write(f"Wrote {len(rows)} rows to {args.csv_out} and {args.md_out}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
