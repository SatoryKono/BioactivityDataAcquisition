"""Unified query facade for local memory-layer retrieval and graph passthrough."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from memory.graph import query as graph_query
from memory.rag.retrieval import TASK_PROFILES, load_chunk_manifest, rank_chunks
from memory.resources import CATALOG_DIR, MEMORY_ROOT, POLICY_DIR, load_yaml_resource
from memory.timeline._common import read_jsonl

DEFAULT_RAG_CHUNKS = MEMORY_ROOT / "rag" / "manifests" / "chunks.jsonl"
DEFAULT_TIMELINE_DIR = MEMORY_ROOT / "timeline" / "events"
DEFAULT_PROFILE = "general"

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


def query_rag(
    *,
    query: str | None,
    source_type: str | None,
    domain: str | None,
    repo_zone: str | None,
    symbol_kind: str | None,
    chunks_path: Path = DEFAULT_RAG_CHUNKS,
    limit: int = 20,
    profile: str = DEFAULT_PROFILE,
) -> dict[str, Any]:
    """Return filtered deterministic RAG chunks."""
    chunks = load_chunk_manifest(chunks_path)
    matches = rank_chunks(
        chunks,
        source_type=source_type,
        domain=domain,
        repo_zone=repo_zone,
        symbol_kind=symbol_kind,
        query=query,
        profile=profile,
    )[:limit]
    return {
        "kind": "rag",
        "query": query,
        "profile": profile,
        "count": len(matches),
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
        "source": " ".join(str(item) for item in event.get("source_refs") or []).lower(),
        "related": " ".join(str(item) for item in event.get("related_refs") or []).lower(),
        "graph": " ".join(str(item) for item in event.get("graph_node_refs") or []).lower(),
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
) -> dict[str, Any]:
    """Return filtered timeline events from generated local projections."""
    matches: list[dict[str, Any]] = []
    lowered_query = query.lower() if query is not None else None
    for path in _iter_timeline_paths(events_dir):
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
        "results": matches,
    }


def query_all(
    *,
    query: str,
    chunks_path: Path = DEFAULT_RAG_CHUNKS,
    events_dir: Path = DEFAULT_TIMELINE_DIR,
    limit: int = 10,
    profile: str = DEFAULT_PROFILE,
) -> dict[str, Any]:
    """Run a lightweight local search across catalog, RAG, and timeline."""
    rag_payload = query_rag(
        query=query,
        source_type=None,
        domain=None,
        repo_zone=None,
        symbol_kind=None,
        chunks_path=chunks_path,
        limit=limit,
        profile=profile,
    )
    timeline_payload = query_timeline(
        query=query,
        event_family=None,
        event_type=None,
        events_dir=events_dir,
        limit=limit,
        profile=profile,
    )

    catalog_hits: list[dict[str, Any]] = []
    lowered_query = query.lower()
    for view in ("sources", "owners", "zones", "placement"):
        payload = query_catalog(view)
        haystack = json.dumps(
            payload["payload"], sort_keys=True, ensure_ascii=True
        ).lower()
        if lowered_query in haystack:
            catalog_hits.append(payload)

    return {
        "kind": "all",
        "query": query,
        "profile": profile,
        "results": {
            "catalog": catalog_hits,
            "rag": rag_payload["results"],
            "timeline": timeline_payload["results"],
        },
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
        "--profile", choices=tuple(TASK_PROFILES.keys()), default=DEFAULT_PROFILE
    )

    graph_parser = subparsers.add_parser(
        "graph",
        help="Pass through to memory.graph.query.",
        parents=[common],
    )
    graph_parser.add_argument("graph_args", nargs=argparse.REMAINDER)
    return parser


def _emit(payload: dict[str, Any], *, as_json: bool) -> int:
    status_code = 0 if payload.get("ok", True) else 1
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True))
        return status_code

    kind = payload.get("kind")
    if kind == "catalog":
        print(f"Catalog view: {payload['view']}")
        print(
            json.dumps(payload["payload"], indent=2, sort_keys=True, ensure_ascii=True)
        )
        return status_code
    if kind in {"rag", "timeline"}:
        print(f"{kind} results: {payload['count']}")
        for item in payload["results"]:
            title = (
                item.get("title")
                or item.get("event_type")
                or item.get("source_path")
                or item.get("id")
            )
            print(f"- {title}")
        return status_code
    if kind == "all":
        results = payload["results"]
        print(f"All-surface query: {payload['query']}")
        print(f"- catalog matches: {len(results['catalog'])}")
        print(f"- rag matches: {len(results['rag'])}")
        print(f"- timeline matches: {len(results['timeline'])}")
        return status_code
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True))
    return status_code


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "catalog":
        return _emit(query_catalog(args.view), as_json=args.json)
    if args.command == "rag":
        return _emit(
            query_rag(
                query=args.query,
                source_type=args.source_type,
                domain=args.domain,
                repo_zone=args.repo_zone,
                symbol_kind=args.symbol_kind,
                chunks_path=args.chunks_path,
                limit=args.limit,
                profile=args.profile,
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
            ),
            as_json=args.json,
        )
    if args.command == "graph":
        return graph_query.main(args.graph_args)
    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
