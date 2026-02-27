#!/usr/bin/env python3
"""Inventory and lightweight policy audit for docs diagrams."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
import subprocess
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path

SUPPORTED_EXTS: set[str] = {".mermaid", ".mmd", ".puml", ".d2", ".svg", ".png"}
INIT_RE = re.compile(r"%%\{\s*(init|initialize)\s*:", re.IGNORECASE)
VIEW_RE = re.compile(r"(?m)^\s*%%\s*View\s*:")
PARENT_RE = re.compile(r"(?i)\bParent\s*:\s*([^\s|]+)")
FLOW_EDGE_RE = re.compile(r"(<-->|-->|<--|-.->|---|==>|<==)")


@dataclass(frozen=True)
class Row:
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


def run(cmd: list[str]) -> tuple[int, str]:
    process = subprocess.run(
        cmd,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return process.returncode, (process.stdout or "").strip()


def git_last_modified(path: Path) -> str | None:
    rc, out = run(["git", "log", "-1", "--format=%cI %h", "--", str(path)])
    if rc == 0 and out:
        return out
    return None


def mtime_iso(path: Path) -> str:
    return dt.datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")


def read_text(path: Path, limit: int = 400_000) -> str:
    return path.read_bytes()[:limit].decode("utf-8", errors="replace")


def detect_mermaid_type(text: str) -> str:
    lines = [
        ln.strip()
        for ln in text.splitlines()
        if ln.strip() and not ln.strip().startswith("%%")
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


def count_flowchart(text: str) -> tuple[int, int]:
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
            r"([A-Za-z0-9_.-]+)\s*(?:<-->|-->|<--|-.->|---|==>|<==)\s*([A-Za-z0-9_.-]+)",
            normalized,
        ):
            nodes.add(match.group(1))
            nodes.add(match.group(2))
        for match in re.finditer(r"(^|\s)([A-Za-z0-9_.-]+)\s*[\[\(\{]", normalized):
            nodes.add(match.group(2))
    return len(nodes), edges


def get_status(nodes: int | None) -> str:
    if nodes is None:
        return "UNKNOWN"
    if nodes >= 35:
        return "CRITICAL"
    if nodes >= 20:
        return "OVERLOADED"
    return "OK"


def iter_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTS:
            yield path


def write_csv(rows: list[Row], out_path: Path) -> None:
    fieldnames = list(Row.__dataclass_fields__.keys())
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def write_markdown(rows: list[Row], out_path: Path) -> None:
    headers = list(Row.__dataclass_fields__.keys())
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join(["---"] * len(headers)) + "|",
    ]
    for row in rows:
        values = [getattr(row, key) for key in headers]
        lines.append("| " + " | ".join(values) + " |")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--docs", default="docs")
    parser.add_argument("--out-csv", required=True)
    parser.add_argument("--out-md", required=True)
    parser.add_argument("--use-git", action="store_true")
    args = parser.parse_args()

    docs_root = Path(args.docs)
    rows: list[Row] = []

    for path in sorted(iter_files(docs_root)):
        ext = path.suffix.lower()
        fmt = ext.lstrip(".")
        last_modified = git_last_modified(path) if args.use_git else None
        last_value = last_modified if last_modified is not None else mtime_iso(path)
        size_kb = f"{(path.stat().st_size / 1024.0):.1f}"

        diag_type = "other"
        nodes: int | None = None
        edges: int | None = None
        has_init = "false"
        has_view_meta = "false"
        parent = ""

        if ext in {".mmd", ".mermaid"}:
            text = read_text(path)
            diag_type = detect_mermaid_type(text)
            if diag_type == "flowchart":
                nodes, edges = count_flowchart(text)
            has_init = "true" if INIT_RE.search(text) else "false"
            has_view_meta = "true" if VIEW_RE.search(text) else "false"
            parent_match = PARENT_RE.search(text)
            parent = parent_match.group(1) if parent_match else ""

        rows.append(
            Row(
                path=str(path),
                name=path.name,
                diag_type=diag_type,
                format=fmt,
                nodes_count=str(nodes) if nodes is not None else "NA",
                edges_count=str(edges) if edges is not None else "NA",
                size_kb=size_kb,
                last_modified=last_value,
                status=get_status(nodes),
                has_init=has_init,
                has_view_meta=has_view_meta,
                parent=parent,
            )
        )

    write_csv(rows, Path(args.out_csv))
    write_markdown(rows, Path(args.out_md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
