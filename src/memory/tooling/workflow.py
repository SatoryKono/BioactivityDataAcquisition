"""Daily pre-task and post-task workflow helpers for memory-enabled work."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

WORKFLOW_PRUNE_PREVIEW_LIMIT = 10
DEFAULT_PROFILE = "general"


def _discover_memory_root() -> Path:
    from memory.resources import discover_memory_root

    return discover_memory_root()


def _discover_repo_root() -> Path | None:
    from memory.resources import discover_repo_root

    return discover_repo_root()


def _query_defaults() -> tuple[Path, Path]:
    from memory.query import default_rag_chunks_path, default_timeline_dir

    return default_rag_chunks_path(), default_timeline_dir()


def _query_runtime() -> tuple[dict[str, object], Any, Any]:
    from memory.query import TASK_PROFILES, query_all, query_catalog

    return TASK_PROFILES, query_all, query_catalog


def _rag_max_sources() -> int:
    from memory.rag.filters import WORKFLOW_RAG_MAX_SOURCES

    return WORKFLOW_RAG_MAX_SOURCES


def _write_note(*, path: Path, metadata: dict[str, Any], body: str) -> None:
    from memory.notes import write_markdown_note

    write_markdown_note(path, metadata=metadata, body=body)


def _slugify_task_id(task_id: str) -> str:
    from memory.notes import slugify

    return slugify(task_id)


def _utc_now() -> str:
    from memory.notes import utc_now_iso

    return utc_now_iso()


def _rag_chunks_ready(path: Path) -> bool:
    from memory.artifact_readiness import rag_chunks_ready

    return rag_chunks_ready(path)


def _timeline_events_ready(path: Path) -> bool:
    from memory.artifact_readiness import timeline_events_ready

    return timeline_events_ready(path)


def _default_note_path(task_id: str, *, kind: str) -> Path:
    memory_root = _discover_memory_root()
    slug = _slugify_task_id(task_id)
    if kind == "session":
        return memory_root / "episodic" / "sessions" / f"{slug}.md"
    if kind == "summary":
        return memory_root / "episodic" / "summaries" / f"{slug}.md"
    raise ValueError(f"unsupported episodic note kind: {kind}")


def _session_note_body(
    title: str, retrieval_query: str, retrieval_results: dict[str, Any]
) -> str:
    rag_count = len(retrieval_results["results"]["rag"])
    timeline_count = len(retrieval_results["results"]["timeline"])
    catalog_count = len(retrieval_results["results"]["catalog"])
    return (
        f"# Session note\n\n"
        f"## Task\n\n"
        f"- Title: {title}\n"
        f"- Retrieval query: {retrieval_query}\n\n"
        f"## Retrieved context\n\n"
        f"- Catalog hits: {catalog_count}\n"
        f"- RAG hits: {rag_count}\n"
        f"- Timeline hits: {timeline_count}\n\n"
        f"## Working notes\n\n"
        f"- Replace with current findings\n"
    )


def _summary_note_body(title: str, summary: str) -> str:
    return (
        f"# Episodic summary\n\n"
        f"## Task\n\n"
        f"- Title: {title}\n\n"
        f"## Outcome\n\n"
        f"- {summary}\n\n"
        f"## Lessons learned\n\n"
        f"- Replace with durable follow-up if needed\n"
    )


def _compact_prune_report(report: dict[str, Any] | None) -> dict[str, Any] | None:
    if report is None:
        return None
    compact = {
        "apply": report.get("apply", False),
        "candidate_count": report.get("candidate_count", 0),
        "removed_count": report.get("removed_count", 0),
    }
    for key in (
        "total_count",
        "active_count",
        "max_active",
        "density_status",
        "density_excess",
    ):
        if key in report:
            compact[key] = report[key]
    candidates = report.get("candidates", [])
    if candidates:
        compact["candidate_preview"] = candidates[:WORKFLOW_PRUNE_PREVIEW_LIMIT]
    removed_paths = report.get("removed_paths", [])
    if removed_paths:
        compact["removed_preview"] = removed_paths[:WORKFLOW_PRUNE_PREVIEW_LIMIT]
    return compact


def _default_pre_task_chunks_path(output_root: Path | None) -> Path:
    if output_root is None:
        return _query_defaults()[0]
    return output_root / "rag" / "manifests" / "chunks.jsonl"


def _default_pre_task_events_dir(output_root: Path | None) -> Path:
    if output_root is None:
        return _query_defaults()[1]
    return output_root / "timeline" / "events"


def _pre_task_surfaces(
    *,
    chunks_path: Path | None,
    events_dir: Path | None,
    output_root: Path | None,
) -> tuple[Path, Path]:
    return (
        chunks_path or _default_pre_task_chunks_path(output_root),
        events_dir or _default_pre_task_events_dir(output_root),
    )


def _refresh_pre_task_surfaces(
    *,
    output_root: Path | None,
    refresh_repo_root: Path | None,
    retrieval_query: str,
    include_rag: bool,
    include_timeline: bool,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    resolved_output_root = output_root or Path(
        tempfile.mkdtemp(prefix="memory-pre-task-")
    )
    repo_root = (
        refresh_repo_root or _discover_repo_root() or Path(__file__).resolve().parents[3]
    )
    from memory.tooling.refresh_all import refresh_all

    refresh_report = refresh_all(
        repo_root.resolve(),
        resolved_output_root.resolve(),
        include_rag=include_rag,
        include_timeline=include_timeline,
        include_graph_export=False,
        rag_build_scope="workflow",
        rag_focus_query=retrieval_query,
        rag_max_sources=_rag_max_sources(),
        allow_partial=True,
    )
    return (
        resolved_output_root,
        resolved_output_root / "rag" / "manifests" / "chunks.jsonl",
        resolved_output_root / "timeline" / "events",
        refresh_report,
    )


def _resolve_pre_task_surfaces(
    *,
    chunks_path: Path | None,
    events_dir: Path | None,
    refresh_output_root: Path | None,
    refresh_repo_root: Path | None,
    run_refresh_if_missing: bool,
    retrieval_query: str,
) -> tuple[Path, Path, Path | None, dict[str, Any] | None]:
    output_root = refresh_output_root
    resolved_chunks_path, resolved_events_dir = _pre_task_surfaces(
        chunks_path=chunks_path, events_dir=events_dir, output_root=output_root
    )
    chunks_ready = _rag_chunks_ready(resolved_chunks_path)
    events_ready = _timeline_events_ready(resolved_events_dir)
    if not run_refresh_if_missing:
        return resolved_chunks_path, resolved_events_dir, output_root, None
    if chunks_ready and events_ready:
        return resolved_chunks_path, resolved_events_dir, output_root, None

    output_root, refreshed_chunks_path, refreshed_events_dir, refresh_report = (
        _refresh_pre_task_surfaces(
            output_root=output_root,
            refresh_repo_root=refresh_repo_root,
            retrieval_query=retrieval_query,
            include_rag=not chunks_ready,
            include_timeline=not events_ready,
        )
    )
    if not chunks_ready and _rag_chunks_ready(refreshed_chunks_path):
        resolved_chunks_path = refreshed_chunks_path
    if not events_ready and _timeline_events_ready(refreshed_events_dir):
        resolved_events_dir = refreshed_events_dir
    return resolved_chunks_path, resolved_events_dir, output_root, refresh_report


def _pre_task_missing_artifacts(
    chunks_path: Path, events_dir: Path
) -> list[dict[str, str]]:
    missing: list[dict[str, str]] = []
    if not _rag_chunks_ready(chunks_path):
        missing.append(
            {
                "kind": "rag_chunks",
                "path": str(chunks_path),
                "reason": "missing_or_empty_rag_chunk_manifest",
            }
        )
    if not _timeline_events_ready(events_dir):
        missing.append(
            {
                "kind": "timeline_events",
                "path": str(events_dir),
                "reason": "missing_or_empty_timeline_event_projections",
            }
        )
    return missing


def _empty_pre_task_retrieval(
    *,
    query: str,
    profile: str,
    chunks_path: Path,
    events_dir: Path,
    missing_artifacts: list[dict[str, str]],
) -> dict[str, Any]:
    catalog_hits: list[dict[str, Any]] = []
    _, _, query_catalog_fn = _query_runtime()
    lowered_query = query.lower()
    for view in ("sources", "owners", "zones", "placement"):
        payload = query_catalog_fn(view)
        haystack = json.dumps(
            payload["payload"], sort_keys=True, ensure_ascii=True
        ).lower()
        if lowered_query in haystack:
            catalog_hits.append(payload)
    return {
        "kind": "all",
        "query": query,
        "profile": profile,
        "chunks_path": str(chunks_path),
        "events_dir": str(events_dir),
        "refresh_output_root": None,
        "refresh_report": None,
        "results": {
            "catalog": catalog_hits,
            "rag": [],
            "timeline": [],
        },
        "file_relation_context": None,
        "degraded": True,
        "missing_artifacts": missing_artifacts,
    }


def pre_task_workflow(
    *,
    task_id: str,
    title: str,
    query: str | None,
    source_refs: list[str],
    create_session_note: bool = True,
    session_note_path: Path | None = None,
    chunks_path: Path | None = None,
    events_dir: Path | None = None,
    refresh_output_root: Path | None = None,
    refresh_repo_root: Path | None = None,
    run_refresh_if_missing: bool = True,
    limit: int = 10,
    profile: str = DEFAULT_PROFILE,
) -> dict[str, Any]:
    """Run the standard pre-task memory flow."""
    retrieval_query = query or title
    resolved_chunks_path, resolved_events_dir, output_root, refresh_report = (
        _resolve_pre_task_surfaces(
            chunks_path=chunks_path,
            events_dir=events_dir,
            refresh_output_root=refresh_output_root,
            refresh_repo_root=refresh_repo_root,
            run_refresh_if_missing=run_refresh_if_missing,
            retrieval_query=retrieval_query,
        )
    )

    task_profiles, query_all_fn, _ = _query_runtime()
    if profile not in task_profiles:
        raise ValueError(f"unsupported task profile: {profile}")

    missing_artifacts = _pre_task_missing_artifacts(
        resolved_chunks_path, resolved_events_dir
    )
    if missing_artifacts:
        retrieval = _empty_pre_task_retrieval(
            query=retrieval_query,
            profile=profile,
            chunks_path=resolved_chunks_path,
            events_dir=resolved_events_dir,
            missing_artifacts=missing_artifacts,
        )
    else:
        retrieval = query_all_fn(
            query=retrieval_query,
            chunks_path=resolved_chunks_path,
            events_dir=resolved_events_dir,
            limit=limit,
            profile=profile,
        )
    session_path: Path | None = None
    if create_session_note:
        session_path = session_note_path or _default_note_path(task_id, kind="session")
        _write_note(
            path=session_path,
            metadata={
                "id": _slugify_task_id(task_id),
                "title": title,
                "task_id": task_id,
                "created_at": _utc_now(),
                "ttl_days": 14,
                "confidence": "episodic",
                "source_refs": source_refs or ["<add-source-ref>"],
                "summary": "Active task session context.",
                "query": retrieval_query,
            },
            body=_session_note_body(title, retrieval_query, retrieval),
        )
    degraded = bool(retrieval.get("degraded", False))
    return {
        "kind": "pre-task",
        "task_id": task_id,
        "title": title,
        "ok": not degraded,
        "query": retrieval_query,
        "session_note": str(session_path) if session_path else None,
        "refresh_output_root": str(output_root) if output_root else None,
        "refresh_report": refresh_report,
        "retrieval": retrieval,
    }


def post_task_workflow(
    *,
    task_id: str,
    title: str,
    summary: str,
    source_refs: list[str],
    refresh_output_root: Path | None = None,
    refresh_repo_root: Path | None = None,
    run_refresh: bool = True,
    run_prune: bool = False,
    promote_to: str | None = None,
    move_on_promote: bool = False,
    summary_note_path: Path | None = None,
) -> dict[str, Any]:
    """Run the standard post-task memory flow."""
    summary_path = summary_note_path or _default_note_path(task_id, kind="summary")
    _write_note(
        path=summary_path,
        metadata={
            "id": _slugify_task_id(task_id),
            "title": title,
            "task_id": task_id,
            "created_at": _utc_now(),
            "ttl_days": 14,
            "confidence": "episodic",
            "source_refs": source_refs or ["<add-source-ref>"],
            "summary": summary,
        },
        body=_summary_note_body(title, summary),
    )

    from memory.validation import validate_memory_scaffold

    validation_issues = validate_memory_scaffold()
    if validation_issues:
        return {
            "kind": "post-task",
            "task_id": task_id,
            "title": title,
            "summary_note": str(summary_path),
            "ok": False,
            "validation_issues": [
                {"path": issue.path, "message": issue.message}
                for issue in validation_issues
            ],
        }

    refresh_report: dict[str, Any] | None = None
    output_root = refresh_output_root
    if run_refresh:
        if output_root is None:
            output_root = Path(tempfile.mkdtemp(prefix="memory-post-task-"))
        repo_root = (
            refresh_repo_root
            or _discover_repo_root()
            or Path(__file__).resolve().parents[3]
        )
        from memory.tooling.refresh_all import refresh_all

        refresh_report = refresh_all(
            repo_root.resolve(),
            output_root.resolve(),
            include_rag=True,
            include_timeline=True,
            include_graph_export=False,
            rag_build_scope="workflow",
            rag_focus_query=title,
            rag_max_sources=_rag_max_sources(),
            allow_partial=True,
        )

    if run_prune:
        from memory.tooling.prune import prune_episodic_notes

        prune_report = prune_episodic_notes(apply=False)
    else:
        prune_report = None

    curated_path: Path | None = None
    if promote_to is not None:
        from memory.tooling.promote_note import promote_note

        curated_path = promote_note(
            summary_path,
            target_kind=promote_to,
            summary=summary,
            move=move_on_promote,
        )

    return {
        "kind": "post-task",
        "task_id": task_id,
        "title": title,
        "summary_note": str(summary_path),
        "refresh_output_root": str(output_root) if output_root else None,
        "refresh_report": refresh_report,
        "prune_report": _compact_prune_report(prune_report),
        "promoted_note": str(curated_path) if curated_path else None,
        "degraded": bool(refresh_report and not refresh_report.get("ok", True)),
        "ok": True,
    }


def review_curated_workflow(
    *,
    curated_root: Path | None = None,
) -> dict[str, Any]:
    """Run the regular curated-memory review ritual."""
    from memory.tooling.review_curated import review_curated_notes

    report = review_curated_notes(curated_root)
    summary = report["summary"]
    cadence = "Run this review on a regular engineering cadence and before release or audit checkpoints."
    next_action = (
        "Review due and stale notes, refresh last_verified for durable knowledge, "
        "and archive superseded notes."
    )
    return {
        "kind": "review-curated",
        "ok": True,
        "cadence": cadence,
        "next_action": next_action,
        "summary": summary,
        "records": report["records"],
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the daily pre-task and post-task memory workflow."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    pre_parser = subparsers.add_parser(
        "pre-task", help="Run the standard pre-task retrieval flow."
    )
    pre_parser.add_argument("--task-id", required=True)
    pre_parser.add_argument("--title", required=True)
    pre_parser.add_argument("--query", default=None)
    pre_parser.add_argument("--source-ref", action="append", default=[])
    pre_parser.add_argument("--chunks-path", type=Path, default=None)
    pre_parser.add_argument("--events-dir", type=Path, default=None)
    pre_parser.add_argument("--refresh-output-root", type=Path, default=None)
    pre_parser.add_argument("--skip-refresh-if-missing", action="store_true")
    pre_parser.add_argument("--limit", type=int, default=10)
    pre_parser.add_argument(
        "--profile", default=DEFAULT_PROFILE, help="Task retrieval profile (validated at runtime)."
    )
    pre_parser.add_argument("--skip-session-note", action="store_true")
    pre_parser.add_argument("--json", action="store_true")

    post_parser = subparsers.add_parser(
        "post-task", help="Run the standard post-task memory flow."
    )
    post_parser.add_argument("--task-id", required=True)
    post_parser.add_argument("--title", required=True)
    post_parser.add_argument("--summary", required=True)
    post_parser.add_argument("--source-ref", action="append", default=[])
    post_parser.add_argument("--refresh-output-root", type=Path, default=None)
    post_parser.add_argument("--skip-refresh", action="store_true")
    post_parser.add_argument("--prune", action="store_true")
    post_parser.add_argument(
        "--promote-to",
        choices=("decision", "incident", "lesson", "domain_knowledge"),
        default=None,
    )
    post_parser.add_argument("--move-on-promote", action="store_true")
    post_parser.add_argument("--json", action="store_true")

    review_parser = subparsers.add_parser(
        "review-curated",
        help="Run the regular curated-memory review ritual.",
    )
    review_parser.add_argument("--root", type=Path, default=None)
    review_parser.add_argument("--json", action="store_true")

    return parser


def _payload_exit_code(payload: dict[str, Any]) -> int:
    return 0 if payload.get("ok", True) else 1


def _emit(payload: dict[str, Any], *, as_json: bool) -> int:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True))
    elif payload["kind"] == "pre-task":
        print(f"Pre-task workflow: {payload['task_id']}")
        if payload.get("session_note"):
            print(f"- session note: {payload['session_note']}")
        if payload.get("refresh_output_root"):
            print(f"- refresh output root: {payload['refresh_output_root']}")
        results = payload["retrieval"]["results"]
        print(f"- catalog hits: {len(results['catalog'])}")
        print(f"- rag hits: {len(results['rag'])}")
        print(f"- timeline hits: {len(results['timeline'])}")
        if payload["retrieval"].get("degraded"):
            print("- degraded: missing retrieval artifacts; refresh was skipped")
    else:
        print(f"Post-task workflow: {payload['task_id']}")
        print(f"- summary note: {payload['summary_note']}")
        if payload.get("refresh_output_root"):
            print(f"- refresh output root: {payload['refresh_output_root']}")
        if payload.get("promoted_note"):
            print(f"- promoted note: {payload['promoted_note']}")
        if payload.get("degraded"):
            print("- degraded: refresh completed with partial artifact failures")
    return _payload_exit_code(payload)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "pre-task":
        payload = pre_task_workflow(
            task_id=args.task_id,
            title=args.title,
            query=args.query,
            source_refs=args.source_ref,
            create_session_note=not args.skip_session_note,
            chunks_path=args.chunks_path,
            events_dir=args.events_dir,
            refresh_output_root=args.refresh_output_root,
            run_refresh_if_missing=not args.skip_refresh_if_missing,
            limit=args.limit,
            profile=args.profile,
        )
        return _emit(payload, as_json=args.json)

    if args.command == "post-task":
        payload = post_task_workflow(
            task_id=args.task_id,
            title=args.title,
            summary=args.summary,
            source_refs=args.source_ref,
            refresh_output_root=args.refresh_output_root,
            run_refresh=not args.skip_refresh,
            run_prune=args.prune,
            promote_to=args.promote_to,
            move_on_promote=args.move_on_promote,
        )
        return _emit(payload, as_json=args.json)

    if args.command == "review-curated":
        payload = review_curated_workflow(curated_root=args.root)
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True))
            return 0 if payload.get("ok", True) else 1

        summary = payload["summary"]
        print("Curated review ritual:")
        print(f"- notes: {summary['note_count']}")
        print(f"- due: {summary['due_count']}")
        print(f"- stale: {summary['stale_count']}")
        print(f"- review candidates: {summary['review_candidates']}")
        print(f"- cadence: {payload['cadence']}")
        print(f"- next action: {payload['next_action']}")
        return 0 if payload.get("ok", True) else 1

    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
