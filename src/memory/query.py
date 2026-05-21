"""Unified query facade for local memory-layer retrieval and graph passthrough."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from memory.artifact_readiness import rag_chunks_ready, timeline_events_ready
from memory.graph import query as graph_query
from memory.graph.importers.expanded_json import (
    default_expanded_graph_path,
    load_entity_relation_index,
    load_file_relation_index,
    load_module_relation_index,
    write_expanded_graph_relation_artifacts,
)
from memory.graph.importers.expanded_json import (
    query_entity_neighborhood as _query_entity_neighborhood,
)
from memory.graph.importers.expanded_json import (
    query_entity_relations as _query_entity_relations,
)
from memory.graph.importers.expanded_json import (
    query_file_neighborhood as _query_file_neighborhood,
)
from memory.graph.importers.expanded_json import (
    query_file_relations as _query_file_relations,
)
from memory.graph.importers.expanded_json import (
    query_module_neighborhood as _query_module_neighborhood,
)
from memory.graph.importers.expanded_json import (
    query_module_relations as _query_module_relations,
)
from memory.rag.retrieval import TASK_PROFILES, load_chunk_manifest, rank_chunks
from memory.rag.filters import WORKFLOW_RAG_MAX_SOURCES
from memory.resources import (
    CATALOG_DIR,
    MEMORY_ROOT,
    POLICY_DIR,
    discover_memory_root,
    load_yaml_resource,
)
from memory.timeline._common import read_jsonl
from memory.tooling.refresh_all import refresh_all

LEGACY_RAG_CHUNKS = MEMORY_ROOT / "rag" / "manifests" / "chunks.jsonl"
DERIVED_RAG_CHUNKS = MEMORY_ROOT / "derived" / "rag" / "manifests" / "chunks.jsonl"
LEGACY_TIMELINE_DIR = MEMORY_ROOT / "timeline" / "events"
DERIVED_TIMELINE_DIR = MEMORY_ROOT / "derived" / "timeline" / "events"
DEFAULT_FILE_RELATION_INDEX = MEMORY_ROOT / "graph" / "indexes" / "file_relations.json"
DEFAULT_MODULE_RELATION_INDEX = (
    MEMORY_ROOT / "graph" / "indexes" / "module_relations.json"
)
DEFAULT_ENTITY_RELATION_INDEX = (
    MEMORY_ROOT / "graph" / "indexes" / "entity_relations.json"
)
DEFAULT_PROFILE = "general"
FILE_RELATION_INDEX_HELP = "Generated file relation index path."
MODULE_RELATION_INDEX_HELP = "Generated module relation index path."
ENTITY_RELATION_INDEX_HELP = "Generated entity relation index path."
MISSING_MANIFEST_HINT = (
    "Run `python -m memory.tooling.refresh_all` first or pass `--auto-refresh` "
    "to build temporary rebuild-only manifests for this query."
)

_CONFIDENCE_RANKS = {
    level["id"]: int(level["rank"])
    for level in load_yaml_resource(POLICY_DIR / "confidence.yaml").get("levels", [])
    if isinstance(level, dict) and isinstance(level.get("id"), str)
}
_TIMELINE_PROFILE_BONUS: dict[str, dict[str, int]] = {
    "general": {},
    "architecture": {"ci": 15, "run": 10, "incident": 5},
    "implementation": {"run": 25, "ci": 20, "incident": 5},
    "operations": {"incident": 40, "run": 30, "ci": 15},
    "audit": {"incident": 25, "run": 25, "ci": 25},
}


def _resolve_memory_root(memory_root: Path | None = None) -> Path:
    if memory_root is not None:
        return memory_root
    return discover_memory_root()


def default_rag_chunks_path(memory_root: Path | None = None) -> Path:
    """Prefer ready derived RAG artifacts, with legacy fallback for compatibility."""
    resolved_root = _resolve_memory_root(memory_root)
    derived_path = resolved_root / "derived" / "rag" / "manifests" / "chunks.jsonl"
    legacy_path = resolved_root / "rag" / "manifests" / "chunks.jsonl"
    if rag_chunks_ready(derived_path):
        return derived_path
    if rag_chunks_ready(legacy_path):
        return legacy_path
    if derived_path.parent.exists():
        return derived_path
    return legacy_path


def default_timeline_dir(memory_root: Path | None = None) -> Path:
    """Prefer ready derived timeline artifacts, with legacy fallback for compatibility."""
    resolved_root = _resolve_memory_root(memory_root)
    derived_dir = resolved_root / "derived" / "timeline" / "events"
    legacy_dir = resolved_root / "timeline" / "events"
    if timeline_events_ready(derived_dir):
        return derived_dir
    if timeline_events_ready(legacy_dir):
        return legacy_dir
    if derived_dir.exists() or derived_dir.parent.exists():
        return derived_dir
    return legacy_dir


DEFAULT_RAG_CHUNKS = default_rag_chunks_path()
DEFAULT_TIMELINE_DIR = default_timeline_dir()


@dataclass(frozen=True)
class RagQueryOptions:
    """Inputs for deterministic local RAG chunk retrieval."""

    query: str | None
    source_type: str | None = None
    domain: str | None = None
    repo_zone: str | None = None
    symbol_kind: str | None = None
    chunks_path: Path = field(default_factory=default_rag_chunks_path)
    limit: int = 20
    profile: str = DEFAULT_PROFILE
    auto_refresh: bool = False
    refresh_output_root: Path | None = None
    refresh_repo_root: Path | None = None
    file_context: str | None = None
    file_relation_index_path: Path = DEFAULT_FILE_RELATION_INDEX
    expanded_graph_path: Path | None = None
    file_context_depth: int = 1


def _load_catalog_view(view: str) -> Any:
    mapping = {
        "sources": CATALOG_DIR / "source_registry.yaml",
        "owners": CATALOG_DIR / "owner_map.yaml",
        "zones": CATALOG_DIR / "repo_zones.yaml",
        "placement": CATALOG_DIR / "placement_rules.yaml",
    }
    path = mapping[view]
    return load_yaml_resource(path)


def query_catalog(view: str) -> dict[str, Any]:
    """Return one structured catalog view."""
    payload = _load_catalog_view(view)
    return {"kind": "catalog", "view": view, "payload": payload}


def _catalog_hits_for_query(query: str) -> list[dict[str, Any]]:
    catalog_hits: list[dict[str, Any]] = []
    lowered_query = query.lower()
    for view in ("sources", "owners", "zones", "placement"):
        payload = query_catalog(view)
        haystack = json.dumps(
            payload["payload"], sort_keys=True, ensure_ascii=True
        ).lower()
        if lowered_query in haystack:
            catalog_hits.append(payload)
    return catalog_hits


def _missing_manifest_error(path: Path, artifact: str) -> FileNotFoundError:
    return FileNotFoundError(
        f"Missing {artifact} memory artifact at {path}. {MISSING_MANIFEST_HINT}"
    )


def _missing_graph_snapshot_error(path: Path) -> FileNotFoundError:
    return FileNotFoundError(
        f"Missing expanded graph snapshot at {path}. Pass `--expanded-graph-path` "
        "or provide a generated file relation index."
    )


def _resolve_refresh_output_root(output_root: Path | None) -> Path:
    return output_root or Path(tempfile.mkdtemp(prefix="memory-query-"))


def _refresh_query_artifacts(
    *,
    refresh_output_root: Path | None,
    refresh_repo_root: Path | None,
    include_rag: bool,
    include_timeline: bool,
    retrieval_query: str | None = None,
) -> tuple[Path, dict[str, Any]]:
    output_root = _resolve_refresh_output_root(refresh_output_root)
    repo_root = refresh_repo_root or Path(__file__).resolve().parents[2]
    report = refresh_all(
        repo_root.resolve(),
        output_root.resolve(),
        include_rag=include_rag,
        include_timeline=include_timeline,
        include_graph_export=False,
        rag_build_scope="workflow",
        rag_focus_query=retrieval_query,
        rag_max_sources=WORKFLOW_RAG_MAX_SOURCES,
        allow_partial=True,
    )
    return output_root, report


def _refresh_file_relation_index(
    *,
    refresh_output_root: Path | None,
    expanded_graph_path: Path | None,
    refresh_repo_root: Path | None,
) -> tuple[Path, Path, dict[str, Any]]:
    output_root = _resolve_refresh_output_root(refresh_output_root)
    repo_root = refresh_repo_root or Path(__file__).resolve().parents[2]
    snapshot_path = expanded_graph_path or default_expanded_graph_path(repo_root)
    if not snapshot_path.exists():
        raise _missing_graph_snapshot_error(snapshot_path)
    _, index_path, report = write_expanded_graph_relation_artifacts(
        snapshot_path.resolve(),
        output_root.resolve(),
    )
    return index_path, output_root, report


def _refresh_module_relation_index(
    *,
    refresh_output_root: Path | None,
    expanded_graph_path: Path | None,
    refresh_repo_root: Path | None,
) -> tuple[Path, Path, dict[str, Any]]:
    output_root = _resolve_refresh_output_root(refresh_output_root)
    repo_root = refresh_repo_root or Path(__file__).resolve().parents[2]
    snapshot_path = expanded_graph_path or default_expanded_graph_path(repo_root)
    if not snapshot_path.exists():
        raise _missing_graph_snapshot_error(snapshot_path)
    _, _, report = write_expanded_graph_relation_artifacts(
        snapshot_path.resolve(),
        output_root.resolve(),
    )
    return (
        output_root / "graph" / "indexes" / "module_relations.json",
        output_root,
        report,
    )


def _refresh_entity_relation_index(
    *,
    refresh_output_root: Path | None,
    expanded_graph_path: Path | None,
    refresh_repo_root: Path | None,
) -> tuple[Path, Path, dict[str, Any]]:
    output_root = _resolve_refresh_output_root(refresh_output_root)
    repo_root = refresh_repo_root or Path(__file__).resolve().parents[2]
    snapshot_path = expanded_graph_path or default_expanded_graph_path(repo_root)
    if not snapshot_path.exists():
        raise _missing_graph_snapshot_error(snapshot_path)
    _, _, report = write_expanded_graph_relation_artifacts(
        snapshot_path.resolve(),
        output_root.resolve(),
        repo_root=repo_root.resolve(),
    )
    return (
        output_root / "graph" / "indexes" / "entity_relations.json",
        output_root,
        report,
    )


def _resolve_file_relation_index(
    *,
    index_path: Path,
    auto_refresh: bool,
    refresh_output_root: Path | None,
    expanded_graph_path: Path | None,
    refresh_repo_root: Path | None,
) -> tuple[Path, Path | None, dict[str, Any] | None]:
    if index_path.exists():
        return index_path, None, None
    if not auto_refresh:
        raise _missing_manifest_error(index_path, "file relation index")
    return _refresh_file_relation_index(
        refresh_output_root=refresh_output_root,
        expanded_graph_path=expanded_graph_path,
        refresh_repo_root=refresh_repo_root,
    )


def _resolve_module_relation_index(
    *,
    index_path: Path,
    auto_refresh: bool,
    refresh_output_root: Path | None,
    expanded_graph_path: Path | None,
    refresh_repo_root: Path | None,
) -> tuple[Path, Path | None, dict[str, Any] | None]:
    if index_path.exists():
        return index_path, None, None
    if not auto_refresh:
        raise _missing_manifest_error(index_path, "module relation index")
    return _refresh_module_relation_index(
        refresh_output_root=refresh_output_root,
        expanded_graph_path=expanded_graph_path,
        refresh_repo_root=refresh_repo_root,
    )


def _resolve_entity_relation_index(
    *,
    index_path: Path,
    auto_refresh: bool,
    refresh_output_root: Path | None,
    expanded_graph_path: Path | None,
    refresh_repo_root: Path | None,
) -> tuple[Path, Path | None, dict[str, Any] | None]:
    if index_path.exists():
        return index_path, None, None
    if not auto_refresh:
        raise _missing_manifest_error(index_path, "entity relation index")
    return _refresh_entity_relation_index(
        refresh_output_root=refresh_output_root,
        expanded_graph_path=expanded_graph_path,
        refresh_repo_root=refresh_repo_root,
    )


def _resolve_query_paths(
    *,
    chunks_path: Path,
    events_dir: Path,
    auto_refresh: bool,
    refresh_output_root: Path | None,
    refresh_repo_root: Path | None,
    retrieval_query: str | None = None,
    require_chunks: bool = True,
    require_events: bool = True,
) -> tuple[Path, Path, Path | None, dict[str, Any] | None]:
    chunks_ready = rag_chunks_ready(chunks_path)
    events_ready = timeline_events_ready(events_dir)
    required_chunks_ready = not require_chunks or chunks_ready
    required_events_ready = not require_events or events_ready
    if required_chunks_ready and required_events_ready:
        return chunks_path, events_dir, None, None
    if not auto_refresh:
        if require_chunks and not chunks_ready:
            raise _missing_manifest_error(chunks_path, "RAG chunk manifest")
        raise _missing_manifest_error(events_dir, "timeline event projections")

    output_root, report = _refresh_query_artifacts(
        refresh_output_root=refresh_output_root,
        refresh_repo_root=refresh_repo_root,
        include_rag=require_chunks and not chunks_ready,
        include_timeline=require_events and not events_ready,
        retrieval_query=retrieval_query,
    )
    resolved_chunks_path = chunks_path
    if require_chunks and not chunks_ready:
        refreshed_chunks_path = output_root / "rag" / "manifests" / "chunks.jsonl"
        if rag_chunks_ready(refreshed_chunks_path):
            resolved_chunks_path = refreshed_chunks_path
    resolved_events_dir = events_dir
    if require_events and not events_ready:
        refreshed_events_dir = output_root / "timeline" / "events"
        if timeline_events_ready(refreshed_events_dir):
            resolved_events_dir = refreshed_events_dir
    return resolved_chunks_path, resolved_events_dir, output_root, report


def query_file_refs(
    *,
    source_path: str,
    direction: str = "both",
    index_path: Path = DEFAULT_FILE_RELATION_INDEX,
    limit: int = 20,
    auto_refresh: bool = False,
    refresh_output_root: Path | None = None,
    expanded_graph_path: Path | None = None,
    refresh_repo_root: Path | None = None,
) -> dict[str, Any]:
    """Return direct file-reference relations for one source path."""
    resolved_index_path, output_root, refresh_report = _resolve_file_relation_index(
        index_path=index_path,
        auto_refresh=auto_refresh,
        refresh_output_root=refresh_output_root,
        expanded_graph_path=expanded_graph_path,
        refresh_repo_root=refresh_repo_root,
    )
    payload = _query_file_relations(
        load_file_relation_index(resolved_index_path),
        source_path,
        direction=direction,
        limit=limit,
    )
    payload["index_path"] = str(resolved_index_path)
    payload["refresh_output_root"] = str(output_root) if output_root else None
    payload["refresh_report"] = refresh_report
    return payload


def query_file_impact(
    *,
    source_path: str,
    index_path: Path = DEFAULT_FILE_RELATION_INDEX,
    limit: int = 50,
    auto_refresh: bool = False,
    refresh_output_root: Path | None = None,
    expanded_graph_path: Path | None = None,
    refresh_repo_root: Path | None = None,
) -> dict[str, Any]:
    """Return inbound and outbound impact candidates for one file."""
    payload = query_file_refs(
        source_path=source_path,
        direction="both",
        index_path=index_path,
        limit=limit,
        auto_refresh=auto_refresh,
        refresh_output_root=refresh_output_root,
        expanded_graph_path=expanded_graph_path,
        refresh_repo_root=refresh_repo_root,
    )
    payload["kind"] = "file_impact"
    payload["impact_candidates"] = {
        "files_that_reference_query": [
            item["source_path"] for item in payload["inbound"]
        ],
        "files_referenced_by_query": [
            item["target_path"] for item in payload["outbound"]
        ],
    }
    return payload


def query_file_neighborhood(
    *,
    source_path: str,
    depth: int = 1,
    index_path: Path = DEFAULT_FILE_RELATION_INDEX,
    limit: int = 50,
    auto_refresh: bool = False,
    refresh_output_root: Path | None = None,
    expanded_graph_path: Path | None = None,
    refresh_repo_root: Path | None = None,
) -> dict[str, Any]:
    """Return a bounded graph neighborhood over file-reference relations."""
    resolved_index_path, output_root, refresh_report = _resolve_file_relation_index(
        index_path=index_path,
        auto_refresh=auto_refresh,
        refresh_output_root=refresh_output_root,
        expanded_graph_path=expanded_graph_path,
        refresh_repo_root=refresh_repo_root,
    )
    payload = _query_file_neighborhood(
        load_file_relation_index(resolved_index_path),
        source_path,
        depth=depth,
        limit=limit,
    )
    payload["index_path"] = str(resolved_index_path)
    payload["refresh_output_root"] = str(output_root) if output_root else None
    payload["refresh_report"] = refresh_report
    return payload


def query_module_refs(
    *,
    module_name: str,
    direction: str = "both",
    index_path: Path = DEFAULT_MODULE_RELATION_INDEX,
    limit: int = 20,
    auto_refresh: bool = False,
    refresh_output_root: Path | None = None,
    expanded_graph_path: Path | None = None,
    refresh_repo_root: Path | None = None,
) -> dict[str, Any]:
    """Return direct module-reference relations for one module."""
    resolved_index_path, output_root, refresh_report = _resolve_module_relation_index(
        index_path=index_path,
        auto_refresh=auto_refresh,
        refresh_output_root=refresh_output_root,
        expanded_graph_path=expanded_graph_path,
        refresh_repo_root=refresh_repo_root,
    )
    payload = _query_module_relations(
        load_module_relation_index(resolved_index_path),
        module_name,
        direction=direction,
        limit=limit,
    )
    payload["index_path"] = str(resolved_index_path)
    payload["refresh_output_root"] = str(output_root) if output_root else None
    payload["refresh_report"] = refresh_report
    return payload


def query_module_impact(
    *,
    module_name: str,
    index_path: Path = DEFAULT_MODULE_RELATION_INDEX,
    limit: int = 50,
    auto_refresh: bool = False,
    refresh_output_root: Path | None = None,
    expanded_graph_path: Path | None = None,
    refresh_repo_root: Path | None = None,
) -> dict[str, Any]:
    """Return inbound and outbound impact candidates for one module."""
    payload = query_module_refs(
        module_name=module_name,
        direction="both",
        index_path=index_path,
        limit=limit,
        auto_refresh=auto_refresh,
        refresh_output_root=refresh_output_root,
        expanded_graph_path=expanded_graph_path,
        refresh_repo_root=refresh_repo_root,
    )
    payload["kind"] = "module_impact"
    payload["impact_candidates"] = {
        "modules_that_reference_query": [
            item["source_name"] for item in payload["inbound"]
        ],
        "modules_referenced_by_query": [
            item["target_name"] for item in payload["outbound"]
        ],
    }
    return payload


def query_module_neighborhood(
    *,
    module_name: str,
    depth: int = 1,
    index_path: Path = DEFAULT_MODULE_RELATION_INDEX,
    limit: int = 50,
    auto_refresh: bool = False,
    refresh_output_root: Path | None = None,
    expanded_graph_path: Path | None = None,
    refresh_repo_root: Path | None = None,
) -> dict[str, Any]:
    """Return a bounded graph neighborhood over module-reference relations."""
    resolved_index_path, output_root, refresh_report = _resolve_module_relation_index(
        index_path=index_path,
        auto_refresh=auto_refresh,
        refresh_output_root=refresh_output_root,
        expanded_graph_path=expanded_graph_path,
        refresh_repo_root=refresh_repo_root,
    )
    payload = _query_module_neighborhood(
        load_module_relation_index(resolved_index_path),
        module_name,
        depth=depth,
        limit=limit,
    )
    payload["index_path"] = str(resolved_index_path)
    payload["refresh_output_root"] = str(output_root) if output_root else None
    payload["refresh_report"] = refresh_report
    return payload


def query_entity_refs(
    *,
    entity: str,
    direction: str = "both",
    relation: str | None = None,
    index_path: Path = DEFAULT_ENTITY_RELATION_INDEX,
    limit: int = 20,
    auto_refresh: bool = False,
    refresh_output_root: Path | None = None,
    expanded_graph_path: Path | None = None,
    refresh_repo_root: Path | None = None,
) -> dict[str, Any]:
    """Return direct generic entity relation records for one graph entity."""
    resolved_index_path, output_root, refresh_report = _resolve_entity_relation_index(
        index_path=index_path,
        auto_refresh=auto_refresh,
        refresh_output_root=refresh_output_root,
        expanded_graph_path=expanded_graph_path,
        refresh_repo_root=refresh_repo_root,
    )
    payload = _query_entity_relations(
        load_entity_relation_index(resolved_index_path),
        entity,
        direction=direction,
        relation=relation,
        limit=limit,
    )
    payload["index_path"] = str(resolved_index_path)
    payload["refresh_output_root"] = str(output_root) if output_root else None
    payload["refresh_report"] = refresh_report
    return payload


def query_entity_impact(
    *,
    entity: str,
    index_path: Path = DEFAULT_ENTITY_RELATION_INDEX,
    limit: int = 50,
    auto_refresh: bool = False,
    refresh_output_root: Path | None = None,
    expanded_graph_path: Path | None = None,
    refresh_repo_root: Path | None = None,
) -> dict[str, Any]:
    """Return inbound and outbound impact candidates for one graph entity."""
    payload = query_entity_refs(
        entity=entity,
        direction="both",
        index_path=index_path,
        limit=limit,
        auto_refresh=auto_refresh,
        refresh_output_root=refresh_output_root,
        expanded_graph_path=expanded_graph_path,
        refresh_repo_root=refresh_repo_root,
    )
    payload["kind"] = "entity_impact"
    payload["impact_candidates"] = {
        "entities_that_reference_query": [
            item["source_id"] for item in payload["inbound"]
        ],
        "entities_referenced_by_query": [
            item["target_id"] for item in payload["outbound"]
        ],
    }
    return payload


def query_entity_neighborhood(
    *,
    entity: str,
    depth: int = 1,
    index_path: Path = DEFAULT_ENTITY_RELATION_INDEX,
    limit: int = 50,
    auto_refresh: bool = False,
    refresh_output_root: Path | None = None,
    expanded_graph_path: Path | None = None,
    refresh_repo_root: Path | None = None,
) -> dict[str, Any]:
    """Return a bounded graph neighborhood over generic entity relations."""
    resolved_index_path, output_root, refresh_report = _resolve_entity_relation_index(
        index_path=index_path,
        auto_refresh=auto_refresh,
        refresh_output_root=refresh_output_root,
        expanded_graph_path=expanded_graph_path,
        refresh_repo_root=refresh_repo_root,
    )
    payload = _query_entity_neighborhood(
        load_entity_relation_index(resolved_index_path),
        entity,
        depth=depth,
        limit=limit,
    )
    payload["index_path"] = str(resolved_index_path)
    payload["refresh_output_root"] = str(output_root) if output_root else None
    payload["refresh_report"] = refresh_report
    return payload


def _rag_file_relation_context(
    *,
    file_context: str | None,
    index_path: Path,
    auto_refresh: bool,
    refresh_output_root: Path | None,
    expanded_graph_path: Path | None,
    refresh_repo_root: Path | None,
    depth: int,
) -> tuple[str | None, set[str], dict[str, Any] | None]:
    if file_context is None:
        return None, set(), None
    resolved_index_path, output_root, refresh_report = _resolve_file_relation_index(
        index_path=index_path,
        auto_refresh=auto_refresh,
        refresh_output_root=refresh_output_root,
        expanded_graph_path=expanded_graph_path,
        refresh_repo_root=refresh_repo_root,
    )
    neighborhood = _query_file_neighborhood(
        load_file_relation_index(resolved_index_path),
        file_context,
        depth=depth,
        limit=500,
    )
    resolved_path = neighborhood.get("resolved_path")
    nodes = {
        str(path)
        for path in neighborhood.get("nodes") or []
        if isinstance(path, str) and path != resolved_path
    }
    context = {
        "file_context": file_context,
        "resolved_path": resolved_path,
        "index_path": str(resolved_index_path),
        "depth": depth,
        "related_file_count": len(nodes),
        "refresh_output_root": str(output_root) if output_root else None,
        "refresh_report": refresh_report,
    }
    return str(resolved_path) if resolved_path else None, nodes, context


def query_rag(options: RagQueryOptions) -> dict[str, Any]:
    """Return filtered deterministic RAG chunks."""
    resolved_chunks_path, _, output_root, refresh_report = _resolve_query_paths(
        chunks_path=options.chunks_path,
        events_dir=DEFAULT_TIMELINE_DIR,
        auto_refresh=options.auto_refresh,
        refresh_output_root=options.refresh_output_root,
        refresh_repo_root=options.refresh_repo_root,
        retrieval_query=options.query,
        require_events=False,
    )
    if not rag_chunks_ready(resolved_chunks_path):
        raise _missing_manifest_error(resolved_chunks_path, "RAG chunk manifest")
    chunks = load_chunk_manifest(resolved_chunks_path)
    resolved_file_context, related_file_paths, file_relation_context = (
        _rag_file_relation_context(
            file_context=options.file_context,
            index_path=options.file_relation_index_path,
            auto_refresh=options.auto_refresh,
            refresh_output_root=output_root or options.refresh_output_root,
            expanded_graph_path=options.expanded_graph_path,
            refresh_repo_root=options.refresh_repo_root,
            depth=options.file_context_depth,
        )
    )
    matches = rank_chunks(
        chunks,
        source_type=options.source_type,
        domain=options.domain,
        repo_zone=options.repo_zone,
        symbol_kind=options.symbol_kind,
        query=options.query,
        profile=options.profile,
        file_context_path=resolved_file_context,
        related_file_paths=related_file_paths,
    )[: options.limit]
    return {
        "kind": "rag",
        "query": options.query,
        "profile": options.profile,
        "count": len(matches),
        "chunks_path": str(resolved_chunks_path),
        "file_relation_context": file_relation_context,
        "refresh_output_root": str(output_root) if output_root else None,
        "refresh_report": refresh_report,
        "results": matches,
    }


def _iter_timeline_paths(events_dir: Path) -> list[Path]:
    if not events_dir.exists():
        return []
    return sorted(path for path in events_dir.glob("*.jsonl") if path.is_file())


def _score_timeline_event(
    event: dict[str, Any],
    *,
    query: str | None,
    profile: str,
) -> tuple[int, list[str]]:
    normalized_profile = (
        profile if profile in _TIMELINE_PROFILE_BONUS else DEFAULT_PROFILE
    )
    score = 0
    reasons: list[str] = []

    score += _score_timeline_confidence(event, reasons)
    score += _score_timeline_family(event, normalized_profile, reasons)
    score += _score_timeline_severity(event, reasons)
    score += _score_timeline_query(event, query, reasons)

    return score, reasons


def _score_timeline_confidence(event: dict[str, Any], reasons: list[str]) -> int:
    confidence = str(event.get("confidence") or "derived")
    bonus = _CONFIDENCE_RANKS.get(confidence, 0) // 2
    if bonus:
        reasons.append(f"confidence:{confidence}")
    return bonus


def _score_timeline_family(
    event: dict[str, Any], profile: str, reasons: list[str]
) -> int:
    event_family = str(event.get("event_family") or "")
    bonus = _TIMELINE_PROFILE_BONUS[profile].get(event_family, 0)
    if bonus:
        reasons.append(f"event_family:{event_family}")
    return bonus


def _score_timeline_severity(event: dict[str, Any], reasons: list[str]) -> int:
    severity = str(event.get("severity") or "")
    if severity == "error":
        reasons.append("severity:error")
        return 18
    if severity == "warning":
        reasons.append("severity:warning")
        return 10
    return 0


def _timeline_query_fields(event: dict[str, Any]) -> dict[str, str]:
    return {
        "event_type": str(event.get("event_type") or "").lower(),
        "source": " ".join(
            str(item) for item in event.get("source_refs") or []
        ).lower(),
        "related": " ".join(
            str(item) for item in event.get("related_refs") or []
        ).lower(),
        "graph": " ".join(
            str(item) for item in event.get("graph_node_refs") or []
        ).lower(),
        "payload": json.dumps(
            event.get("payload") or {}, sort_keys=True, ensure_ascii=True
        ).lower(),
    }


def _score_timeline_query(
    event: dict[str, Any],
    query: str | None,
    reasons: list[str],
) -> int:
    if query is None:
        return 0
    lowered_query = query.lower()
    if not lowered_query:
        return 0
    fields = _timeline_query_fields(event)
    score = _score_timeline_exact_query(lowered_query, fields, reasons)
    for token in (token for token in lowered_query.split() if token):
        score += _score_timeline_query_token(token, fields)
    return score


def _score_timeline_exact_query(
    lowered_query: str,
    fields: dict[str, str],
    reasons: list[str],
) -> int:
    weights = {
        "event_type": 25,
        "related": 25,
        "graph": 20,
        "payload": 12,
        "source": 10,
    }
    score = 0
    for field, weight in weights.items():
        if lowered_query in fields[field]:
            score += weight
            reasons.append(f"query:{field}")
    return score


def _score_timeline_query_token(token: str, fields: dict[str, str]) -> int:
    weights = {
        "event_type": 8,
        "related": 9,
        "graph": 7,
        "payload": 3,
        "source": 2,
    }
    return sum(weight for field, weight in weights.items() if token in fields[field])


def _timeline_event_matches(
    event: dict[str, Any],
    *,
    event_family: str | None,
    event_type: str | None,
    lowered_query: str | None,
) -> bool:
    if event_family is not None and event.get("event_family") != event_family:
        return False
    if event_type is not None and event.get("event_type") != event_type:
        return False
    if lowered_query is None:
        return True
    haystack = json.dumps(event, sort_keys=True, ensure_ascii=True).lower()
    return lowered_query in haystack


def query_timeline(
    *,
    query: str | None,
    event_family: str | None,
    event_type: str | None,
    events_dir: Path = DEFAULT_TIMELINE_DIR,
    limit: int = 20,
    profile: str = DEFAULT_PROFILE,
    auto_refresh: bool = False,
    refresh_output_root: Path | None = None,
    refresh_repo_root: Path | None = None,
) -> dict[str, Any]:
    """Return filtered timeline events from generated local projections."""
    _, resolved_events_dir, output_root, refresh_report = _resolve_query_paths(
        chunks_path=DEFAULT_RAG_CHUNKS,
        events_dir=events_dir,
        auto_refresh=auto_refresh,
        refresh_output_root=refresh_output_root,
        refresh_repo_root=refresh_repo_root,
        retrieval_query=query,
        require_chunks=False,
    )
    if not timeline_events_ready(resolved_events_dir):
        raise _missing_manifest_error(
            resolved_events_dir, "timeline event projections"
        )
    matches: list[dict[str, Any]] = []
    lowered_query = query.lower() if query is not None else None
    for path in _iter_timeline_paths(resolved_events_dir):
        for event in read_jsonl(path):
            if not _timeline_event_matches(
                event,
                event_family=event_family,
                event_type=event_type,
                lowered_query=lowered_query,
            ):
                continue
            score, reasons = _score_timeline_event(event, query=query, profile=profile)
            enriched = dict(event)
            enriched["score"] = score
            enriched["ranking_reasons"] = reasons
            matches.append(enriched)
    matches.sort(
        key=lambda item: (
            -int(item.get("score", 0)),
            str(item.get("event_type") or ""),
            str(item.get("id") or ""),
        )
    )
    matches = matches[:limit]
    return {
        "kind": "timeline",
        "query": query,
        "profile": profile,
        "count": len(matches),
        "events_dir": str(resolved_events_dir),
        "refresh_output_root": str(output_root) if output_root else None,
        "refresh_report": refresh_report,
        "results": matches,
    }


def query_all(
    *,
    query: str,
    chunks_path: Path = DEFAULT_RAG_CHUNKS,
    events_dir: Path = DEFAULT_TIMELINE_DIR,
    limit: int = 10,
    profile: str = DEFAULT_PROFILE,
    auto_refresh: bool = False,
    refresh_output_root: Path | None = None,
    refresh_repo_root: Path | None = None,
    file_context: str | None = None,
    file_relation_index_path: Path = DEFAULT_FILE_RELATION_INDEX,
    expanded_graph_path: Path | None = None,
    file_context_depth: int = 1,
) -> dict[str, Any]:
    """Run a lightweight local search across catalog, RAG, and timeline."""
    resolved_chunks_path, resolved_events_dir, output_root, refresh_report = (
        _resolve_query_paths(
            chunks_path=chunks_path,
            events_dir=events_dir,
            auto_refresh=auto_refresh,
            refresh_output_root=refresh_output_root,
            refresh_repo_root=refresh_repo_root,
            retrieval_query=query,
        )
    )
    missing_artifacts: list[dict[str, str]] = []
    rag_results: list[dict[str, Any]] = []
    timeline_results: list[dict[str, Any]] = []
    file_relation_context: dict[str, Any] | None = None

    if rag_chunks_ready(resolved_chunks_path):
        rag_payload = query_rag(
            RagQueryOptions(
                query=query,
                chunks_path=resolved_chunks_path,
                limit=limit,
                profile=profile,
                file_context=file_context,
                file_relation_index_path=file_relation_index_path,
                expanded_graph_path=expanded_graph_path,
                file_context_depth=file_context_depth,
                auto_refresh=False,
                refresh_output_root=output_root or refresh_output_root,
                refresh_repo_root=refresh_repo_root,
            )
        )
        rag_results = rag_payload["results"]
        file_relation_context = rag_payload.get("file_relation_context")
    else:
        missing_artifacts.append(
            {
                "kind": "rag_chunks",
                "path": str(resolved_chunks_path),
                "reason": "missing_or_empty_rag_chunk_manifest",
            }
        )

    if timeline_events_ready(resolved_events_dir):
        timeline_payload = query_timeline(
            query=query,
            event_family=None,
            event_type=None,
            events_dir=resolved_events_dir,
            limit=limit,
            profile=profile,
        )
        timeline_results = timeline_payload["results"]
    else:
        missing_artifacts.append(
            {
                "kind": "timeline_events",
                "path": str(resolved_events_dir),
                "reason": "missing_or_empty_timeline_event_projections",
            }
        )

    return {
        "kind": "all",
        "query": query,
        "profile": profile,
        "chunks_path": str(resolved_chunks_path),
        "events_dir": str(resolved_events_dir),
        "refresh_output_root": str(output_root) if output_root else None,
        "refresh_report": refresh_report,
        "degraded": bool(missing_artifacts),
        "missing_artifacts": missing_artifacts,
        "results": {
            "catalog": _catalog_hits_for_query(query),
            "rag": rag_results,
            "timeline": timeline_results,
        },
        "file_relation_context": file_relation_context,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Unified query facade for local memory-layer retrieval."
    )
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--json", action="store_true", help="Emit machine-readable JSON output."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    catalog_parser = subparsers.add_parser(
        "catalog",
        help="Read a structured memory catalog view.",
        parents=[common],
    )
    catalog_parser.add_argument(
        "view", choices=("sources", "owners", "zones", "placement")
    )

    rag_parser = subparsers.add_parser(
        "rag",
        help="Query deterministic local RAG manifests.",
        parents=[common],
    )
    rag_parser.add_argument("--query", type=str, default=None)
    rag_parser.add_argument("--source-type", type=str, default=None)
    rag_parser.add_argument("--domain", type=str, default=None)
    rag_parser.add_argument("--repo-zone", type=str, default=None)
    rag_parser.add_argument("--symbol-kind", type=str, default=None)
    rag_parser.add_argument("--chunks-path", type=Path, default=DEFAULT_RAG_CHUNKS)
    rag_parser.add_argument("--limit", type=int, default=20)
    rag_parser.add_argument(
        "--auto-refresh",
        action="store_true",
        help="Build temporary RAG/timeline artifacts first when manifests are missing.",
    )
    rag_parser.add_argument("--refresh-output-root", type=Path, default=None)
    rag_parser.add_argument(
        "--file-context",
        type=str,
        default=None,
        help="Boost RAG chunks from this file and its references_file neighborhood.",
    )
    rag_parser.add_argument(
        "--file-relation-index",
        type=Path,
        default=DEFAULT_FILE_RELATION_INDEX,
        help="Generated file relation index used by --file-context.",
    )
    rag_parser.add_argument("--expanded-graph-path", type=Path, default=None)
    rag_parser.add_argument("--file-context-depth", type=int, default=1)
    rag_parser.add_argument(
        "--profile", choices=tuple(TASK_PROFILES.keys()), default=DEFAULT_PROFILE
    )

    timeline_parser = subparsers.add_parser(
        "timeline",
        help="Query deterministic local timeline events.",
        parents=[common],
    )
    timeline_parser.add_argument("--query", type=str, default=None)
    timeline_parser.add_argument("--event-family", type=str, default=None)
    timeline_parser.add_argument("--event-type", type=str, default=None)
    timeline_parser.add_argument(
        "--events-dir", type=Path, default=DEFAULT_TIMELINE_DIR
    )
    timeline_parser.add_argument("--limit", type=int, default=20)
    timeline_parser.add_argument(
        "--auto-refresh",
        action="store_true",
        help="Build temporary RAG/timeline artifacts first when event projections are missing.",
    )
    timeline_parser.add_argument("--refresh-output-root", type=Path, default=None)
    timeline_parser.add_argument(
        "--profile",
        choices=tuple(TASK_PROFILES.keys()),
        default=DEFAULT_PROFILE,
    )

    all_parser = subparsers.add_parser(
        "all",
        help="Search catalog, RAG, and timeline together.",
        parents=[common],
    )
    all_parser.add_argument("query", type=str)
    all_parser.add_argument("--chunks-path", type=Path, default=DEFAULT_RAG_CHUNKS)
    all_parser.add_argument("--events-dir", type=Path, default=DEFAULT_TIMELINE_DIR)
    all_parser.add_argument("--limit", type=int, default=10)
    all_parser.add_argument(
        "--auto-refresh",
        action="store_true",
        help="Build temporary RAG/timeline artifacts first when generated artifacts are missing.",
    )
    all_parser.add_argument("--refresh-output-root", type=Path, default=None)
    all_parser.add_argument(
        "--file-context",
        type=str,
        default=None,
        help="Boost RAG chunks from this file and its references_file neighborhood.",
    )
    all_parser.add_argument(
        "--file-relation-index",
        type=Path,
        default=DEFAULT_FILE_RELATION_INDEX,
        help="Generated file relation index used by --file-context.",
    )
    all_parser.add_argument("--expanded-graph-path", type=Path, default=None)
    all_parser.add_argument("--file-context-depth", type=int, default=1)
    all_parser.add_argument(
        "--profile", choices=tuple(TASK_PROFILES.keys()), default=DEFAULT_PROFILE
    )

    refs_parser = subparsers.add_parser(
        "refs",
        help="Query direct file -> references_file -> file relations.",
        parents=[common],
    )
    refs_parser.add_argument("source_path", type=str)
    refs_parser.add_argument(
        "--direction",
        choices=("both", "outbound", "inbound"),
        default="both",
    )
    refs_parser.add_argument(
        "--index-path",
        type=Path,
        default=DEFAULT_FILE_RELATION_INDEX,
        help=FILE_RELATION_INDEX_HELP,
    )
    refs_parser.add_argument("--limit", type=int, default=20)
    refs_parser.add_argument("--auto-refresh", action="store_true")
    refs_parser.add_argument("--refresh-output-root", type=Path, default=None)
    refs_parser.add_argument("--expanded-graph-path", type=Path, default=None)

    impact_parser = subparsers.add_parser(
        "impact",
        help="Query inbound/outbound file impact candidates.",
        parents=[common],
    )
    impact_parser.add_argument("source_path", type=str)
    impact_parser.add_argument(
        "--index-path",
        type=Path,
        default=DEFAULT_FILE_RELATION_INDEX,
        help=FILE_RELATION_INDEX_HELP,
    )
    impact_parser.add_argument("--limit", type=int, default=50)
    impact_parser.add_argument("--auto-refresh", action="store_true")
    impact_parser.add_argument("--refresh-output-root", type=Path, default=None)
    impact_parser.add_argument("--expanded-graph-path", type=Path, default=None)

    neighborhood_parser = subparsers.add_parser(
        "neighborhood",
        help="Query a bounded file-reference graph neighborhood.",
        parents=[common],
    )
    neighborhood_parser.add_argument("source_path", type=str)
    neighborhood_parser.add_argument("--depth", type=int, default=1)
    neighborhood_parser.add_argument(
        "--index-path",
        type=Path,
        default=DEFAULT_FILE_RELATION_INDEX,
        help=FILE_RELATION_INDEX_HELP,
    )
    neighborhood_parser.add_argument("--limit", type=int, default=50)
    neighborhood_parser.add_argument("--auto-refresh", action="store_true")
    neighborhood_parser.add_argument("--refresh-output-root", type=Path, default=None)
    neighborhood_parser.add_argument("--expanded-graph-path", type=Path, default=None)

    module_refs_parser = subparsers.add_parser(
        "module-refs",
        help="Query direct module -> references -> module relations.",
        parents=[common],
    )
    module_refs_parser.add_argument("module_name", type=str)
    module_refs_parser.add_argument(
        "--direction",
        choices=("both", "outbound", "inbound"),
        default="both",
    )
    module_refs_parser.add_argument(
        "--index-path",
        type=Path,
        default=DEFAULT_MODULE_RELATION_INDEX,
        help=MODULE_RELATION_INDEX_HELP,
    )
    module_refs_parser.add_argument("--limit", type=int, default=20)
    module_refs_parser.add_argument("--auto-refresh", action="store_true")
    module_refs_parser.add_argument("--refresh-output-root", type=Path, default=None)
    module_refs_parser.add_argument("--expanded-graph-path", type=Path, default=None)

    module_impact_parser = subparsers.add_parser(
        "module-impact",
        help="Query inbound/outbound module impact candidates.",
        parents=[common],
    )
    module_impact_parser.add_argument("module_name", type=str)
    module_impact_parser.add_argument(
        "--index-path",
        type=Path,
        default=DEFAULT_MODULE_RELATION_INDEX,
        help=MODULE_RELATION_INDEX_HELP,
    )
    module_impact_parser.add_argument("--limit", type=int, default=50)
    module_impact_parser.add_argument("--auto-refresh", action="store_true")
    module_impact_parser.add_argument("--refresh-output-root", type=Path, default=None)
    module_impact_parser.add_argument("--expanded-graph-path", type=Path, default=None)

    module_neighborhood_parser = subparsers.add_parser(
        "module-neighborhood",
        help="Query a bounded module-reference graph neighborhood.",
        parents=[common],
    )
    module_neighborhood_parser.add_argument("module_name", type=str)
    module_neighborhood_parser.add_argument("--depth", type=int, default=1)
    module_neighborhood_parser.add_argument(
        "--index-path",
        type=Path,
        default=DEFAULT_MODULE_RELATION_INDEX,
        help=MODULE_RELATION_INDEX_HELP,
    )
    module_neighborhood_parser.add_argument("--limit", type=int, default=50)
    module_neighborhood_parser.add_argument("--auto-refresh", action="store_true")
    module_neighborhood_parser.add_argument(
        "--refresh-output-root", type=Path, default=None
    )
    module_neighborhood_parser.add_argument(
        "--expanded-graph-path", type=Path, default=None
    )

    entity_refs_parser = subparsers.add_parser(
        "entity-refs",
        help="Query direct generic entity relations.",
        parents=[common],
    )
    entity_refs_parser.add_argument("entity", type=str)
    entity_refs_parser.add_argument(
        "--direction",
        choices=("both", "outbound", "inbound"),
        default="both",
    )
    entity_refs_parser.add_argument("--relation", type=str, default=None)
    entity_refs_parser.add_argument(
        "--index-path",
        type=Path,
        default=DEFAULT_ENTITY_RELATION_INDEX,
        help=ENTITY_RELATION_INDEX_HELP,
    )
    entity_refs_parser.add_argument("--limit", type=int, default=20)
    entity_refs_parser.add_argument("--auto-refresh", action="store_true")
    entity_refs_parser.add_argument("--refresh-output-root", type=Path, default=None)
    entity_refs_parser.add_argument("--expanded-graph-path", type=Path, default=None)

    entity_impact_parser = subparsers.add_parser(
        "entity-impact",
        help="Query inbound/outbound generic entity impact candidates.",
        parents=[common],
    )
    entity_impact_parser.add_argument("entity", type=str)
    entity_impact_parser.add_argument(
        "--index-path",
        type=Path,
        default=DEFAULT_ENTITY_RELATION_INDEX,
        help=ENTITY_RELATION_INDEX_HELP,
    )
    entity_impact_parser.add_argument("--limit", type=int, default=50)
    entity_impact_parser.add_argument("--auto-refresh", action="store_true")
    entity_impact_parser.add_argument("--refresh-output-root", type=Path, default=None)
    entity_impact_parser.add_argument("--expanded-graph-path", type=Path, default=None)

    entity_neighborhood_parser = subparsers.add_parser(
        "entity-neighborhood",
        help="Query a bounded generic entity-relation graph neighborhood.",
        parents=[common],
    )
    entity_neighborhood_parser.add_argument("entity", type=str)
    entity_neighborhood_parser.add_argument("--depth", type=int, default=1)
    entity_neighborhood_parser.add_argument(
        "--index-path",
        type=Path,
        default=DEFAULT_ENTITY_RELATION_INDEX,
        help=ENTITY_RELATION_INDEX_HELP,
    )
    entity_neighborhood_parser.add_argument("--limit", type=int, default=50)
    entity_neighborhood_parser.add_argument("--auto-refresh", action="store_true")
    entity_neighborhood_parser.add_argument(
        "--refresh-output-root", type=Path, default=None
    )
    entity_neighborhood_parser.add_argument(
        "--expanded-graph-path", type=Path, default=None
    )

    graph_parser = subparsers.add_parser(
        "graph",
        help="Pass through to memory.graph.query.",
        parents=[common],
    )
    graph_parser.add_argument("graph_args", nargs=argparse.REMAINDER)
    return parser


def _payload_exit_code(payload: dict[str, Any]) -> int:
    return 0 if payload.get("ok", True) else 1


def _emit_json_payload(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True))


def _emit_catalog(payload: dict[str, Any]) -> None:
    print(f"Catalog view: {payload['view']}")
    print(json.dumps(payload["payload"], indent=2, sort_keys=True, ensure_ascii=True))


def _emit_ranked_results(payload: dict[str, Any]) -> None:
    kind = payload["kind"]
    print(f"{kind} results: {payload['count']}")
    for item in payload["results"]:
        title = (
            item.get("title")
            or item.get("event_type")
            or item.get("source_path")
            or item.get("id")
        )
        print(f"- {title}")


def _emit_all(payload: dict[str, Any]) -> None:
    results = payload["results"]
    print(f"All-surface query: {payload['query']}")
    print(f"- catalog matches: {len(results['catalog'])}")
    print(f"- rag matches: {len(results['rag'])}")
    print(f"- timeline matches: {len(results['timeline'])}")


def _emit_file_relation_summary(payload: dict[str, Any]) -> None:
    print(f"{payload['kind']}: {payload['query']}")
    print(f"- resolved path: {payload.get('resolved_path')}")
    print(f"- inbound: {len(payload.get('inbound') or [])}")
    print(f"- outbound: {len(payload.get('outbound') or [])}")


def _emit_file_neighborhood_summary(payload: dict[str, Any]) -> None:
    print(f"file_neighborhood: {payload['query']}")
    print(f"- resolved path: {payload.get('resolved_path')}")
    print(f"- nodes: {len(payload.get('nodes') or [])}")
    print(f"- edges: {len(payload.get('edges') or [])}")


def _emit_module_relation_summary(payload: dict[str, Any]) -> None:
    print(f"{payload['kind']}: {payload['query']}")
    print(f"- resolved module: {payload.get('resolved_module')}")
    print(f"- inbound: {len(payload.get('inbound') or [])}")
    print(f"- outbound: {len(payload.get('outbound') or [])}")


def _emit_module_neighborhood_summary(payload: dict[str, Any]) -> None:
    print(f"module_neighborhood: {payload['query']}")
    print(f"- resolved module: {payload.get('resolved_module')}")
    print(f"- nodes: {len(payload.get('nodes') or [])}")
    print(f"- edges: {len(payload.get('edges') or [])}")


def _emit_entity_relation_summary(payload: dict[str, Any]) -> None:
    print(f"{payload['kind']}: {payload['query']}")
    print(f"- resolved entity: {payload.get('resolved_entity')}")
    print(f"- relation filter: {payload.get('relation')}")
    print(f"- inbound: {len(payload.get('inbound') or [])}")
    print(f"- outbound: {len(payload.get('outbound') or [])}")


def _emit_entity_neighborhood_summary(payload: dict[str, Any]) -> None:
    print(f"entity_neighborhood: {payload['query']}")
    print(f"- resolved entity: {payload.get('resolved_entity')}")
    print(f"- nodes: {len(payload.get('nodes') or [])}")
    print(f"- edges: {len(payload.get('edges') or [])}")


_TEXT_EMITTERS = {
    "catalog": _emit_catalog,
    "rag": _emit_ranked_results,
    "timeline": _emit_ranked_results,
    "all": _emit_all,
    "file_refs": _emit_file_relation_summary,
    "file_impact": _emit_file_relation_summary,
    "file_neighborhood": _emit_file_neighborhood_summary,
    "module_refs": _emit_module_relation_summary,
    "module_impact": _emit_module_relation_summary,
    "module_neighborhood": _emit_module_neighborhood_summary,
    "entity_refs": _emit_entity_relation_summary,
    "entity_impact": _emit_entity_relation_summary,
    "entity_neighborhood": _emit_entity_neighborhood_summary,
}


def _emit(payload: dict[str, Any], *, as_json: bool) -> int:
    if as_json:
        _emit_json_payload(payload)
    else:
        _TEXT_EMITTERS.get(str(payload.get("kind")), _emit_json_payload)(payload)
    return _payload_exit_code(payload)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "catalog":
            return _emit(query_catalog(args.view), as_json=args.json)
        if args.command == "rag":
            return _emit(
                query_rag(
                    RagQueryOptions(
                        query=args.query,
                        source_type=args.source_type,
                        domain=args.domain,
                        repo_zone=args.repo_zone,
                        symbol_kind=args.symbol_kind,
                        chunks_path=args.chunks_path,
                        limit=args.limit,
                        profile=args.profile,
                        auto_refresh=args.auto_refresh,
                        refresh_output_root=args.refresh_output_root,
                        file_context=args.file_context,
                        file_relation_index_path=args.file_relation_index,
                        expanded_graph_path=args.expanded_graph_path,
                        file_context_depth=args.file_context_depth,
                    )
                ),
                as_json=args.json,
            )
        if args.command == "timeline":
            return _emit(
                query_timeline(
                    query=args.query,
                    event_family=args.event_family,
                    event_type=args.event_type,
                    events_dir=args.events_dir,
                    limit=args.limit,
                    profile=args.profile,
                    auto_refresh=args.auto_refresh,
                    refresh_output_root=args.refresh_output_root,
                ),
                as_json=args.json,
            )
        if args.command == "all":
            return _emit(
                query_all(
                    query=args.query,
                    chunks_path=args.chunks_path,
                    events_dir=args.events_dir,
                    limit=args.limit,
                    profile=args.profile,
                    auto_refresh=args.auto_refresh,
                    refresh_output_root=args.refresh_output_root,
                    file_context=args.file_context,
                    file_relation_index_path=args.file_relation_index,
                    expanded_graph_path=args.expanded_graph_path,
                    file_context_depth=args.file_context_depth,
                ),
                as_json=args.json,
            )
        if args.command == "refs":
            return _emit(
                query_file_refs(
                    source_path=args.source_path,
                    direction=args.direction,
                    index_path=args.index_path,
                    limit=args.limit,
                    auto_refresh=args.auto_refresh,
                    refresh_output_root=args.refresh_output_root,
                    expanded_graph_path=args.expanded_graph_path,
                ),
                as_json=args.json,
            )
        if args.command == "impact":
            return _emit(
                query_file_impact(
                    source_path=args.source_path,
                    index_path=args.index_path,
                    limit=args.limit,
                    auto_refresh=args.auto_refresh,
                    refresh_output_root=args.refresh_output_root,
                    expanded_graph_path=args.expanded_graph_path,
                ),
                as_json=args.json,
            )
        if args.command == "neighborhood":
            return _emit(
                query_file_neighborhood(
                    source_path=args.source_path,
                    depth=args.depth,
                    index_path=args.index_path,
                    limit=args.limit,
                    auto_refresh=args.auto_refresh,
                    refresh_output_root=args.refresh_output_root,
                    expanded_graph_path=args.expanded_graph_path,
                ),
                as_json=args.json,
            )
        if args.command == "module-refs":
            return _emit(
                query_module_refs(
                    module_name=args.module_name,
                    direction=args.direction,
                    index_path=args.index_path,
                    limit=args.limit,
                    auto_refresh=args.auto_refresh,
                    refresh_output_root=args.refresh_output_root,
                    expanded_graph_path=args.expanded_graph_path,
                ),
                as_json=args.json,
            )
        if args.command == "module-impact":
            return _emit(
                query_module_impact(
                    module_name=args.module_name,
                    index_path=args.index_path,
                    limit=args.limit,
                    auto_refresh=args.auto_refresh,
                    refresh_output_root=args.refresh_output_root,
                    expanded_graph_path=args.expanded_graph_path,
                ),
                as_json=args.json,
            )
        if args.command == "module-neighborhood":
            return _emit(
                query_module_neighborhood(
                    module_name=args.module_name,
                    depth=args.depth,
                    index_path=args.index_path,
                    limit=args.limit,
                    auto_refresh=args.auto_refresh,
                    refresh_output_root=args.refresh_output_root,
                    expanded_graph_path=args.expanded_graph_path,
                ),
                as_json=args.json,
            )
        if args.command == "entity-refs":
            return _emit(
                query_entity_refs(
                    entity=args.entity,
                    direction=args.direction,
                    relation=args.relation,
                    index_path=args.index_path,
                    limit=args.limit,
                    auto_refresh=args.auto_refresh,
                    refresh_output_root=args.refresh_output_root,
                    expanded_graph_path=args.expanded_graph_path,
                ),
                as_json=args.json,
            )
        if args.command == "entity-impact":
            return _emit(
                query_entity_impact(
                    entity=args.entity,
                    index_path=args.index_path,
                    limit=args.limit,
                    auto_refresh=args.auto_refresh,
                    refresh_output_root=args.refresh_output_root,
                    expanded_graph_path=args.expanded_graph_path,
                ),
                as_json=args.json,
            )
        if args.command == "entity-neighborhood":
            return _emit(
                query_entity_neighborhood(
                    entity=args.entity,
                    depth=args.depth,
                    index_path=args.index_path,
                    limit=args.limit,
                    auto_refresh=args.auto_refresh,
                    refresh_output_root=args.refresh_output_root,
                    expanded_graph_path=args.expanded_graph_path,
                ),
                as_json=args.json,
            )
        if args.command == "graph":
            return graph_query.main(args.graph_args)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
