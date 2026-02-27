#!/usr/bin/env python3
"""Build inventory reports for diagram files under docs/."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

SUPPORTED_EXTS: set[str] = {".mermaid", ".mmd", ".puml", ".d2", ".svg", ".png"}
INIT_RE = re.compile(r"%%\{\s*(init|initialize)\s*:", re.IGNORECASE)
VIEW_RE = re.compile(r"(?m)^\s*%%\s*View\s*:")
PARENT_RE = re.compile(r"(?i)\bParent\s*:\s*([^\s|]+)")
FLOW_EDGE_RE = re.compile(r"(<-->|-->|<--|-.->|---|==>|<==)")
FLOW_NODE_RE = re.compile(
    r"([A-Za-z0-9_.-]+)\s*(?:<-->|-->|<--|-.->|---|==>|<==)\s*([A-Za-z0-9_.-]+)"
)
SHAPE_NODE_RE = re.compile(r"(^|\s)([A-Za-z0-9_.-]+)\s*[\[\(\{]")


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit diagrams in docs/ and export report files"
    )
    parser.add_argument("--docs", default="docs", help="Docs root to scan")
    parser.add_argument("--out-csv", required=True, help="Output CSV path")
    parser.add_argument("--out-md", required=True, help="Output markdown path")
    parser.add_argument(
        "--use-git", action="store_true", help="Use git commit timestamp"
    )
    return parser.parse_args()


def run_command(command: list[str]) -> tuple[int, str]:
    proc = subprocess.run(
        command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return proc.returncode, (proc.stdout or "").strip()


def get_git_last_modified(path: Path) -> str | None:
    code, output = run_command(["git", "log", "-1", "--format=%cI %h", "--", str(path)])
    if code == 0 and output:
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


def count_flowchart_nodes_edges(text: str) -> tuple[int, int]:
    nodes: set[str] = set()
    edges = 0

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if (
            not line
            or line.startswith("%%")
            or line.startswith(("style ", "classDef", "linkStyle"))
        ):
            continue
        normalized = re.sub(r"\|[^|]*\|", "|", line)
        edges += len(FLOW_EDGE_RE.findall(normalized))
        for match in FLOW_NODE_RE.finditer(normalized):
            nodes.add(match.group(1))
            nodes.add(match.group(2))
        for match in SHAPE_NODE_RE.finditer(normalized):
            nodes.add(match.group(2))

    return len(nodes), edges


def classify_status(nodes: int | None) -> str:
    if nodes is None:
        return "UNKNOWN"
    if nodes >= 35:
        return "CRITICAL"
    if nodes >= 20:
        return "OVERLOADED"
    return "OK"


def iter_diagram_files(docs_root: Path) -> list[Path]:
    return sorted(
        path
        for path in docs_root.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTS
    )


def build_inventory_row(path: Path, use_git: bool) -> InventoryRow:
    suffix = path.suffix.lower()
    file_format = suffix.lstrip(".")
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

    if suffix in {".mmd", ".mermaid"}:
        content = read_text(path)
        diag_type = detect_mermaid_type(content)
        if diag_type == "flowchart":
            nodes_count, edges_count = count_flowchart_nodes_edges(content)
        has_init = "true" if INIT_RE.search(content) else "false"
        has_view_meta = "true" if VIEW_RE.search(content) else "false"
        parent_match = PARENT_RE.search(content)
        parent = parent_match.group(1) if parent_match else ""

    return InventoryRow(
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


def write_csv(rows: list[InventoryRow], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [field.name for field in InventoryRow.__dataclass_fields__.values()]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def write_markdown(rows: list[InventoryRow], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    headers = [field.name for field in InventoryRow.__dataclass_fields__.values()]
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


def main() -> int:
    args = parse_args()
    docs_root = Path(args.docs)
    rows = [
        build_inventory_row(path, use_git=args.use_git)
        for path in iter_diagram_files(docs_root)
    ]

    write_csv(rows, Path(args.out_csv))
    write_markdown(rows, Path(args.out_md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
