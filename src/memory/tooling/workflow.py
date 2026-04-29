"""Daily pre-task and post-task workflow helpers for memory-enabled work."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

from memory.notes import slugify, utc_now_iso, write_markdown_note
from memory.query import DEFAULT_RAG_CHUNKS, DEFAULT_TIMELINE_DIR, query_all
from memory.resources import discover_memory_root, discover_repo_root
from memory.tooling.promote_note import promote_note
from memory.tooling.prune import prune_episodic_notes
from memory.tooling.refresh_all import refresh_all
from memory.tooling.review_curated import review_curated_notes
from memory.validation import validate_memory_scaffold


def _default_note_path(task_id: str, *, kind: str) -> Path:
    memory_root = discover_memory_root()
    slug = slugify(task_id)
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
) -> dict[str, Any]:
    """Run the standard pre-task memory flow."""
    retrieval_query = query or title
    refresh_report: dict[str, Any] | None = None
    output_root: Path | None = refresh_output_root
    if chunks_path is not None:
        resolved_chunks_path = chunks_path
    elif output_root is not None:
        resolved_chunks_path = output_root / "rag" / "manifests" / "chunks.jsonl"
    else:
        resolved_chunks_path = DEFAULT_RAG_CHUNKS

    if events_dir is not None:
        resolved_events_dir = events_dir
    elif output_root is not None:
        resolved_events_dir = output_root / "timeline" / "events"
    else:
        resolved_events_dir = DEFAULT_TIMELINE_DIR

    if run_refresh_if_missing and (
        not resolved_chunks_path.exists() or not resolved_events_dir.exists()
    ):
        if output_root is None:
            output_root = Path(tempfile.mkdtemp(prefix="memory-pre-task-"))
        repo_root = (
            refresh_repo_root
            or discover_repo_root()
            or Path(__file__).resolve().parents[3]
        )
        refresh_report = refresh_all(
            repo_root.resolve(),
            output_root.resolve(),
            include_rag=True,
            include_timeline=True,
            include_graph_export=False,
        )
        resolved_chunks_path = output_root / "rag" / "manifests" / "chunks.jsonl"
        resolved_events_dir = output_root / "timeline" / "events"

    retrieval = query_all(
        query=retrieval_query,
        chunks_path=resolved_chunks_path,
        events_dir=resolved_events_dir,
        limit=limit,
    )
    session_path: Path | None = None
    if create_session_note:
        session_path = session_note_path or _default_note_path(task_id, kind="session")
        write_markdown_note(
            session_path,
            metadata={
                "id": slugify(task_id),
                "title": title,
                "task_id": task_id,
                "created_at": utc_now_iso(),
                "ttl_days": 14,
                "confidence": "episodic",
                "source_refs": source_refs or ["<add-source-ref>"],
                "summary": "Active task session context.",
                "query": retrieval_query,
            },
            body=_session_note_body(title, retrieval_query, retrieval),
        )
    return {
        "kind": "pre-task",
        "task_id": task_id,
        "title": title,
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
    write_markdown_note(
        summary_path,
        metadata={
            "id": slugify(task_id),
            "title": title,
            "task_id": task_id,
            "created_at": utc_now_iso(),
            "ttl_days": 14,
            "confidence": "episodic",
            "source_refs": source_refs or ["<add-source-ref>"],
            "summary": summary,
        },
        body=_summary_note_body(title, summary),
    )

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
            or discover_repo_root()
            or Path(__file__).resolve().parents[3]
        )
        refresh_report = refresh_all(
            repo_root.resolve(),
            output_root.resolve(),
            include_rag=True,
            include_timeline=True,
            include_graph_export=False,
        )

    prune_report = prune_episodic_notes(apply=False) if run_prune else None

    curated_path: Path | None = None
    if promote_to is not None:
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
        "prune_report": prune_report,
        "promoted_note": str(curated_path) if curated_path else None,
        "ok": True if refresh_report is None else bool(refresh_report.get("ok", False)),
    }


def review_curated_workflow(
    *,
    curated_root: Path | None = None,
) -> dict[str, Any]:
    """Run the regular curated-memory review ritual."""
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
    else:
        print(f"Post-task workflow: {payload['task_id']}")
        print(f"- summary note: {payload['summary_note']}")
        if payload.get("refresh_output_root"):
            print(f"- refresh output root: {payload['refresh_output_root']}")
        if payload.get("promoted_note"):
            print(f"- promoted note: {payload['promoted_note']}")
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
