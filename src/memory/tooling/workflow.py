"""Daily pre-task and post-task workflow helpers for memory-enabled work."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from contextlib import ExitStack
from pathlib import Path
from typing import Any

WORKFLOW_PRUNE_PREVIEW_LIMIT = 10
DEFAULT_PROFILE = "general"
DEFAULT_POST_TASK_VALIDATION_TIMEOUT_SECONDS = 15.0
# Cold workflow refresh on mounted or cloud-synced checkouts can exceed the
# validation budget while still being bounded enough for the post-task path.
DEFAULT_POST_TASK_REFRESH_TIMEOUT_SECONDS = 120.0
_UNKNOWN_PATH = "<unknown>"
_DAILY_WORKFLOW_MD = "src/memory/DAILY_WORKFLOW.md"
_CHUNKS_JSONL = "chunks.jsonl"
_MEMORY_WORKFLOW_SMOKE_TITLE = "Memory workflow smoke"
# Deterministic non-production actor identity for the smoke command only.
# Must not be used by production pre-task / post-task CLI paths.
_SMOKE_RUNTIME = "smoke"
_SMOKE_AGENT = "memory-workflow-smoke"
# Smoke writes only under a TemporaryDirectory; force read-write so ambient
# BIOETL_AI_MEMORY_MODE=read-only|off does not disable session/summary notes.
_SMOKE_MEMORY_MODE = "read-write"
_SMOKE_PROVENANCE_ENV = (
    "BIOETL_AI_RUNTIME",
    "BIOETL_AI_AGENT",
    "BIOETL_AI_MEMORY_MODE",
)


def _discover_memory_root() -> Path:
    from memory.resources import discover_memory_root

    return discover_memory_root()


def _discover_repo_root() -> Path | None:
    from memory.resources import discover_repo_root

    return discover_repo_root()


def _query_defaults() -> tuple[Path, Path]:
    from memory.query import default_rag_chunks_path, default_timeline_dir

    return default_rag_chunks_path(), default_timeline_dir()


def _query_runtime() -> tuple[Any, Any, Any]:
    from memory.query import TASK_PROFILES, query_all, query_catalog

    return TASK_PROFILES, query_all, query_catalog


def _rag_max_sources() -> int:
    from memory.rag.filters import WORKFLOW_RAG_MAX_SOURCES

    return WORKFLOW_RAG_MAX_SOURCES


def refresh_all(
    root: Path,
    output_root: Path,
    *,
    include_rag: bool = True,
    include_timeline: bool = True,
    include_graph_export: bool = False,
    include_graph_relations: bool = False,
    expanded_graph_path: Path | None = None,
    rag_build_scope: str = "repo",
    rag_focus_query: str | None = None,
    rag_max_sources: int | None = None,
    allow_partial: bool = False,
) -> dict[str, Any]:
    """Module seam for workflow-time refresh, patchable in integration tests."""
    from memory.tooling.refresh_all import refresh_all as _refresh_all

    return _refresh_all(
        root,
        output_root,
        include_rag=include_rag,
        include_timeline=include_timeline,
        include_graph_export=include_graph_export,
        include_graph_relations=include_graph_relations,
        expanded_graph_path=expanded_graph_path,
        rag_build_scope=rag_build_scope,
        rag_focus_query=rag_focus_query,
        rag_max_sources=rag_max_sources,
        allow_partial=allow_partial,
    )


def validate_memory_scaffold() -> list[Any]:
    """Module seam for scaffold validation, patchable in integration tests."""
    from memory.validation import validate_memory_scaffold as _validate

    return list(_validate())


def _format_validation_issues(issues: list[object]) -> list[dict[str, str]]:
    formatted: list[dict[str, str]] = []
    for issue in issues:
        path = getattr(issue, "path", _UNKNOWN_PATH)
        message = getattr(issue, "message", str(issue))
        formatted.append({"path": str(path), "message": str(message)})
    return formatted


def _run_post_task_validation(
    *,
    timeout_seconds: float | None,
    repo_root: Path,
) -> dict[str, Any]:
    if timeout_seconds is None or timeout_seconds <= 0:
        issues = validate_memory_scaffold()
        return {
            "status": "completed",
            "issues": _format_validation_issues(issues),
        }

    command = [sys.executable, "-m", "memory.tooling.validate", "--json"]
    try:
        result = subprocess.run(
            command,
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "status": "timed_out",
            "issues": [],
            "timeout_seconds": timeout_seconds,
            "stderr": (exc.stderr or "").strip(),
        }
    except OSError as exc:
        return {
            "status": "runtime_error",
            "issues": [],
            "timeout_seconds": timeout_seconds,
            "error": str(exc),
        }

    stdout = result.stdout.strip()
    stderr = result.stderr.strip()
    try:
        payload = json.loads(stdout) if stdout else {}
    except json.JSONDecodeError:
        return {
            "status": "runtime_error",
            "issues": [],
            "timeout_seconds": timeout_seconds,
            "error": "validation subprocess returned non-JSON output",
            "stdout": stdout,
            "stderr": stderr,
            "returncode": result.returncode,
        }

    issues = payload.get("issues", [])
    if isinstance(issues, list) and result.returncode in (0, 1):
        return {"status": "completed", "issues": issues}

    return {
        "status": "runtime_error",
        "issues": issues if isinstance(issues, list) else [],
        "timeout_seconds": timeout_seconds,
        "stdout": stdout,
        "stderr": stderr,
        "returncode": result.returncode,
    }


def _run_post_task_refresh(
    *,
    timeout_seconds: float | None,
    repo_root: Path,
    output_root: Path,
    focus_query: str,
) -> dict[str, Any]:
    if timeout_seconds is None or timeout_seconds <= 0:
        try:
            return refresh_all(
                repo_root.resolve(),
                output_root.resolve(),
                include_rag=True,
                include_timeline=True,
                include_graph_export=False,
                rag_build_scope="workflow",
                rag_focus_query=focus_query,
                rag_max_sources=_rag_max_sources(),
                allow_partial=True,
            )
        except Exception as exc:
            return {
                "ok": False,
                "status": "runtime_error",
                "artifacts": [],
                "error": f"{exc.__class__.__name__}: {exc}",
            }

    command = [
        sys.executable,
        "-m",
        "memory.tooling.refresh_all",
        "--root",
        str(repo_root.resolve()),
        "--output-root",
        str(output_root.resolve()),
        "--rag-build-scope",
        "workflow",
        "--rag-focus-query",
        focus_query,
        "--rag-max-sources",
        str(_rag_max_sources()),
        "--allow-partial",
        "--json",
    ]
    try:
        result = subprocess.run(
            command,
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "status": "timed_out",
            "timeout_seconds": timeout_seconds,
            "artifacts": [],
            "stderr": (exc.stderr or "").strip(),
        }
    except OSError as exc:
        return {
            "ok": False,
            "status": "runtime_error",
            "timeout_seconds": timeout_seconds,
            "artifacts": [],
            "error": str(exc),
        }

    stdout = result.stdout.strip()
    stderr = result.stderr.strip()
    try:
        payload = json.loads(stdout) if stdout else {}
    except json.JSONDecodeError:
        return {
            "ok": False,
            "status": "runtime_error",
            "timeout_seconds": timeout_seconds,
            "artifacts": [],
            "error": "refresh subprocess returned non-JSON output",
            "stdout": stdout,
            "stderr": stderr,
            "returncode": result.returncode,
        }

    if not isinstance(payload, dict):
        return {
            "ok": False,
            "status": "runtime_error",
            "timeout_seconds": timeout_seconds,
            "artifacts": [],
            "error": "refresh subprocess returned non-object JSON output",
            "stdout": stdout,
            "stderr": stderr,
            "returncode": result.returncode,
        }
    if result.returncode != 0:
        payload = {
            **payload,
            "ok": False,
            "status": payload.get("status", "runtime_error"),
            "timeout_seconds": timeout_seconds,
            "stderr": stderr,
            "returncode": result.returncode,
        }
    return payload


def prune_episodic_notes(*, apply: bool = False) -> dict[str, Any]:
    """Module seam for episodic pruning, patchable in integration tests."""
    from memory.tooling.prune import prune_episodic_notes as _prune

    return _prune(apply=apply)


def promote_note(
    source: Path,
    *,
    target_kind: str,
    summary: str,
    move: bool = False,
) -> Path:
    """Module seam for note promotion, patchable in integration tests."""
    from memory.tooling.promote_note import promote_note as _promote_note

    return _promote_note(
        source,
        target_kind=target_kind,
        summary=summary,
        move=move,
    )


def review_curated_notes(root: Path | None = None) -> dict[str, Any]:
    """Module seam for curated review ritual, patchable in integration tests."""
    from memory.tooling.review_curated import review_curated_notes as _review

    return _review(root)


def _write_note(*, path: Path, metadata: dict[str, Any], body: str) -> None:
    from memory.notes import write_markdown_note
    from memory.security import TrustLevel, assert_safe_for_persistence

    persistent_payload = json.dumps(
        {"metadata": metadata, "body": body},
        ensure_ascii=True,
        sort_keys=True,
    )
    assert_safe_for_persistence(
        persistent_payload,
        trust=TrustLevel.TRUSTED_REPOSITORY,
    )
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
    from memory.scope import RepositoryScope

    repo_root = _discover_repo_root() or Path(__file__).resolve().parents[3]
    scope = RepositoryScope.discover(repo_root, task_id=task_id)
    namespace = scope.namespace_path(memory_root / "episodic" / "tasks")
    if kind == "session":
        return namespace / "session.md"
    if kind == "summary":
        return namespace / "summary.md"
    raise ValueError(f"unsupported episodic note kind: {kind}")


def _record_envelope_metadata(
    *,
    task_id: str,
    record_id: str,
    source_refs: list[str],
) -> dict[str, Any]:
    """Return version-bound provenance shared by generated task notes."""
    from memory.records import (
        ActorIdentity,
        RecordEnvelope,
        RecordType,
        SecurityClass,
        TrustLevel,
    )
    from memory.scope import RepositoryScope

    repo_root = _discover_repo_root() or Path(__file__).resolve().parents[3]
    scope = RepositoryScope.discover(repo_root, task_id=task_id)
    runtime = os.environ.get("BIOETL_AI_RUNTIME", "").strip()
    agent = os.environ.get("BIOETL_AI_AGENT", "").strip()
    if not runtime or runtime.lower() == "unknown":
        raise ValueError(
            "BIOETL_AI_RUNTIME must identify the runtime for durable memory writes"
        )
    if not agent or agent.lower() == "unknown":
        raise ValueError(
            "BIOETL_AI_AGENT must identify the agent for durable memory writes"
        )
    envelope = RecordEnvelope.create(
        record_id=record_id,
        record_type=RecordType.WORKING,
        repo_id=scope.repo_id,
        git_commit=scope.git_commit,
        branch=scope.branch,
        worktree_id=scope.worktree_id,
        task_id=task_id,
        actor=ActorIdentity(
            runtime=runtime,
            agent=agent,
            model=os.environ.get("BIOETL_AI_MODEL"),
        ),
        source_refs=tuple(source_refs),
        trust=TrustLevel.TRUSTED_REPOSITORY,
        security_class=SecurityClass.INTERNAL,
    )
    payload = envelope.to_dict()
    payload["content_digest"] = envelope.content_digest
    return payload


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
    return output_root / "rag" / "manifests" / _CHUNKS_JSONL


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
        refresh_repo_root
        or _discover_repo_root()
        or Path(__file__).resolve().parents[3]
    )
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
        resolved_output_root / "rag" / "manifests" / _CHUNKS_JSONL,
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
    from memory.persistence import resolve_persistence_policy

    persistence = resolve_persistence_policy()
    create_session_note = create_session_note and persistence.can_write
    # Read-only mode forbids persistent memory mutation, but rebuild-only
    # retrieval artifacts may still be generated in an isolated temporary
    # directory. Never honor a caller-provided output root without write
    # capability; this keeps read-only refresh ephemeral by construction.
    if run_refresh_if_missing and not persistence.can_write:
        refresh_output_root = None
    retrieval_query = query or title
    if not persistence.can_read:
        return {
            "kind": "pre-task",
            "task_id": task_id,
            "title": title,
            "persistence_mode": persistence.mode.value,
            "ok": True,
            "query": retrieval_query,
            "session_note": None,
            "refresh_output_root": None,
            "refresh_report": None,
            "retrieval": {
                "kind": "disabled",
                "query": retrieval_query,
                "results": {},
                "degraded": False,
                "missing_artifacts": [],
            },
        }
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
        effective_source_refs = source_refs or ["<add-source-ref>"]
        _write_note(
            path=session_path,
            metadata={
                **_record_envelope_metadata(
                    task_id=task_id,
                    record_id=_slugify_task_id(task_id),
                    source_refs=effective_source_refs,
                ),
                "id": _slugify_task_id(task_id),
                "title": title,
                "ttl_days": 14,
                "confidence": "episodic",
                "source_refs": effective_source_refs,
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
        "persistence_mode": persistence.mode.value,
        "ok": not degraded,
        "query": retrieval_query,
        "session_note": str(session_path) if session_path else None,
        "refresh_output_root": str(output_root) if output_root else None,
        "refresh_report": refresh_report,
        "retrieval": retrieval,
    }


def _post_task_base_payload(
    *,
    task_id: str,
    title: str,
    summary_path: Path,
) -> dict[str, Any]:
    return {
        "kind": "post-task",
        "task_id": task_id,
        "title": title,
        "summary_note": str(summary_path),
    }


def _format_post_task_validation_issue(issue: object) -> dict[str, str]:
    if isinstance(issue, dict):
        return {
            "path": str(issue.get("path", _UNKNOWN_PATH)),
            "message": str(issue.get("message", issue)),
        }
    return {
        "path": str(getattr(issue, "path", _UNKNOWN_PATH)),
        "message": str(getattr(issue, "message", issue)),
    }


def _post_task_validation_failure_payload(
    *,
    task_id: str,
    title: str,
    summary_path: Path,
    validation_result: dict[str, Any],
) -> dict[str, Any] | None:
    validation_issues = validation_result.get("issues", [])
    validation_status = validation_result.get("status", "completed")
    base = _post_task_base_payload(
        task_id=task_id, title=title, summary_path=summary_path
    )
    if validation_status != "completed":
        payload: dict[str, Any] = {
            **base,
            "ok": False,
            "degraded": True,
            "validation_status": validation_status,
            "validation_issues": validation_issues,
        }
        if "timeout_seconds" in validation_result:
            payload["validation_timeout_seconds"] = validation_result["timeout_seconds"]
        for key in ("error", "stderr", "stdout", "returncode"):
            if value := validation_result.get(key):
                payload[f"validation_{key}"] = value
        return payload
    if not validation_issues:
        return None
    return {
        **base,
        "ok": False,
        "validation_issues": [
            _format_post_task_validation_issue(issue) for issue in validation_issues
        ],
    }


def _maybe_run_post_task_refresh(
    *,
    run_refresh: bool,
    refresh_timeout_seconds: float | None,
    repo_root: Path,
    refresh_repo_root: Path | None,
    refresh_output_root: Path | None,
    focus_query: str,
) -> tuple[Path | None, dict[str, Any] | None]:
    if not run_refresh:
        return refresh_output_root, None
    output_root = refresh_output_root or Path(
        tempfile.mkdtemp(prefix="memory-post-task-")
    )
    refresh_report = _run_post_task_refresh(
        timeout_seconds=refresh_timeout_seconds,
        repo_root=(refresh_repo_root or repo_root).resolve(),
        output_root=output_root.resolve(),
        focus_query=focus_query,
    )
    return output_root, refresh_report


def _write_post_task_summary_note(
    *,
    task_id: str,
    title: str,
    summary: str,
    source_refs: list[str],
    summary_note_path: Path | None,
) -> Path:
    summary_path = summary_note_path or _default_note_path(task_id, kind="summary")
    effective_source_refs = source_refs or ["<add-source-ref>"]
    _write_note(
        path=summary_path,
        metadata={
            **_record_envelope_metadata(
                task_id=task_id,
                record_id=_slugify_task_id(task_id),
                source_refs=effective_source_refs,
            ),
            "id": _slugify_task_id(task_id),
            "title": title,
            "ttl_days": 14,
            "confidence": "episodic",
            "source_refs": effective_source_refs,
            "summary": summary,
        },
        body=_summary_note_body(title, summary),
    )
    return summary_path


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
    validation_timeout_seconds: float
    | None = DEFAULT_POST_TASK_VALIDATION_TIMEOUT_SECONDS,
    refresh_timeout_seconds: float | None = None,
) -> dict[str, Any]:
    """Run the standard post-task memory flow."""
    from memory.persistence import resolve_persistence_policy

    persistence = resolve_persistence_policy()
    if not persistence.can_write:
        if promote_to is not None:
            persistence.require_write()
        repo_root = _discover_repo_root() or Path(__file__).resolve().parents[3]
        validation_result = _run_post_task_validation(
            timeout_seconds=validation_timeout_seconds,
            repo_root=repo_root.resolve(),
        )
        return {
            "kind": "post-task",
            "task_id": task_id,
            "title": title,
            "summary_note": None,
            "persistence_mode": persistence.mode.value,
            "refresh_output_root": None,
            "refresh_report": None,
            "prune_report": None,
            "promoted_note": None,
            "validation_status": validation_result.get("status", "completed"),
            "validation_issues": validation_result.get("issues", []),
            "degraded": False,
            "ok": not validation_result.get("issues"),
        }
    summary_path = _write_post_task_summary_note(
        task_id=task_id,
        title=title,
        summary=summary,
        source_refs=source_refs,
        summary_note_path=summary_note_path,
    )
    repo_root = _discover_repo_root() or Path(__file__).resolve().parents[3]
    validation_result = _run_post_task_validation(
        timeout_seconds=validation_timeout_seconds,
        repo_root=repo_root.resolve(),
    )
    failure_payload = _post_task_validation_failure_payload(
        task_id=task_id,
        title=title,
        summary_path=summary_path,
        validation_result=validation_result,
    )
    if failure_payload is not None:
        return failure_payload

    output_root, refresh_report = _maybe_run_post_task_refresh(
        run_refresh=run_refresh,
        refresh_timeout_seconds=refresh_timeout_seconds,
        repo_root=repo_root,
        refresh_repo_root=refresh_repo_root,
        refresh_output_root=refresh_output_root,
        focus_query=title,
    )
    prune_report = prune_episodic_notes(apply=False) if run_prune else None
    curated_path = (
        promote_note(
            summary_path,
            target_kind=promote_to,
            summary=summary,
            move=move_on_promote,
        )
        if promote_to is not None
        else None
    )
    return {
        **_post_task_base_payload(
            task_id=task_id, title=title, summary_path=summary_path
        ),
        "refresh_output_root": str(output_root) if output_root else None,
        "persistence_mode": persistence.mode.value,
        "refresh_report": refresh_report,
        "prune_report": _compact_prune_report(prune_report),
        "promoted_note": str(curated_path) if curated_path else None,
        "degraded": bool(refresh_report and not refresh_report.get("ok", True)),
        "ok": True,
    }


def _write_smoke_inputs(root: Path) -> tuple[Path, Path]:
    from memory.rag.chunking import content_hash

    chunk_content = "memory workflow pre post smoke"
    source_path = _DAILY_WORKFLOW_MD
    chunk = {
        "id": "memory-workflow-smoke-chunk",
        "title": _MEMORY_WORKFLOW_SMOKE_TITLE,
        "content": chunk_content,
        "content_hash": content_hash(chunk_content),
        "source_path": source_path,
        "source_type": "doc",
        "domain": "memory",
        "repo_zone": "canonical_runtime",
        "symbol_kind": "markdown_section",
    }
    catalog_path = root / "corpus_catalog.json"
    catalog_path.write_text(
        json.dumps(
            {
                "build_scope": "workflow",
                "chunk_count": 1,
                "focus_query": "memory workflow",
                "generator_version": 2,
                "git_head_sha": None,
                "source_count": 1,
                "source_surface_sha256": "0" * 64,
                "sources": [
                    {
                        "content_hash": "0" * 64,
                        "domain": "memory",
                        "owner": "BioETL Team",
                        "repo_zone": "canonical_runtime",
                        "section_count": 1,
                        "source_path": source_path,
                        "source_type": "doc",
                    }
                ],
                "working_tree_state": "unavailable",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    chunks_path = root / _CHUNKS_JSONL
    chunks_path.write_text(
        json.dumps(chunk, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    events_dir = root / "events"
    events_dir.mkdir(parents=True, exist_ok=True)
    (events_dir / "workflow.jsonl").write_text(
        json.dumps(
            {
                "id": "memory-workflow-smoke-event",
                "event_type": "memory.workflow.smoke",
                "event_family": "memory",
                "severity": "info",
                "occurred_at": "2026-07-05T00:00:00Z",
                "source_refs": [_DAILY_WORKFLOW_MD],
                "payload": {"surface": "memory.tooling.workflow"},
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return chunks_path, events_dir


def _inject_smoke_provenance_env() -> dict[str, str | None]:
    """Install smoke-only actor identity; return previous env values to restore.

    Also forces ``BIOETL_AI_MEMORY_MODE=read-write`` for the smoke duration so
    temporary session/summary notes under ``TemporaryDirectory`` can be written
    even when the caller shell is set to ``read-only`` or ``off``. Production
    ``pre-task`` / ``post-task`` CLI paths never call this helper.
    """
    previous: dict[str, str | None] = {}
    for key in _SMOKE_PROVENANCE_ENV:
        previous[key] = os.environ.get(key)
    os.environ["BIOETL_AI_RUNTIME"] = _SMOKE_RUNTIME
    os.environ["BIOETL_AI_AGENT"] = _SMOKE_AGENT
    os.environ["BIOETL_AI_MEMORY_MODE"] = _SMOKE_MEMORY_MODE
    return previous


def _restore_provenance_env(previous: dict[str, str | None]) -> None:
    """Restore actor-identity env keys to their pre-smoke values."""
    for key, value in previous.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def smoke_workflow(
    *,
    validation_timeout_seconds: float
    | None = DEFAULT_POST_TASK_VALIDATION_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Run a lightweight pre/post workflow smoke without committing artifacts.

    Injects deterministic non-production provenance
    (``BIOETL_AI_RUNTIME=smoke``, ``BIOETL_AI_AGENT=memory-workflow-smoke``)
    and temporary ``BIOETL_AI_MEMORY_MODE=read-write`` for the smoke run only,
    then restores the previous environment. Production ``pre-task`` /
    ``post-task`` paths remain fail-closed on missing identity and honour the
    caller's persistence mode.
    """
    repo_root = _discover_repo_root() or Path(__file__).resolve().parents[3]
    previous_env = _inject_smoke_provenance_env()
    try:
        with ExitStack() as stack:
            temp_root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
            chunks_path, events_dir = _write_smoke_inputs(temp_root)
            session_note_path = temp_root / "session.md"
            summary_note_path = temp_root / "summary.md"
            pre_payload = pre_task_workflow(
                task_id="memory-workflow-smoke",
                title=_MEMORY_WORKFLOW_SMOKE_TITLE,
                query="memory workflow",
                source_refs=[_DAILY_WORKFLOW_MD],
                create_session_note=True,
                session_note_path=session_note_path,
                chunks_path=chunks_path,
                events_dir=events_dir,
                run_refresh_if_missing=False,
                limit=3,
                profile=DEFAULT_PROFILE,
            )
            post_payload = post_task_workflow(
                task_id="memory-workflow-smoke",
                title=_MEMORY_WORKFLOW_SMOKE_TITLE,
                summary="Validated lightweight memory workflow pre/post smoke.",
                source_refs=[_DAILY_WORKFLOW_MD],
                run_refresh=False,
                summary_note_path=summary_note_path,
                validation_timeout_seconds=validation_timeout_seconds,
            )
            # Check file existence before context manager exits
            session_exists = session_note_path.exists()
            summary_exists = summary_note_path.exists()
            ok = bool(
                pre_payload.get("ok")
                and post_payload.get("ok")
                and session_exists
                and summary_exists
            )
            return {
                "kind": "smoke",
                "ok": ok,
                "python_executable": sys.executable,
                "repo_root": str(repo_root),
                "actor": {
                    "runtime": _SMOKE_RUNTIME,
                    "agent": _SMOKE_AGENT,
                },
                "pre_task_ok": bool(pre_payload.get("ok")),
                "post_task_ok": bool(post_payload.get("ok")),
                "post_task_degraded": bool(post_payload.get("degraded", False)),
                "post_task_validation_status": post_payload.get(
                    "validation_status", "completed"
                ),
                "generated_artifacts": "temporary_directory_removed",
            }
    finally:
        _restore_provenance_env(previous_env)


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
    pre_parser.add_argument(
        "--profile",
        default=DEFAULT_PROFILE,
        help="Task retrieval profile (validated at runtime).",
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
        "--validation-timeout-seconds",
        type=float,
        default=DEFAULT_POST_TASK_VALIDATION_TIMEOUT_SECONDS,
        help=(
            "Timeout for memory validation before returning a degraded payload; "
            "set to 0 to disable the timeout."
        ),
    )
    post_parser.add_argument(
        "--refresh-timeout-seconds",
        type=float,
        default=DEFAULT_POST_TASK_REFRESH_TIMEOUT_SECONDS,
        help=(
            "Timeout for post-task refresh before returning a degraded payload; "
            "set to 0 to run refresh in-process without the subprocess timeout."
        ),
    )
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

    smoke_parser = subparsers.add_parser(
        "smoke",
        help="Run a lightweight deterministic pre/post workflow smoke.",
    )
    smoke_parser.add_argument(
        "--validation-timeout-seconds",
        type=float,
        default=DEFAULT_POST_TASK_VALIDATION_TIMEOUT_SECONDS,
    )
    smoke_parser.add_argument("--json", action="store_true")

    return parser


def _payload_exit_code(payload: dict[str, Any]) -> int:
    return 0 if payload.get("ok", True) else 1


def _emit_json(payload: dict[str, Any]) -> int:
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True))
    return _payload_exit_code(payload)


def _emit_pre_task_text(payload: dict[str, Any]) -> None:
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


def _emit_post_task_text(payload: dict[str, Any]) -> None:
    print(f"Post-task workflow: {payload['task_id']}")
    if payload.get("summary_note"):
        print(f"- summary note: {payload['summary_note']}")
    else:
        print("- summary note: disabled by persistence mode")
    if payload.get("refresh_output_root"):
        print(f"- refresh output root: {payload['refresh_output_root']}")
    if payload.get("promoted_note"):
        print(f"- promoted note: {payload['promoted_note']}")
    if not payload.get("degraded"):
        return
    validation_status = payload.get("validation_status")
    if validation_status:
        print(f"- degraded: validation did not complete ({validation_status})")
        return
    print("- degraded: refresh completed with partial artifact failures")


def _emit(payload: dict[str, Any], *, as_json: bool) -> int:
    if as_json:
        return _emit_json(payload)
    if payload["kind"] == "pre-task":
        _emit_pre_task_text(payload)
    else:
        _emit_post_task_text(payload)
    return _payload_exit_code(payload)


def _run_pre_task_command(args: argparse.Namespace) -> int:
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


def _run_post_task_command(args: argparse.Namespace) -> int:
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
        validation_timeout_seconds=args.validation_timeout_seconds,
        refresh_timeout_seconds=args.refresh_timeout_seconds,
    )
    return _emit(payload, as_json=args.json)


def _emit_smoke_text(payload: dict[str, Any]) -> None:
    print(f"{_MEMORY_WORKFLOW_SMOKE_TITLE}:")
    print(f"- python: {payload['python_executable']}")
    print(f"- pre-task: {'ok' if payload['pre_task_ok'] else 'failed'}")
    print(f"- post-task: {'ok' if payload['post_task_ok'] else 'failed'}")
    if payload.get("post_task_degraded"):
        print(
            "- post-task degraded: "
            f"{payload.get('post_task_validation_status', 'unknown')}"
        )


def _run_smoke_command(args: argparse.Namespace) -> int:
    payload = smoke_workflow(
        validation_timeout_seconds=args.validation_timeout_seconds,
    )
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return _payload_exit_code(payload)
    _emit_smoke_text(payload)
    return _payload_exit_code(payload)


def _emit_review_curated_text(payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    print("Curated review ritual:")
    print(f"- notes: {summary['note_count']}")
    print(f"- due: {summary['due_count']}")
    print(f"- stale: {summary['stale_count']}")
    print(f"- review candidates: {summary['review_candidates']}")
    print(f"- cadence: {payload['cadence']}")
    print(f"- next action: {payload['next_action']}")


def _run_review_curated_command(args: argparse.Namespace) -> int:
    payload = review_curated_workflow(curated_root=args.root)
    if args.json:
        return _emit_json(payload)
    _emit_review_curated_text(payload)
    return _payload_exit_code(payload)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    handlers = {
        "pre-task": _run_pre_task_command,
        "post-task": _run_post_task_command,
        "smoke": _run_smoke_command,
        "review-curated": _run_review_curated_command,
    }
    handler = handlers.get(args.command)
    if handler is None:
        parser.error(f"unsupported command: {args.command}")
        return 2
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
