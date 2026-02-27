#!/usr/bin/env python3
"""Inventory and classify diagram files under docs/."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

SUPPORTED_EXTENSIONS: set[str] = {".mermaid", ".mmd", ".puml", ".d2", ".svg", ".png"}
INIT_RE = re.compile(r"%%\{\s*(init|initialize)\s*:", re.IGNORECASE)
VIEW_RE = re.compile(r"(?m)^\s*%%\s*View\s*:")
PARENT_RE = re.compile(r"(?i)\bParent\s*:\s*([^\s|]+)")
FLOW_EDGE_RE = re.compile(r"(<-->|-->|<--|-.->|---|==>|<==|<==>)")


@dataclass(frozen=True)
class DiagramInventoryRow:
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
    return_code, output = run_command(
        ["git", "log", "-1", "--format=%cI %h", "--", str(path)]
    )
    if return_code == 0 and output:
        return output
    return None


def get_mtime_iso(path: Path) -> str:
    return dt.datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")


def read_text(path: Path, limit: int = 400_000) -> str:
    return path.read_bytes()[:limit].decode("utf-8", errors="replace")


def detect_mermaid_type(text: str) -> str:
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("%%")
    ]
    head = lines[0].lower() if lines else ""
    if head.startswith(("flowchart", "graph")):
        return "flowchart"
    if head.startswith("classdiagram"):
        return "class"
    if head.startswith("sequencediagram"):
        return "sequence"
    if head.startswith("erdiagram"):
        return "er"
    if re.search(r"\bC4(Context|Container|Component)\b", text, re.IGNORECASE):
        return "C4"
    return "other"


def count_flowchart_nodes_and_edges(text: str) -> tuple[int, int]:
    nodes: set[str] = set()
    edges = 0

    for line in text.splitlines():
        stripped = line.strip()
        if (
            not stripped
            or stripped.startswith("%%")
            or stripped.startswith(("style ", "classDef", "linkStyle"))
        ):
            continue

        normalized = re.sub(r"\|[^|]*\|", "|", stripped)
        edges += len(FLOW_EDGE_RE.findall(normalized))

        for match in re.finditer(
            r"([A-Za-z0-9_.-]+)\s*(?:<-->|-->|<--|-.->|---|==>|<==|<==>)\s*([A-Za-z0-9_.-]+)",
            normalized,
        ):
            nodes.add(match.group(1))
            nodes.add(match.group(2))

        for match in re.finditer(r"(^|\s)([A-Za-z0-9_.-]+)\s*[\[(\{]", normalized):
            nodes.add(match.group(2))

    return len(nodes), edges


def classify_status(nodes_count: int | None) -> str:
    if nodes_count is None:
        return "UNKNOWN"
    if nodes_count >= 35:
        return "CRITICAL"
    if nodes_count >= 20:
        return "OVERLOADED"
    return "OK"


def iter_diagram_files(root: Path) -> list[Path]:
    return [
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    ]


def build_row(path: Path, use_git: bool) -> DiagramInventoryRow:
    extension = path.suffix.lower()
    file_format = extension.lstrip(".")
    last_modified = get_git_last_modified(path) if use_git else None
    if not last_modified:
        last_modified = get_mtime_iso(path)

    size_kb = f"{(path.stat().st_size / 1024.0):.1f}"
    diag_type = "other"
    nodes_count: int | None = None
    edges_count: int | None = None
    has_init = "false"
    has_view_meta = "false"
    parent = ""

    if extension in {".mmd", ".mermaid"}:
        text = read_text(path)
        diag_type = detect_mermaid_type(text)
        if diag_type == "flowchart":
            nodes_count, edges_count = count_flowchart_nodes_and_edges(text)
        has_init = "true" if INIT_RE.search(text) else "false"
        has_view_meta = "true" if VIEW_RE.search(text) else "false"
        parent_match = PARENT_RE.search(text)
        if parent_match:
            parent = parent_match.group(1)

    return DiagramInventoryRow(
        path=str(path),
        name=path.name,
        diag_type=diag_type,
        format=file_format,
        nodes_count=str(nodes_count) if nodes_count is not None else "NA",
        edges_count=str(edges_count) if edges_count is not None else "NA",
        size_kb=size_kb,
        last_modified=last_modified,
        status=classify_status(nodes_count),
        has_init=has_init,
        has_view_meta=has_view_meta,
        parent=parent,
    )


def write_csv(rows: list[DiagramInventoryRow], output_path: Path) -> None:
    if not rows:
        output_path.write_text(
            "path,name,diag_type,format,nodes_count,edges_count,size_kb,last_modified,status,has_init,has_view_meta,parent\n",
            encoding="utf-8",
        )
        return

    field_names = list(asdict(rows[0]).keys())
    with output_path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=field_names)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def write_markdown(rows: list[DiagramInventoryRow], output_path: Path) -> None:
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
        lines.append(
            "| "
            + " | ".join(
                [
                    row.path,
                    row.name,
                    row.diag_type,
                    row.format,
                    row.nodes_count,
                    row.edges_count,
                    row.size_kb,
                    row.last_modified,
                    row.status,
                    row.has_init,
                    row.has_view_meta,
                    row.parent,
                ]
            )
            + " |"
        )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--docs", default="docs")
    parser.add_argument("--out-csv", required=True)
    parser.add_argument("--out-md", required=True)
    parser.add_argument("--use-git", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    docs_root = Path(args.docs)
    rows = [
        build_row(path, args.use_git) for path in sorted(iter_diagram_files(docs_root))
    ]

    write_csv(rows, Path(args.out_csv))
    write_markdown(rows, Path(args.out_md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
