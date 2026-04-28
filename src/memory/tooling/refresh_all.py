"""Refresh deterministic project-memory artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from memory.graph import sync as graph_sync
from memory.graph.importers.expanded_json import (
    default_expanded_graph_path,
    write_expanded_graph_relation_artifacts,
)
from memory.rag.indexing import write_rag_manifests
from memory.resources import MEMORY_ROOT
from memory.timeline.ingest_ci import write_ci_events
from memory.timeline.ingest_incidents import write_incident_events
from memory.timeline.ingest_runs import write_run_events


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Refresh deterministic project-memory artifacts."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[3],
        help="Repository root to read canonical sources from.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=MEMORY_ROOT,
        help="Memory package root for generated artifacts.",
    )
    parser.add_argument(
        "--skip-rag",
        action="store_true",
        help="Skip RAG manifest generation.",
    )
    parser.add_argument(
        "--skip-timeline",
        action="store_true",
        help="Skip timeline projection generation.",
    )
    parser.add_argument(
        "--include-graph-export",
        action="store_true",
        help="Also export a deterministic graph snapshot under graph/exports/.",
    )
    parser.add_argument(
        "--include-graph-relations",
        action="store_true",
        help="Also import file-level relation projections from expanded graph JSON.",
    )
    parser.add_argument(
        "--expanded-graph-path",
        type=Path,
        default=None,
        help="Path to bioetl_knowledge_graph_expanded.json for relation imports.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the refresh summary as JSON.",
    )
    return parser


def refresh_all(
    root: Path,
    output_root: Path,
    *,
    include_rag: bool = True,
    include_timeline: bool = True,
    include_graph_export: bool = False,
    include_graph_relations: bool = False,
    expanded_graph_path: Path | None = None,
) -> dict[str, Any]:
    """Refresh supported memory artifacts and return a summary."""
    summary: dict[str, Any] = {"ok": True, "artifacts": []}

    if include_rag:
        rag_dir = output_root / "rag" / "manifests"
        catalog_path, chunks_path = write_rag_manifests(root, rag_dir)
        summary["artifacts"].append(
            {
                "kind": "rag",
                "paths": [str(catalog_path), str(chunks_path)],
            }
        )

    if include_timeline:
        timeline_dir = output_root / "timeline" / "events"
        run_path = write_run_events(root, timeline_dir / "runs.jsonl")
        ci_path = write_ci_events(root, timeline_dir / "ci.jsonl")
        incident_path = write_incident_events(root, timeline_dir / "incidents.jsonl")
        summary["artifacts"].append(
            {
                "kind": "timeline",
                "paths": [str(run_path), str(ci_path), str(incident_path)],
            }
        )

    if include_graph_export:
        graph_export = output_root / "graph" / "exports" / "repo_snapshot.json"
        exit_code = graph_sync.main(
            ["--root", str(root), "--export", str(graph_export)]
        )
        summary["artifacts"].append(
            {
                "kind": "graph",
                "paths": [str(graph_export)],
                "exit_code": exit_code,
            }
        )
        if exit_code != 0:
            summary["ok"] = False

    if include_graph_relations:
        snapshot_path = expanded_graph_path or default_expanded_graph_path(root)
        if not snapshot_path.exists():
            summary["ok"] = False
            summary["artifacts"].append(
                {
                    "kind": "graph_relations",
                    "paths": [],
                    "error": f"missing expanded graph snapshot: {snapshot_path}",
                }
            )
        else:
            _, _, relation_summary = write_expanded_graph_relation_artifacts(
                snapshot_path,
                output_root,
                repo_root=root,
            )
            summary["artifacts"].append(
                {
                    "kind": "graph_relations",
                    "paths": relation_summary["paths"],
                    "relation_count": relation_summary["relation_count"],
                    "file_count": relation_summary["file_count"],
                    "module_relation_count": relation_summary["module_relation_count"],
                    "module_count": relation_summary["module_count"],
                    "entity_relation_count": relation_summary["entity_relation_count"],
                    "entity_count": relation_summary["entity_count"],
                    "entity_relation_counts": relation_summary[
                        "entity_relation_counts"
                    ],
                    "source_snapshot": relation_summary["source_snapshot"],
                }
            )

    return summary


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    summary = refresh_all(
        args.root.resolve(),
        args.output_root.resolve(),
        include_rag=not args.skip_rag,
        include_timeline=not args.skip_timeline,
        include_graph_export=args.include_graph_export,
        include_graph_relations=args.include_graph_relations,
        expanded_graph_path=args.expanded_graph_path,
    )

    if args.json:
        pass
    else:
        "passed" if summary["ok"] else "failed"
        for _artifact in summary["artifacts"]:
            pass

    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
