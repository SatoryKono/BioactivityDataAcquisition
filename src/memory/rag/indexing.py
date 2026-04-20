"""Build deterministic RAG manifests for project knowledge sources."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from memory.graph.refs import graph_refs_for_source, related_refs_for_source
from memory.rag.chunking import (
    build_chunk_id,
    chunk_source,
    content_hash,
    infer_domain,
    infer_source_type,
)
from memory.rag.filters import iter_rag_sources
from memory.resources import CATALOG_DIR, MEMORY_ROOT, load_yaml_resource

DEFAULT_OUTPUT_DIR = MEMORY_ROOT / "rag" / "manifests"
GENERATOR_VERSION = 1


def _load_owner_specs() -> list[tuple[str, tuple[str, ...]]]:
    payload = load_yaml_resource(CATALOG_DIR / "owner_map.yaml")
    specs: list[tuple[str, tuple[str, ...]]] = []
    for entry in payload.get("owners", []):
        if not isinstance(entry, dict):
            continue
        owner = entry.get("owner")
        paths = entry.get("paths", [])
        if not isinstance(owner, str):
            continue
        normalized_paths = tuple(str(path).rstrip("/") for path in paths if isinstance(path, str))
        specs.append((owner, normalized_paths))
    return specs


def _load_repo_zone_specs() -> list[tuple[str, tuple[str, ...]]]:
    payload = load_yaml_resource(CATALOG_DIR / "repo_zones.yaml")
    specs: list[tuple[str, tuple[str, ...]]] = []
    for entry in payload.get("zones", []):
        if not isinstance(entry, dict):
            continue
        zone_id = entry.get("id")
        paths = entry.get("paths", [])
        if not isinstance(zone_id, str):
            continue
        normalized_paths = tuple(str(path).rstrip("/") for path in paths if isinstance(path, str))
        specs.append((zone_id, normalized_paths))
    return specs


def _lookup_owner(rel_path: str, owner_specs: list[tuple[str, tuple[str, ...]]]) -> str:
    for owner, prefixes in owner_specs:
        if any(rel_path.startswith(f"{prefix}/") or rel_path == prefix for prefix in prefixes):
            return owner
    return "BioETL Team"


def _lookup_repo_zone(rel_path: str, zone_specs: list[tuple[str, tuple[str, ...]]]) -> str:
    for zone_id, prefixes in zone_specs:
        if any(rel_path.startswith(f"{prefix}/") or rel_path == prefix for prefix in prefixes):
            return zone_id
    return "unclassified"


def build_rag_manifests(root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Build deterministic corpus catalog and chunk records for project sources."""
    sources = iter_rag_sources(root)
    owner_specs = _load_owner_specs()
    zone_specs = _load_repo_zone_specs()
    corpus_sources: list[dict[str, Any]] = []
    chunk_records: list[dict[str, Any]] = []

    for path in sources:
        rel_path = path.relative_to(root)
        rel_path_str = rel_path.as_posix()
        text = path.read_text(encoding="utf-8")
        sections = chunk_source(rel_path, text)
        source_type = infer_source_type(rel_path)
        domain = infer_domain(rel_path)
        owner = _lookup_owner(rel_path_str, owner_specs)
        repo_zone = _lookup_repo_zone(rel_path_str, zone_specs)
        corpus_sources.append(
            {
                "source_path": rel_path_str,
                "source_type": source_type,
                "domain": domain,
                "repo_zone": repo_zone,
                "owner": owner,
                "content_hash": content_hash(text),
                "section_count": len(sections),
            }
        )
        for section in sections:
            chunk_records.append(
                {
                    "id": build_chunk_id(rel_path_str, section.title, section.index),
                    "source_path": rel_path_str,
                    "source_type": source_type,
                    "domain": domain,
                    "repo_zone": repo_zone,
                    "title": section.title,
                    "heading_level": section.level,
                    "symbol": section.title if section.symbol_kind not in {None, "markdown_section", "config_document"} else None,
                    "symbol_kind": section.symbol_kind,
                    "content": section.content,
                    "content_hash": content_hash(section.content),
                    "graph_node_refs": graph_refs_for_source(
                        rel_path_str,
                        source_type,
                        symbol_kind=section.symbol_kind,
                        symbol_name=section.title if section.symbol_kind in {"class", "function", "async_function"} else None,
                    ),
                    "related_refs": related_refs_for_source(
                        rel_path_str,
                        source_type,
                        symbol_kind=section.symbol_kind,
                        symbol_name=section.title if section.symbol_kind in {"class", "function", "async_function"} else None,
                    ),
                    "owner": owner,
                    "freshness_class": "warm",
                }
            )

    catalog = {
        "generator_version": GENERATOR_VERSION,
        "source_count": len(corpus_sources),
        "chunk_count": len(chunk_records),
        "sources": corpus_sources,
    }
    return catalog, chunk_records


def write_rag_manifests(root: Path, output_dir: Path) -> tuple[Path, Path]:
    """Write deterministic corpus catalog and chunk manifests."""
    output_dir.mkdir(parents=True, exist_ok=True)
    catalog, chunks = build_rag_manifests(root)
    catalog_path = output_dir / "corpus_catalog.json"
    chunks_path = output_dir / "chunks.jsonl"
    catalog_path.write_text(json.dumps(catalog, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with chunks_path.open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(json.dumps(chunk, sort_keys=True, ensure_ascii=True))
            handle.write("\n")
    return catalog_path, chunks_path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build deterministic RAG manifests for project knowledge."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[3],
        help="Repository root to index.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory for generated manifests.",
    )
    parser.add_argument(
        "--print-summary",
        action="store_true",
        help="Print a short build summary after generation.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    catalog_path, chunks_path = write_rag_manifests(args.root.resolve(), args.output_dir)
    if args.print_summary:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        print(
            f"Generated RAG manifests: {catalog_path} and {chunks_path} "
            f"(sources={catalog['source_count']}, chunks={catalog['chunk_count']})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
