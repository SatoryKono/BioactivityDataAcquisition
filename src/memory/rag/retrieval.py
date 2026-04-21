"""Helpers for loading, filtering, and ranking deterministic RAG chunks."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from memory.resources import POLICY_DIR, load_yaml_resource

SOURCE_BUCKET_BY_TYPE = {
    "code": "runtime_code",
    "config": "project_configs",
    "memory": "memory_implementation",
    "adr": "accepted_adrs",
    "doc": "active_docs",
    "plan": "active_docs",
    "runbook": "active_docs",
    "test": "tests",
    "workflow": "operational_assets",
    "dashboard": "operational_assets",
    "script": "operational_assets",
}

TASK_PROFILES: dict[str, dict[str, dict[str, int]]] = {
    "general": {
        "source_type": {},
        "domain": {},
        "repo_zone": {},
        "symbol_kind": {},
    },
    "architecture": {
        "source_type": {
            "adr": 40,
            "memory": 35,
            "doc": 20,
            "plan": 15,
            "test": 10,
            "code": 5,
        },
        "domain": {"architecture": 35, "memory_subsystem": 25, "project": 10},
        "repo_zone": {"canonical_architecture_docs": 20},
        "symbol_kind": {"markdown_section": 8, "class": 5, "function": 5},
    },
    "implementation": {
        "source_type": {"code": 45, "memory": 35, "config": 30, "test": 20, "adr": 10},
        "domain": {
            "runtime": 25,
            "memory_subsystem": 25,
            "configuration": 20,
            "quality": 10,
        },
        "repo_zone": {"canonical_runtime": 25},
        "symbol_kind": {
            "class": 15,
            "function": 15,
            "async_function": 15,
            "config_section": 10,
        },
    },
    "operations": {
        "source_type": {
            "runbook": 50,
            "workflow": 35,
            "dashboard": 30,
            "script": 25,
            "config": 20,
            "doc": 15,
            "test": 5,
        },
        "domain": {"operations": 35, "configuration": 15},
        "repo_zone": {"canonical_operations_docs": 25},
        "symbol_kind": {"markdown_section": 10, "config_section": 10},
    },
    "audit": {
        "source_type": {
            "test": 35,
            "workflow": 30,
            "memory": 28,
            "adr": 25,
            "config": 20,
            "dashboard": 20,
            "script": 18,
            "plan": 15,
            "doc": 15,
            "code": 10,
        },
        "domain": {
            "quality": 25,
            "memory_subsystem": 25,
            "architecture": 20,
            "configuration": 20,
            "runtime": 10,
        },
        "repo_zone": {"canonical_quality": 20, "canonical_architecture_docs": 15},
        "symbol_kind": {
            "function": 10,
            "class": 10,
            "config_section": 12,
            "markdown_section": 8,
        },
    },
}

_CONFIDENCE_RANKS = {
    level["id"]: int(level["rank"])
    for level in load_yaml_resource(POLICY_DIR / "confidence.yaml").get("levels", [])
    if isinstance(level, dict) and isinstance(level.get("id"), str)
}
_SOURCE_PRIORITY_ORDER = list(
    load_yaml_resource(POLICY_DIR / "source_priority.yaml").get("ordered_sources", [])
)
_SOURCE_PRIORITY_BONUS = {
    source: (len(_SOURCE_PRIORITY_ORDER) - index) * 8
    for index, source in enumerate(_SOURCE_PRIORITY_ORDER)
}


def load_chunk_manifest(path: Path) -> list[dict[str, Any]]:
    """Load a JSONL chunk manifest."""
    chunks: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        chunks.append(json.loads(line))
    return chunks


def filter_chunks(
    chunks: Iterable[dict[str, Any]],
    *,
    source_type: str | None = None,
    domain: str | None = None,
    repo_zone: str | None = None,
    symbol_kind: str | None = None,
    query: str | None = None,
) -> list[dict[str, Any]]:
    """Apply simple deterministic filters to loaded chunk records."""
    lowered_query = query.lower() if query is not None else None
    result: list[dict[str, Any]] = []
    for chunk in chunks:
        if _chunk_matches_filters(
            chunk,
            source_type=source_type,
            domain=domain,
            repo_zone=repo_zone,
            symbol_kind=symbol_kind,
            lowered_query=lowered_query,
        ):
            result.append(chunk)
    return result


def _chunk_matches_filters(
    chunk: dict[str, Any],
    *,
    source_type: str | None,
    domain: str | None,
    repo_zone: str | None,
    symbol_kind: str | None,
    lowered_query: str | None,
) -> bool:
    if source_type is not None and chunk.get("source_type") != source_type:
        return False
    if domain is not None and chunk.get("domain") != domain:
        return False
    if repo_zone is not None and chunk.get("repo_zone") != repo_zone:
        return False
    if symbol_kind is not None and chunk.get("symbol_kind") != symbol_kind:
        return False
    if lowered_query is None:
        return True
    return lowered_query in _chunk_search_haystack(chunk)


def _chunk_search_haystack(chunk: dict[str, Any]) -> str:
    return " ".join(
        str(chunk.get(field, ""))
        for field in (
            "title",
            "content",
            "source_path",
            "source_type",
            "repo_zone",
            "symbol_kind",
            "graph_node_refs",
            "related_refs",
        )
    ).lower()


def score_chunk(
    chunk: dict[str, Any],
    *,
    query: str | None,
    profile: str = "general",
    file_context_path: str | None = None,
    related_file_paths: set[str] | None = None,
) -> tuple[int, list[str]]:
    """Return deterministic ranking score and brief reasons for one chunk."""
    score = 0
    reasons: list[str] = []

    score += _score_source_priority(chunk, reasons)
    score += _score_confidence(chunk, reasons)
    score += _score_profile_fields(chunk, profile, reasons)
    score += _score_query_matches(chunk, query, reasons)
    score += _score_file_relation_context(
        chunk,
        file_context_path=file_context_path,
        related_file_paths=related_file_paths,
        reasons=reasons,
    )

    return score, reasons


def _score_file_relation_context(
    chunk: dict[str, Any],
    *,
    file_context_path: str | None,
    related_file_paths: set[str] | None,
    reasons: list[str],
) -> int:
    chunk_path = str(chunk.get("source_path") or "").replace("\\", "/").lstrip("./")
    if not chunk_path:
        return 0
    if file_context_path is not None and chunk_path == file_context_path:
        reasons.append("file_context:focus")
        return 45
    if related_file_paths is not None and chunk_path in related_file_paths:
        reasons.append("file_relation:references_file")
        return 32
    return 0


def _score_source_priority(chunk: dict[str, Any], reasons: list[str]) -> int:
    source_bucket = SOURCE_BUCKET_BY_TYPE.get(str(chunk.get("source_type") or ""))
    if source_bucket is None:
        return 0
    bonus = _SOURCE_PRIORITY_BONUS.get(source_bucket, 0)
    if bonus:
        reasons.append(f"source:{source_bucket}")
    return bonus


def _score_confidence(chunk: dict[str, Any], reasons: list[str]) -> int:
    confidence = str(chunk.get("confidence") or "derived")
    bonus = _CONFIDENCE_RANKS.get(confidence, 0) // 2
    if bonus:
        reasons.append(f"confidence:{confidence}")
    return bonus


def _score_profile_fields(
    chunk: dict[str, Any],
    profile: str,
    reasons: list[str],
) -> int:
    normalized_profile = profile if profile in TASK_PROFILES else "general"
    weights = TASK_PROFILES[normalized_profile]
    score = 0
    for key, field in (
        ("source_type", "source_type"),
        ("domain", "domain"),
        ("repo_zone", "repo_zone"),
        ("symbol_kind", "symbol_kind"),
    ):
        value = str(chunk.get(field) or "")
        bonus = weights[key].get(value, 0)
        if bonus:
            score += bonus
            reasons.append(f"{field}:{value}")
    return score


def _query_fields(chunk: dict[str, Any]) -> dict[str, str]:
    return {
        "title": str(chunk.get("title") or "").lower(),
        "path": str(chunk.get("source_path") or "").lower(),
        "content": str(chunk.get("content") or "").lower(),
        "related": " ".join(
            str(item) for item in chunk.get("related_refs") or []
        ).lower(),
        "graph": " ".join(
            str(item) for item in chunk.get("graph_node_refs") or []
        ).lower(),
    }


def _score_query_matches(
    chunk: dict[str, Any],
    query: str | None,
    reasons: list[str],
) -> int:
    if query is None:
        return 0
    lowered_query = query.lower()
    if not lowered_query:
        return 0
    fields = _query_fields(chunk)
    score = _score_exact_query_matches(lowered_query, fields, reasons)
    for token in (token for token in lowered_query.split() if token):
        score += _score_query_token(token, fields)
    return score


def _score_exact_query_matches(
    lowered_query: str,
    fields: dict[str, str],
    reasons: list[str],
) -> int:
    weights = {
        "title": 30,
        "path": 22,
        "related": 25,
        "graph": 20,
        "content": 10,
    }
    score = 0
    for field, weight in weights.items():
        if lowered_query in fields[field]:
            score += weight
            reasons.append(f"query:{field}")
    return score


def _score_query_token(token: str, fields: dict[str, str]) -> int:
    weights = {
        "title": 10,
        "path": 8,
        "related": 9,
        "graph": 7,
        "content": 2,
    }
    return sum(weight for field, weight in weights.items() if token in fields[field])


def rank_chunks(
    chunks: Iterable[dict[str, Any]],
    *,
    source_type: str | None = None,
    domain: str | None = None,
    repo_zone: str | None = None,
    symbol_kind: str | None = None,
    query: str | None = None,
    profile: str = "general",
    file_context_path: str | None = None,
    related_file_paths: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Filter and rank chunk records for task-aware retrieval."""
    ranked: list[dict[str, Any]] = []
    for chunk in filter_chunks(
        chunks,
        source_type=source_type,
        domain=domain,
        repo_zone=repo_zone,
        symbol_kind=symbol_kind,
        query=query,
    ):
        score, reasons = score_chunk(
            chunk,
            query=query,
            profile=profile,
            file_context_path=file_context_path,
            related_file_paths=related_file_paths,
        )
        enriched = dict(chunk)
        enriched["score"] = score
        enriched["ranking_reasons"] = reasons
        ranked.append(enriched)
    ranked.sort(
        key=lambda item: (
            -int(item.get("score", 0)),
            str(item.get("source_path") or ""),
            str(item.get("title") or ""),
        )
    )
    return ranked
