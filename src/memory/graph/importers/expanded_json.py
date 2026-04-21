"""Import high-signal relations from ``bioetl_knowledge_graph_expanded.json``."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from memory.resources import MEMORY_ROOT

GENERATOR_VERSION = 1
DEFAULT_PROJECTION_DIR = MEMORY_ROOT / "graph" / "projections"
DEFAULT_INDEX_DIR = MEMORY_ROOT / "graph" / "indexes"


def default_expanded_graph_path(root: Path) -> Path:
    """Return the conventional expanded graph snapshot input path."""
    return root / "src" / "bioetl_knowledge_graph_expanded.json"


def load_expanded_graph(path: Path) -> dict[str, Any]:
    """Load an expanded graph snapshot and validate its coarse shape."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("expanded graph snapshot must be a JSON object")
    if not isinstance(payload.get("nodes"), dict) or not isinstance(
        payload.get("edges"), dict
    ):
        raise ValueError("expanded graph snapshot must contain object nodes and edges")
    return payload


def iter_file_reference_records(
    payload: dict[str, Any],
    *,
    source_snapshot: str,
) -> list[dict[str, Any]]:
    """Return normalized ``file -> references_file -> file`` relation records."""
    nodes: dict[str, dict[str, Any]] = payload["nodes"]
    edges: dict[str, dict[str, Any]] = payload["edges"]
    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    snapshot_generated_at = str(meta.get("generated_at") or "unknown")
    records: list[dict[str, Any]] = []

    for edge_id, edge in edges.items():
        if edge.get("edge_type") != "references_file":
            continue
        source_node = nodes.get(str(edge.get("source"))) or {}
        target_node = nodes.get(str(edge.get("target"))) or {}
        source_path = _node_source_path(source_node)
        target_path = _node_source_path(target_node)
        if not source_path or not target_path:
            continue
        records.append(
            {
                "id": f"{source_path}|references_file|{target_path}",
                "source_id": str(edge.get("source") or ""),
                "source_path": source_path,
                "target_id": str(edge.get("target") or ""),
                "target_path": target_path,
                "relation": "references_file",
                "confidence": "derived",
                "provenance": "bioetl_knowledge_graph_expanded.references_file",
                "source_snapshot": source_snapshot,
                "source_generated_at": snapshot_generated_at,
                "edge_id": str(edge_id),
                "description": str(edge.get("description") or ""),
                "evidence": edge.get("meta")
                if isinstance(edge.get("meta"), dict)
                else {},
            }
        )
    records.sort(key=lambda item: (item["source_path"], item["target_path"]))
    return records


def iter_module_reference_records(
    payload: dict[str, Any],
    *,
    source_snapshot: str,
) -> list[dict[str, Any]]:
    """Return normalized ``module -> references -> module`` relation records."""
    nodes: dict[str, dict[str, Any]] = payload["nodes"]
    edges: dict[str, dict[str, Any]] = payload["edges"]
    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    snapshot_generated_at = str(meta.get("generated_at") or "unknown")
    records: list[dict[str, Any]] = []

    for edge_id, edge in edges.items():
        if edge.get("edge_type") != "references":
            continue
        source_id = str(edge.get("source") or "")
        target_id = str(edge.get("target") or "")
        source_node = nodes.get(source_id) or {}
        target_node = nodes.get(target_id) or {}
        if (
            source_node.get("node_type") != "Module"
            or target_node.get("node_type") != "Module"
        ):
            continue
        source_name = _node_module_name(source_node, source_id)
        target_name = _node_module_name(target_node, target_id)
        if not source_name or not target_name:
            continue
        records.append(
            {
                "id": f"{source_name}|references|{target_name}",
                "source_id": source_id,
                "source_name": source_name,
                "source_path": _node_source_path(source_node),
                "target_id": target_id,
                "target_name": target_name,
                "target_path": _node_source_path(target_node),
                "relation": "references",
                "confidence": "derived",
                "provenance": "bioetl_knowledge_graph_expanded.references",
                "source_snapshot": source_snapshot,
                "source_generated_at": snapshot_generated_at,
                "edge_id": str(edge_id),
                "description": str(edge.get("description") or ""),
                "evidence": edge.get("meta")
                if isinstance(edge.get("meta"), dict)
                else {},
            }
        )
    records.sort(key=lambda item: (item["source_name"], item["target_name"]))
    return records


def _node_source_path(node: dict[str, Any]) -> str:
    source_path = node.get("source_path")
    if isinstance(source_path, str) and source_path:
        return source_path.replace("\\", "/")
    return ""


def _node_module_name(node: dict[str, Any], node_id: str) -> str:
    raw_id = str(node.get("id") or node_id)
    if raw_id.startswith("mod:"):
        return raw_id.removeprefix("mod:")
    label = node.get("label")
    return str(label) if isinstance(label, str) else ""


def build_file_relation_index(
    records: list[dict[str, Any]],
    *,
    source_snapshot: str,
) -> dict[str, Any]:
    """Build a compact lookup index for file-level relation queries."""
    by_file: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: {"outbound": [], "inbound": []}
    )
    for record in records:
        outbound = _compact_relation(record, "outbound")
        inbound = _compact_relation(record, "inbound")
        by_file[record["source_path"]]["outbound"].append(outbound)
        by_file[record["target_path"]]["inbound"].append(inbound)

    normalized_by_file = {
        path: {
            "outbound": sorted(
                relations["outbound"], key=lambda item: item["target_path"]
            ),
            "inbound": sorted(
                relations["inbound"], key=lambda item: item["source_path"]
            ),
        }
        for path, relations in sorted(by_file.items())
    }
    return {
        "generator_version": GENERATOR_VERSION,
        "kind": "file_relation_index",
        "relation": "references_file",
        "source_snapshot": source_snapshot,
        "relation_count": len(records),
        "file_count": len(normalized_by_file),
        "by_file": normalized_by_file,
    }


def build_module_relation_index(
    records: list[dict[str, Any]],
    *,
    source_snapshot: str,
) -> dict[str, Any]:
    """Build a compact lookup index for module-level relation queries."""
    by_module: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: {"outbound": [], "inbound": []}
    )
    for record in records:
        outbound = _compact_module_relation(record, "outbound")
        inbound = _compact_module_relation(record, "inbound")
        by_module[record["source_name"]]["outbound"].append(outbound)
        by_module[record["target_name"]]["inbound"].append(inbound)

    normalized_by_module = {
        module_name: {
            "outbound": sorted(
                relations["outbound"], key=lambda item: item["target_name"]
            ),
            "inbound": sorted(
                relations["inbound"], key=lambda item: item["source_name"]
            ),
        }
        for module_name, relations in sorted(by_module.items())
    }
    return {
        "generator_version": GENERATOR_VERSION,
        "kind": "module_relation_index",
        "relation": "references",
        "source_snapshot": source_snapshot,
        "relation_count": len(records),
        "module_count": len(normalized_by_module),
        "by_module": normalized_by_module,
    }


def _compact_relation(record: dict[str, Any], direction: str) -> dict[str, Any]:
    return {
        "id": record["id"],
        "direction": direction,
        "relation": record["relation"],
        "source_path": record["source_path"],
        "target_path": record["target_path"],
        "confidence": record["confidence"],
        "provenance": record["provenance"],
        "source_generated_at": record["source_generated_at"],
        "evidence": record.get("evidence") or {},
    }


def _compact_module_relation(record: dict[str, Any], direction: str) -> dict[str, Any]:
    return {
        "id": record["id"],
        "direction": direction,
        "relation": record["relation"],
        "source_name": record["source_name"],
        "source_path": record["source_path"],
        "target_name": record["target_name"],
        "target_path": record["target_path"],
        "confidence": record["confidence"],
        "provenance": record["provenance"],
        "source_generated_at": record["source_generated_at"],
        "evidence": record.get("evidence") or {},
    }


def write_expanded_graph_relation_artifacts(
    snapshot_path: Path,
    output_root: Path,
) -> tuple[Path, Path, dict[str, Any]]:
    """Write file-reference projection JSONL and lookup index JSON."""
    payload = load_expanded_graph(snapshot_path)
    projection_dir = output_root / "graph" / "projections"
    index_dir = output_root / "graph" / "indexes"
    projection_dir.mkdir(parents=True, exist_ok=True)
    index_dir.mkdir(parents=True, exist_ok=True)

    records = iter_file_reference_records(
        payload,
        source_snapshot=str(snapshot_path),
    )
    module_records = iter_module_reference_records(
        payload,
        source_snapshot=str(snapshot_path),
    )
    projection_path = projection_dir / "file_references.jsonl"
    index_path = index_dir / "file_relations.json"
    module_projection_path = projection_dir / "module_references.jsonl"
    module_index_path = index_dir / "module_relations.json"
    _write_jsonl(projection_path, records)
    _write_jsonl(module_projection_path, module_records)
    index = build_file_relation_index(records, source_snapshot=str(snapshot_path))
    module_index = build_module_relation_index(
        module_records,
        source_snapshot=str(snapshot_path),
    )
    index_path.write_text(
        json.dumps(index, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    module_index_path.write_text(
        json.dumps(module_index, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    summary = {
        "ok": True,
        "kind": "graph_relations",
        "source_snapshot": str(snapshot_path),
        "projection_path": str(projection_path),
        "index_path": str(index_path),
        "module_projection_path": str(module_projection_path),
        "module_index_path": str(module_index_path),
        "paths": [
            str(projection_path),
            str(index_path),
            str(module_projection_path),
            str(module_index_path),
        ],
        "relation_count": len(records),
        "file_count": index["file_count"],
        "module_relation_count": len(module_records),
        "module_count": module_index["module_count"],
    }
    return projection_path, index_path, summary


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=True))
            handle.write("\n")


def load_file_relation_index(path: Path) -> dict[str, Any]:
    """Load a generated file relation lookup index."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("kind") != "file_relation_index":
        raise ValueError(f"invalid file relation index: {path}")
    return payload


def load_module_relation_index(path: Path) -> dict[str, Any]:
    """Load a generated module relation lookup index."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("kind") != "module_relation_index":
        raise ValueError(f"invalid module relation index: {path}")
    return payload


def query_file_relations(
    index: dict[str, Any],
    source_path: str,
    *,
    direction: str = "both",
    limit: int = 20,
) -> dict[str, Any]:
    """Return direct inbound/outbound file relation records for one file."""
    resolved_path = resolve_index_file_path(index, source_path)
    if resolved_path is None:
        return _empty_relation_payload(index, source_path)
    entry = index["by_file"][resolved_path]
    outbound = entry.get("outbound", []) if direction in {"both", "outbound"} else []
    inbound = entry.get("inbound", []) if direction in {"both", "inbound"} else []
    return {
        "kind": "file_refs",
        "query": source_path,
        "resolved_path": resolved_path,
        "relation": index.get("relation"),
        "source_snapshot": index.get("source_snapshot"),
        "outbound": list(outbound)[:limit],
        "inbound": list(inbound)[:limit],
        "count": min(len(outbound), limit) + min(len(inbound), limit),
        "ok": True,
    }


def query_module_relations(
    index: dict[str, Any],
    module_name: str,
    *,
    direction: str = "both",
    limit: int = 20,
) -> dict[str, Any]:
    """Return direct inbound/outbound module relation records for one module."""
    resolved_name = resolve_index_module_name(index, module_name)
    if resolved_name is None:
        return _empty_module_relation_payload(index, module_name)
    entry = index["by_module"][resolved_name]
    outbound = entry.get("outbound", []) if direction in {"both", "outbound"} else []
    inbound = entry.get("inbound", []) if direction in {"both", "inbound"} else []
    return {
        "kind": "module_refs",
        "query": module_name,
        "resolved_module": resolved_name,
        "relation": index.get("relation"),
        "source_snapshot": index.get("source_snapshot"),
        "outbound": list(outbound)[:limit],
        "inbound": list(inbound)[:limit],
        "count": min(len(outbound), limit) + min(len(inbound), limit),
        "ok": True,
    }


def _empty_relation_payload(index: dict[str, Any], source_path: str) -> dict[str, Any]:
    return {
        "kind": "file_refs",
        "query": source_path,
        "resolved_path": None,
        "relation": index.get("relation"),
        "source_snapshot": index.get("source_snapshot"),
        "outbound": [],
        "inbound": [],
        "count": 0,
        "ok": True,
    }


def _empty_module_relation_payload(
    index: dict[str, Any], module_name: str
) -> dict[str, Any]:
    return {
        "kind": "module_refs",
        "query": module_name,
        "resolved_module": None,
        "relation": index.get("relation"),
        "source_snapshot": index.get("source_snapshot"),
        "outbound": [],
        "inbound": [],
        "count": 0,
        "ok": True,
    }


def query_file_neighborhood(
    index: dict[str, Any],
    source_path: str,
    *,
    depth: int = 1,
    limit: int = 50,
) -> dict[str, Any]:
    """Return a bounded BFS neighborhood over file-reference relations."""
    resolved_path = resolve_index_file_path(index, source_path)
    if resolved_path is None:
        return {
            "kind": "file_neighborhood",
            "query": source_path,
            "resolved_path": None,
            "depth": depth,
            "nodes": [],
            "edges": [],
            "count": 0,
            "ok": True,
        }
    by_file = index["by_file"]
    visited = {resolved_path}
    seen_edge_ids: set[str] = set()
    queue: deque[tuple[str, int]] = deque([(resolved_path, 0)])
    edges: list[dict[str, Any]] = []

    while queue and len(edges) < limit:
        current, current_depth = queue.popleft()
        if current_depth >= depth:
            continue
        for relation in _relations_for_entry(by_file.get(current, {})):
            relation_id = str(relation.get("id") or "")
            if relation_id in seen_edge_ids:
                continue
            seen_edge_ids.add(relation_id)
            edges.append(relation)
            neighbor = (
                relation["target_path"]
                if relation["source_path"] == current
                else relation["source_path"]
            )
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, current_depth + 1))
            if len(edges) >= limit:
                break

    return {
        "kind": "file_neighborhood",
        "query": source_path,
        "resolved_path": resolved_path,
        "depth": depth,
        "source_snapshot": index.get("source_snapshot"),
        "nodes": sorted(visited),
        "edges": edges,
        "count": len(edges),
        "ok": True,
    }


def query_module_neighborhood(
    index: dict[str, Any],
    module_name: str,
    *,
    depth: int = 1,
    limit: int = 50,
) -> dict[str, Any]:
    """Return a bounded BFS neighborhood over module-reference relations."""
    resolved_name = resolve_index_module_name(index, module_name)
    if resolved_name is None:
        return {
            "kind": "module_neighborhood",
            "query": module_name,
            "resolved_module": None,
            "depth": depth,
            "nodes": [],
            "edges": [],
            "count": 0,
            "ok": True,
        }
    by_module = index["by_module"]
    visited = {resolved_name}
    seen_edge_ids: set[str] = set()
    queue: deque[tuple[str, int]] = deque([(resolved_name, 0)])
    edges: list[dict[str, Any]] = []

    while queue and len(edges) < limit:
        current, current_depth = queue.popleft()
        if current_depth >= depth:
            continue
        for relation in _module_relations_for_entry(by_module.get(current, {})):
            relation_id = str(relation.get("id") or "")
            if relation_id in seen_edge_ids:
                continue
            seen_edge_ids.add(relation_id)
            edges.append(relation)
            neighbor = (
                relation["target_name"]
                if relation["source_name"] == current
                else relation["source_name"]
            )
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, current_depth + 1))
            if len(edges) >= limit:
                break

    return {
        "kind": "module_neighborhood",
        "query": module_name,
        "resolved_module": resolved_name,
        "depth": depth,
        "source_snapshot": index.get("source_snapshot"),
        "nodes": sorted(visited),
        "edges": edges,
        "count": len(edges),
        "ok": True,
    }


def _relations_for_entry(entry: dict[str, Any]) -> list[dict[str, Any]]:
    relations = [*entry.get("outbound", []), *entry.get("inbound", [])]
    return sorted(
        relations,
        key=lambda item: (
            item.get("source_path", ""),
            item.get("target_path", ""),
            item.get("direction", ""),
        ),
    )


def _module_relations_for_entry(entry: dict[str, Any]) -> list[dict[str, Any]]:
    relations = [*entry.get("outbound", []), *entry.get("inbound", [])]
    return sorted(
        relations,
        key=lambda item: (
            item.get("source_name", ""),
            item.get("target_name", ""),
            item.get("direction", ""),
        ),
    )


def resolve_index_file_path(index: dict[str, Any], query: str) -> str | None:
    """Resolve exact, normalized, or unique suffix file query to index path."""
    normalized_query = query.replace("\\", "/").lstrip("./")
    by_file = index.get("by_file", {})
    if normalized_query in by_file:
        return normalized_query
    suffix_matches = [
        path
        for path in by_file
        if path.endswith(f"/{normalized_query}") or path.endswith(normalized_query)
    ]
    if len(suffix_matches) == 1:
        return suffix_matches[0]
    return None


def resolve_index_module_name(index: dict[str, Any], query: str) -> str | None:
    """Resolve exact or unique suffix module query to index module name."""
    normalized_query = query.removeprefix("mod:")
    by_module = index.get("by_module", {})
    if normalized_query in by_module:
        return normalized_query
    suffix_matches = [
        module_name
        for module_name in by_module
        if module_name.endswith(f".{normalized_query}")
        or module_name.endswith(normalized_query)
    ]
    if len(suffix_matches) == 1:
        return suffix_matches[0]
    return None


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import file/module relations from an expanded BioETL graph JSON."
    )
    parser.add_argument(
        "--snapshot-path",
        type=Path,
        required=True,
        help="Path to bioetl_knowledge_graph_expanded.json.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=MEMORY_ROOT,
        help="Memory root or temporary output root for generated relation artifacts.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON summary.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    _, _, summary = write_expanded_graph_relation_artifacts(
        args.snapshot_path.resolve(),
        args.output_root.resolve(),
    )
    if args.json:
        sys.stdout.write(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    else:
        sys.stdout.write(
            "Imported graph relation artifacts: "
            f"{summary['relation_count']} file relations across "
            f"{summary['file_count']} files; "
            f"{summary['module_relation_count']} module relations across "
            f"{summary['module_count']} modules"
            "\n"
        )
        sys.stdout.write(f"- file projection: {summary['projection_path']}\n")
        sys.stdout.write(f"- file index: {summary['index_path']}\n")
        sys.stdout.write(f"- module projection: {summary['module_projection_path']}\n")
        sys.stdout.write(f"- module index: {summary['module_index_path']}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
