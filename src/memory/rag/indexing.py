"""Build deterministic RAG manifests for project knowledge sources."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
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
from memory.rag.devin_wiki import build_devin_wiki_records
from memory.rag.filters import (
    DEFAULT_SELECTED_SOURCE_IDS,
    WORKFLOW_RAG_MAX_SOURCES,
    WORKFLOW_RAG_SOURCE_IDS,
    iter_rag_sources,
)
from memory.rag.validation import (
    capture_rag_source_identity,
    require_valid_rag_manifest,
    validate_rag_manifest_files,
    validate_rag_manifest_payload,
)
from memory.resources import CATALOG_DIR, MEMORY_ROOT, load_yaml_resource

DEFAULT_OUTPUT_DIR = MEMORY_ROOT / "derived" / "rag" / "manifests"
GENERATOR_VERSION = 2
DEFAULT_BUILD_SCOPE = "full"
WORKFLOW_BUILD_SCOPE = "workflow"


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
        normalized_paths = tuple(
            str(path).rstrip("/") for path in paths if isinstance(path, str)
        )
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
        normalized_paths = tuple(
            str(path).rstrip("/") for path in paths if isinstance(path, str)
        )
        specs.append((zone_id, normalized_paths))
    return specs


def _lookup_owner(rel_path: str, owner_specs: list[tuple[str, tuple[str, ...]]]) -> str:
    for owner, prefixes in owner_specs:
        if any(
            rel_path.startswith(f"{prefix}/") or rel_path == prefix
            for prefix in prefixes
        ):
            return owner
    return "BioETL Team"


def _lookup_repo_zone(
    rel_path: str, zone_specs: list[tuple[str, tuple[str, ...]]]
) -> str:
    for zone_id, prefixes in zone_specs:
        if any(
            rel_path.startswith(f"{prefix}/") or rel_path == prefix
            for prefix in prefixes
        ):
            return zone_id
    return "unclassified"


def _resolve_rag_sources(
    root: Path,
    *,
    build_scope: str,
    focus_query: str | None,
    max_sources: int | None,
) -> list[Path]:
    if build_scope == WORKFLOW_BUILD_SCOPE:
        source_limit = WORKFLOW_RAG_MAX_SOURCES if max_sources is None else max_sources
        return iter_rag_sources(
            root,
            selected_ids=WORKFLOW_RAG_SOURCE_IDS,
            workflow_focus_query=focus_query,
            max_sources=source_limit,
        )
    if build_scope != DEFAULT_BUILD_SCOPE:
        raise ValueError(f"unsupported RAG build scope: {build_scope}")
    if max_sources is not None:
        raise ValueError("full RAG builds cannot cap the eligible source set")
    return iter_rag_sources(
        root,
        selected_ids=DEFAULT_SELECTED_SOURCE_IDS,
        workflow_focus_query=None,
        max_sources=max_sources,
    )


def _section_symbol_name(section: Any) -> str | None:
    if section.symbol_kind in {"class", "function", "async_function"}:
        return section.title
    return None


def _section_symbol_display(section: Any) -> str | None:
    if section.symbol_kind not in {None, "markdown_section", "config_document"}:
        return section.title
    return None


def _build_section_chunk_record(
    *,
    rel_path_str: str,
    source_type: str,
    domain: str,
    owner: str | None,
    repo_zone: str | None,
    section: Any,
) -> dict[str, Any]:
    symbol_name = _section_symbol_name(section)
    return {
        "id": build_chunk_id(rel_path_str, section.title, section.index),
        "source_path": rel_path_str,
        "source_type": source_type,
        "domain": domain,
        "repo_zone": repo_zone,
        "title": section.title,
        "heading_level": section.level,
        "symbol": _section_symbol_display(section),
        "symbol_kind": section.symbol_kind,
        "content": section.content,
        "content_hash": content_hash(section.content),
        "graph_node_refs": graph_refs_for_source(
            rel_path_str,
            source_type,
            symbol_kind=section.symbol_kind,
            symbol_name=symbol_name,
        ),
        "related_refs": related_refs_for_source(
            rel_path_str,
            source_type,
            symbol_kind=section.symbol_kind,
            symbol_name=symbol_name,
        ),
        "owner": owner,
        "freshness_class": "warm",
    }


def _build_standard_source_records(
    root: Path,
    rel_path: Path,
    *,
    source_type: str,
    domain: str,
    owner: str | None,
    repo_zone: str | None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rel_path_str = rel_path.as_posix()
    source_path = root / rel_path
    if not source_path.is_file():
        raise FileNotFoundError(f"RAG source does not exist: {rel_path_str}")
    text = source_path.read_text(encoding="utf-8")
    sections = chunk_source(rel_path, text)
    corpus_source = {
        "source_path": rel_path_str,
        "source_type": source_type,
        "domain": domain,
        "repo_zone": repo_zone,
        "owner": owner,
        "content_hash": content_hash(text),
        "section_count": len(sections),
    }
    chunk_records = [
        _build_section_chunk_record(
            rel_path_str=rel_path_str,
            source_type=source_type,
            domain=domain,
            owner=owner,
            repo_zone=repo_zone,
            section=section,
        )
        for section in sections
    ]
    return corpus_source, chunk_records


def build_rag_manifests(
    root: Path,
    *,
    build_scope: str = DEFAULT_BUILD_SCOPE,
    focus_query: str | None = None,
    max_sources: int | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Build deterministic corpus catalog and chunk records for project sources."""
    sources = _resolve_rag_sources(
        root,
        build_scope=build_scope,
        focus_query=focus_query,
        max_sources=max_sources,
    )
    owner_specs = _load_owner_specs()
    zone_specs = _load_repo_zone_specs()
    corpus_sources: list[dict[str, Any]] = []
    chunk_records: list[dict[str, Any]] = []

    for rel_path in sources:
        rel_path_str = rel_path.as_posix()
        source_type = infer_source_type(rel_path)
        domain = infer_domain(rel_path)
        owner = _lookup_owner(rel_path_str, owner_specs)
        repo_zone = _lookup_repo_zone(rel_path_str, zone_specs)
        if source_type == "devin_wiki":
            corpus_source, chunk_rows = build_devin_wiki_records(
                root,
                rel_path,
                owner=owner,
                repo_zone=repo_zone,
            )
            corpus_sources.append(corpus_source)
            chunk_records.extend(chunk_rows)
            continue
        corpus_source, chunk_rows = _build_standard_source_records(
            root,
            rel_path,
            source_type=source_type,
            domain=domain,
            owner=owner,
            repo_zone=repo_zone,
        )
        corpus_sources.append(corpus_source)
        chunk_records.extend(chunk_rows)

    source_identity = capture_rag_source_identity(
        root,
        [source["source_path"] for source in corpus_sources],
    )
    catalog = {
        "generator_version": GENERATOR_VERSION,
        "build_scope": build_scope,
        "focus_query": focus_query,
        **source_identity,
        "source_count": len(corpus_sources),
        "chunk_count": len(chunk_records),
        "sources": corpus_sources,
    }
    require_valid_rag_manifest(
        validate_rag_manifest_payload(
            root,
            catalog,
            chunk_records,
            require_build_scope=build_scope,
            expected_source_paths=sources,
            verify_sources=False,  # Skip source verification during catalog update
        )
    )
    return catalog, chunk_records


def _serialize_catalog(catalog: dict[str, Any]) -> str:
    return json.dumps(catalog, indent=2, sort_keys=True) + "\n"


def _serialize_chunks(chunks: list[dict[str, Any]]) -> str:
    return "".join(
        f"{json.dumps(chunk, sort_keys=True, ensure_ascii=True)}\n" for chunk in chunks
    )


def _canonical_rag_output_dirs(root: Path) -> tuple[Path, Path]:
    memory_root = root.resolve() / "src" / "memory"
    return (
        memory_root / "derived" / "rag" / "manifests",
        memory_root / "rag" / "manifests",
    )


def _guard_workflow_output_scope(
    root: Path, output_dir: Path, build_scope: str
) -> None:
    if build_scope != WORKFLOW_BUILD_SCOPE:
        return
    resolved_output = output_dir.resolve()
    if resolved_output in _canonical_rag_output_dirs(root):
        raise ValueError(
            "workflow-scoped RAG manifests must use a temporary or external output "
            "directory, not an in-repository canonical RAG directory"
        )


def _publish_manifest_pair(
    staged_catalog: Path,
    staged_chunks: Path,
    output_dir: Path,
) -> tuple[Path, Path]:
    """Publish a validated pair transactionally and restore old files on failure."""
    from scripts.engineering.common.repo_paths import resolve_output_path

    # resolve_output_path keeps relative paths under the repo root while still
    # accepting absolute temporary/workflow destinations used by tests and
    # workflow-scoped builds.
    staged_catalog = resolve_output_path(staged_catalog)
    staged_chunks = resolve_output_path(staged_chunks)
    output_dir = resolve_output_path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    targets = (
        (staged_catalog, output_dir / "corpus_catalog.json"),
        (staged_chunks, output_dir / "chunks.jsonl"),
    )
    backup_dir = Path(tempfile.mkdtemp(prefix=".rag-backup-", dir=output_dir))
    backups: dict[Path, Path] = {}
    published: list[Path] = []
    try:
        for _, target in targets:
            if target.exists():
                backup = backup_dir / target.name
                os.replace(target, backup)  # noqa: PTH105 - policy requires os.replace
                backups[target] = backup
        for staged_path, target in targets:
            os.replace(staged_path, target)  # noqa: PTH105 - policy requires os.replace
            published.append(target)
    except Exception:
        for target in reversed(published):
            if target.exists():
                target.unlink()
        for target, backup in backups.items():
            if backup.exists():
                os.replace(backup, target)  # noqa: PTH105 - policy requires os.replace
        raise
    finally:
        shutil.rmtree(backup_dir, ignore_errors=True)
    return targets[0][1], targets[1][1]


def write_rag_manifests(
    root: Path,
    output_dir: Path,
    *,
    build_scope: str = DEFAULT_BUILD_SCOPE,
    focus_query: str | None = None,
    max_sources: int | None = None,
) -> tuple[Path, Path]:
    """Build, validate, and transactionally publish deterministic manifests."""
    _guard_workflow_output_scope(root, output_dir, build_scope)
    catalog, chunks = build_rag_manifests(
        root,
        build_scope=build_scope,
        focus_query=focus_query,
        max_sources=max_sources,
    )
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging_dir = Path(
        tempfile.mkdtemp(prefix=".rag-manifests-", dir=output_dir.parent)
    )
    try:
        staged_catalog = staging_dir / "corpus_catalog.json"
        staged_chunks = staging_dir / "chunks.jsonl"
        staged_catalog.write_text(_serialize_catalog(catalog), encoding="utf-8")
        staged_chunks.write_text(_serialize_chunks(chunks), encoding="utf-8")
        require_valid_rag_manifest(
            validate_rag_manifest_files(
                root,
                staged_catalog,
                staged_chunks,
                require_build_scope=build_scope,
                verify_sources=False,  # Skip source verification during catalog update
            )
        )
        return _publish_manifest_pair(staged_catalog, staged_chunks, output_dir)
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)


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
    parser.add_argument(
        "--build-scope",
        choices=(DEFAULT_BUILD_SCOPE, WORKFLOW_BUILD_SCOPE),
        default=DEFAULT_BUILD_SCOPE,
        help="Choose the deterministic source scope for the generated manifests.",
    )
    parser.add_argument(
        "--focus-query",
        type=str,
        default=None,
        help="Optional query text used to prioritize workflow-scope sources.",
    )
    parser.add_argument(
        "--max-sources",
        type=int,
        default=None,
        help="Optional deterministic cap on indexed source files.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    catalog_path, chunks_path = write_rag_manifests(
        args.root.resolve(),
        args.output_dir,
        build_scope=args.build_scope,
        focus_query=args.focus_query,
        max_sources=args.max_sources,
    )
    if args.print_summary:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        print(
            f"Generated RAG manifests: {catalog_path} and {chunks_path} "
            f"(sources={catalog['source_count']}, chunks={catalog['chunk_count']})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
