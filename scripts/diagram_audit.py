#!/usr/bin/env python3
"""Inventory and policy-oriented metadata audit for diagram files under docs/."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

SUPPORTED_EXTS: set[str] = {".mermaid", ".mmd", ".puml", ".d2", ".svg", ".png"}
FLOW_EDGE_RE = re.compile(r"(<-->|-->|<--|-.->|---|==>|<==)")
INIT_RE = re.compile(r"%%\{\s*(init|initialize)\s*:", re.IGNORECASE)
VIEW_RE = re.compile(r"(?m)^\s*%%\s*View\s*:")
PARENT_RE = re.compile(r"(?im)^\s*%%\s*Parent\s*:\s*([^\s]+)")


@dataclass(frozen=True)
class InventoryRow:
    path: str
    name: str
    diag_type: str
    format: str
    nodes_count: str
    edges_count: str
    size_kb: str
    last_modified: str
    status: str
    has_init: str
    has_view_meta: str
    parent: str


def run_command(command: list[str]) -> tuple[int, str]:
    process = subprocess.run(
        command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return process.returncode, (process.stdout or "").strip()


def get_git_last_modified(path: Path) -> str | None:
    code, output = run_command(["git", "log", "-1", "--format=%cI %h", "--", str(path)])
    if code == 0 and output:
        return output
    return None


def get_mtime_iso(path: Path) -> str:
    timestamp = path.stat().st_mtime
    return dt.datetime.fromtimestamp(timestamp).isoformat(timespec="seconds")


def read_text(path: Path, limit: int = 400_000) -> str:
    return path.read_bytes()[:limit].decode("utf-8", errors="replace")


def detect_mermaid_type(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    meaningful_lines = [line for line in lines if line and not line.startswith("%%")]
    if not meaningful_lines:
        return "other"

    header = meaningful_lines[0].lower()
    if header.startswith(("flowchart", "graph")):
        return "flowchart"
    if header.startswith("classdiagram"):
        return "class"
    if header.startswith("sequencediagram"):
        return "sequence"
    if header.startswith("erdiagram"):
        return "er"
    if re.search(r"\bC4(Context|Container|Component)\b", text, re.IGNORECASE):
        return "C4"
    if re.search(r"\bbronze\b.*\bsilver\b.*\bgold\b", text, re.IGNORECASE | re.DOTALL):
        return "DAG"
    return "other"


def count_flowchart_nodes_edges(text: str) -> tuple[int, int]:
    nodes: set[str] = set()
    edges = 0

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if (
            not line
            or line.startswith("%%")
            or line.startswith("style ")
            or line.startswith("classDef")
            or line.startswith("linkStyle")
        ):
            continue

        normalized = re.sub(r"\|[^|]*\|", "|", line)
        edges += len(FLOW_EDGE_RE.findall(normalized))

        for match in re.finditer(
            r"([A-Za-z0-9_.-]+)\s*(<-->|-->|<--|-.->|---|==>|<==)\s*([A-Za-z0-9_.-]+)",
            normalized,
        ):
            nodes.add(match.group(1))
            nodes.add(match.group(3))

        for bracketed in re.finditer(r"(^|\s)([A-Za-z0-9_.-]+)\s*[\[\(\{]", normalized):
            nodes.add(bracketed.group(2))

    return len(nodes), edges


def classify_status(nodes: int | None) -> str:
    if nodes is None:
        return "UNKNOWN"
    if nodes >= 35:
        return "CRITICAL"
    if nodes >= 20:
        return "OVERLOADED"
    return "OK"


def iter_diagram_files(root: Path) -> list[Path]:
    return sorted(
        [
            path
            for path in root.rglob("*")
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTS
        ]
    )


def create_row(path: Path, use_git: bool) -> InventoryRow:
    ext = path.suffix.lower()
    fmt = ext.lstrip(".")
    last_modified = get_git_last_modified(path) if use_git else None
    if last_modified is None:
        last_modified = get_mtime_iso(path)

    size_kb = f"{path.stat().st_size / 1024.0:.1f}"
    diag_type = "other"
    nodes_count: int | None = None
    edges_count: int | None = None
    has_init = "false"
    has_view_meta = "false"
    parent = ""

    if ext in {".mermaid", ".mmd"}:
        text = read_text(path)
        diag_type = detect_mermaid_type(text)
        if diag_type == "flowchart":
            nodes_count, edges_count = count_flowchart_nodes_edges(text)
        has_init = "true" if INIT_RE.search(text) else "false"
        has_view_meta = "true" if VIEW_RE.search(text) else "false"
        parent_match = PARENT_RE.search(text)
        if parent_match:
            parent = parent_match.group(1)

    return InventoryRow(
        path=str(path),
        name=path.name,
        diag_type=diag_type,
        format=fmt,
        nodes_count=str(nodes_count) if nodes_count is not None else "NA",
        edges_count=str(edges_count) if edges_count is not None else "NA",
        size_kb=size_kb,
        last_modified=last_modified,
        status=classify_status(nodes_count),
        has_init=has_init,
        has_view_meta=has_view_meta,
        parent=parent,
    )


def write_csv(rows: list[InventoryRow], out_path: Path) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].__dict__.keys())
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def write_markdown(rows: list[InventoryRow], out_path: Path) -> None:
    headers = [
        "path",
        "name",
        "diag_type",
        "format",
        "nodes_count",
        "edges_count",
        "size_kb",
        "last_modified",
        "status",
        "has_init",
        "has_view_meta",
        "parent",
    ]
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join(["---"] * len(headers)) + "|",
    ]
    for row in rows:
        row_data = [getattr(row, header) for header in headers]
        lines.append("| " + " | ".join(row_data) + " |")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit diagrams in docs/ and export inventory."
    )
    parser.add_argument("--docs", default="docs", help="Root directory to scan.")
    parser.add_argument("--out-csv", required=True, help="CSV output path.")
    parser.add_argument("--out-md", required=True, help="Markdown output path.")
    parser.add_argument(
        "--use-git", action="store_true", help="Use git log for last_modified."
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    docs_root = Path(args.docs)
    rows = [create_row(path, args.use_git) for path in iter_diagram_files(docs_root)]

    write_csv(rows, Path(args.out_csv))
    write_markdown(rows, Path(args.out_md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
