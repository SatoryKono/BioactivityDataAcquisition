"""Build deterministic RAG manifests for project markdown knowledge sources."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from memory.rag.chunking import (
    build_chunk_id,
    content_hash,
    infer_domain,
    infer_source_type,
    split_markdown_sections,
)
from memory.rag.filters import iter_markdown_sources
from memory.resources import MEMORY_ROOT

DEFAULT_OUTPUT_DIR = MEMORY_ROOT / "rag" / "manifests"
GENERATOR_VERSION = 1


def build_rag_manifests(root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Build deterministic corpus catalog and chunk records for markdown sources."""
    sources = iter_markdown_sources(root)
    corpus_sources: list[dict[str, Any]] = []
    chunk_records: list[dict[str, Any]] = []

    for path in sources:
        rel_path = path.relative_to(root)
        rel_path_str = rel_path.as_posix()
        text = path.read_text(encoding="utf-8")
        sections = split_markdown_sections(text)
        source_type = infer_source_type(rel_path)
        domain = infer_domain(rel_path)
        corpus_sources.append(
            {
                "source_path": rel_path_str,
                "source_type": source_type,
                "domain": domain,
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
                    "title": section.title,
                    "heading_level": section.level,
                    "content": section.content,
                    "content_hash": content_hash(section.content),
                    "graph_node_refs": [],
                    "owner": "BioETL Team",
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
        description="Build deterministic RAG manifests for markdown project knowledge."
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
