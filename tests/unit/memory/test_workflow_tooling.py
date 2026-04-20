"""Tests for the daily memory workflow tooling."""

from __future__ import annotations

import json
from pathlib import Path

from memory.notes import parse_markdown_note
from memory.tooling import workflow


def test_pre_task_workflow_creates_session_note_and_uses_local_surfaces(tmp_path: Path) -> None:
    chunks_path = tmp_path / "chunks.jsonl"
    chunks_path.write_text(
        json.dumps(
            {
                "id": "chunk-1",
                "title": "Pipeline",
                "content": "chembl_activity pipeline",
                "source_path": "src/bioetl/application/service.py",
                "source_type": "code",
                "domain": "runtime",
                "repo_zone": "canonical_runtime",
                "symbol_kind": "function",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    events_dir = tmp_path / "events"
    events_dir.mkdir()
    (events_dir / "runs.jsonl").write_text(
        json.dumps(
            {
                "id": "run-1",
                "event_type": "run.manifest_registered",
                "event_family": "run",
                "severity": "info",
                "occurred_at": "2026-04-20T00:00:00Z",
                "source_refs": ["data/output/control/run_manifest/m1.json"],
                "payload": {"pipeline_name": "chembl_activity"},
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    session_note_path = tmp_path / "session.md"

    payload = workflow.pre_task_workflow(
        task_id="task-chembl-memory",
        title="Investigate chembl activity memory flow",
        query="chembl_activity",
        source_refs=["src/memory/README.md"],
        session_note_path=session_note_path,
        chunks_path=chunks_path,
        events_dir=events_dir,
        run_refresh_if_missing=False,
        limit=5,
    )

    assert payload["kind"] == "pre-task"
    assert payload["refresh_report"] is None
    assert session_note_path.exists()
    assert len(payload["retrieval"]["results"]["rag"]) == 1
    assert len(payload["retrieval"]["results"]["timeline"]) == 1

    note = parse_markdown_note(session_note_path)
    assert note.metadata["task_id"] == "task-chembl-memory"
    assert note.metadata["confidence"] == "episodic"
    assert note.metadata["query"] == "chembl_activity"


def test_pre_task_workflow_refreshes_if_manifests_are_missing(tmp_path: Path, monkeypatch) -> None:
    refresh_calls: list[tuple[Path, Path]] = []

    def _fake_refresh_all(
        root: Path,
        output_root: Path,
        *,
        include_rag: bool = True,
        include_timeline: bool = True,
        include_graph_export: bool = False,
    ) -> dict[str, object]:
        refresh_calls.append((root, output_root))
        rag_dir = output_root / "rag" / "manifests"
        rag_dir.mkdir(parents=True, exist_ok=True)
        (rag_dir / "chunks.jsonl").write_text(
            json.dumps(
                {
                    "id": "chunk-1",
                    "title": "Refresh result",
                    "content": "refresh before retrieval workflow memory",
                    "source_path": "docs/00-project/overview.md",
                    "source_type": "doc",
                    "domain": "project",
                    "repo_zone": "canonical_project_docs",
                    "symbol_kind": "markdown_section",
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        events_dir = output_root / "timeline" / "events"
        events_dir.mkdir(parents=True, exist_ok=True)
        (events_dir / "runs.jsonl").write_text(
            json.dumps(
                {
                    "id": "run-1",
                    "event_type": "run.manifest_registered",
                    "event_family": "run",
                    "severity": "info",
                    "occurred_at": "2026-04-20T00:00:00Z",
                    "source_refs": ["data/output/control/run_manifest/m1.json"],
                    "payload": {"pipeline_name": "refresh before retrieval"},
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return {"ok": True, "artifacts": []}

    monkeypatch.setattr(workflow, "refresh_all", _fake_refresh_all)

    payload = workflow.pre_task_workflow(
        task_id="task-refresh",
        title="Refresh before retrieval",
        query=None,
        source_refs=["src/memory/README.md"],
        refresh_output_root=tmp_path / "refresh",
        limit=5,
    )

    assert refresh_calls
    assert payload["refresh_output_root"] == str(tmp_path / "refresh")
    assert payload["refresh_report"] == {"ok": True, "artifacts": []}
    assert len(payload["retrieval"]["results"]["rag"]) == 1


def test_post_task_workflow_writes_summary_and_promotes_note(
    tmp_path: Path, monkeypatch
) -> None:
    refresh_calls: list[tuple[Path, Path]] = []
    prune_calls: list[bool] = []
    promoted_targets: list[Path] = []

    def _fake_validate() -> list[object]:
        return []

    def _fake_refresh_all(
        root: Path,
        output_root: Path,
        *,
        include_rag: bool = True,
        include_timeline: bool = True,
        include_graph_export: bool = False,
    ) -> dict[str, object]:
        refresh_calls.append((root, output_root))
        return {"ok": True, "artifacts": [{"kind": "rag"}]}

    def _fake_prune(*, apply: bool = False) -> dict[str, object]:
        prune_calls.append(apply)
        return {"apply": apply, "candidate_count": 0, "removed_count": 0}

    def _fake_promote_note(source: Path, *, target_kind: str, move: bool = False) -> Path:
        target = tmp_path / "curated" / f"{target_kind}.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        promoted_targets.append(target)
        return target

    monkeypatch.setattr(workflow, "validate_memory_scaffold", _fake_validate)
    monkeypatch.setattr(workflow, "refresh_all", _fake_refresh_all)
    monkeypatch.setattr(workflow, "prune_episodic_notes", _fake_prune)
    monkeypatch.setattr(workflow, "promote_note", _fake_promote_note)

    summary_note_path = tmp_path / "summary.md"
    payload = workflow.post_task_workflow(
        task_id="task-summary",
        title="Wire memory into daily engineering",
        summary="Completed the daily workflow integration.",
        source_refs=["src/memory/README.md"],
        refresh_output_root=tmp_path / "refresh",
        summary_note_path=summary_note_path,
        run_prune=True,
        promote_to="lesson",
    )

    assert payload["ok"] is True
    assert summary_note_path.exists()
    assert refresh_calls
    assert prune_calls == [False]
    assert promoted_targets
    assert payload["promoted_note"] == str(promoted_targets[0])

    note = parse_markdown_note(summary_note_path)
    assert note.metadata["task_id"] == "task-summary"
    assert note.metadata["confidence"] == "episodic"


def test_review_curated_workflow_returns_ritual_summary(monkeypatch) -> None:
    def _fake_review(root: Path | None = None) -> dict[str, object]:
        return {
            "ok": True,
            "kind": "curated_review",
            "summary": {
                "note_count": 3,
                "current_count": 1,
                "due_count": 1,
                "stale_count": 1,
                "review_every_days": 30,
                "review_candidates": 2,
            },
            "records": [
                {
                    "path": "src/memory/curated/lessons/example.md",
                    "review_status": "due",
                    "recommendation": "review",
                }
            ],
        }

    monkeypatch.setattr(workflow, "review_curated_notes", _fake_review)

    payload = workflow.review_curated_workflow()

    assert payload["kind"] == "review-curated"
    assert payload["ok"] is True
    assert payload["summary"]["review_candidates"] == 2
    assert "regular engineering cadence" in payload["cadence"]
    assert "archive" in payload["next_action"]
