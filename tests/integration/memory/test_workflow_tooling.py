# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Integration tests for the daily memory workflow tooling."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from memory.notes import parse_markdown_note
from memory.tooling import workflow
from tests.helpers.memory_manifests import write_test_rag_manifest


@pytest.fixture(autouse=True)
def _explicit_actor_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BIOETL_AI_RUNTIME", "test-runtime")
    monkeypatch.setenv("BIOETL_AI_AGENT", "test-agent")


def test_pre_task_off_mode_performs_no_persistent_read_or_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BIOETL_AI_MEMORY_MODE", "off")
    monkeypatch.setattr(
        workflow,
        "_resolve_pre_task_surfaces",
        lambda **_: pytest.fail("off mode must not resolve persistent surfaces"),
    )

    payload = workflow.pre_task_workflow(
        task_id="off-task",
        title="No persistent memory",
        query=None,
        source_refs=[],
    )

    assert payload["persistence_mode"] == "off"
    assert payload["session_note"] is None
    assert payload["retrieval"]["kind"] == "disabled"


pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    "missing_variable",
    ["BIOETL_AI_RUNTIME", "BIOETL_AI_AGENT"],
)
def test_pre_task_rejects_missing_actor_identity_before_durable_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    missing_variable: str,
) -> None:
    monkeypatch.delenv(missing_variable)

    with pytest.raises(ValueError, match=missing_variable):
        workflow.pre_task_workflow(
            task_id="missing-actor",
            title="Missing actor",
            query=None,
            source_refs=["src/memory/README.md"],
            session_note_path=tmp_path / "session.md",
            run_refresh_if_missing=False,
        )

    assert not (tmp_path / "session.md").exists()


def test_pre_task_workflow_creates_session_note_and_uses_local_surfaces(
    tmp_path: Path,
) -> None:
    chunks_path = tmp_path / "chunks.jsonl"
    write_test_rag_manifest(
        chunks_path,
        [
            {
                "id": "chunk-1",
                "title": "Pipeline",
                "content": "chembl_activity pipeline",
                "source_path": "src/bioetl/application/service.py",
                "source_type": "code",
                "domain": "runtime",
                "repo_zone": "canonical_runtime",
                "symbol_kind": "function",
            }
        ],
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
        profile="audit",
    )

    assert payload["kind"] == "pre-task"
    assert payload["ok"] is True
    assert payload["refresh_report"] is None
    assert session_note_path.exists()
    assert len(payload["retrieval"]["results"]["rag"]) == 1
    assert len(payload["retrieval"]["results"]["timeline"]) == 1
    assert payload["retrieval"]["profile"] == "audit"

    note = parse_markdown_note(session_note_path)
    assert note.metadata["task_id"] == "task-chembl-memory"
    assert note.metadata["confidence"] == "episodic"
    assert note.metadata["query"] == "chembl_activity"


def test_emit_returns_nonzero_for_failed_payload(capsys) -> None:
    exit_code = workflow._emit({"kind": "diagnostic", "ok": False}, as_json=True)

    assert exit_code == 1
    assert '"ok": false' in capsys.readouterr().out


def test_pre_task_workflow_refreshes_if_manifests_are_missing(
    tmp_path: Path, monkeypatch
) -> None:
    refresh_calls: list[tuple[Path, Path]] = []
    session_note_path = tmp_path / "session-refresh.md"

    def _fake_refresh_all(
        root: Path,
        output_root: Path,
        *,
        include_rag: bool = True,
        include_timeline: bool = True,
        include_graph_export: bool = False,
        rag_build_scope: str = "full",
        rag_focus_query: str | None = None,
        rag_max_sources: int | None = None,
        allow_partial: bool = False,
    ) -> dict[str, object]:
        refresh_calls.append((root, output_root))
        assert include_rag is True
        assert include_timeline is True
        assert rag_build_scope == "workflow"
        assert rag_focus_query == "Refresh before retrieval"
        assert rag_max_sources == 160
        assert allow_partial is True
        rag_dir = output_root / "rag" / "manifests"
        write_test_rag_manifest(
            rag_dir / "chunks.jsonl",
            [
                {
                    "id": "chunk-1",
                    "title": "Refresh result",
                    "content": "refresh before retrieval workflow memory",
                    "source_path": "docs/00-project/overview.md",
                    "source_type": "doc",
                    "domain": "project",
                    "repo_zone": "canonical_project_docs",
                    "symbol_kind": "markdown_section",
                }
            ],
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
        session_note_path=session_note_path,
        refresh_output_root=tmp_path / "refresh",
        limit=5,
    )

    assert refresh_calls
    assert payload["refresh_output_root"] == str(tmp_path / "refresh")
    assert payload["ok"] is True
    assert payload["refresh_report"] == {"ok": True, "artifacts": []}
    assert len(payload["retrieval"]["results"]["rag"]) == 1


def test_pre_task_read_only_refreshes_only_into_temporary_root(
    tmp_path: Path, monkeypatch
) -> None:
    requested_root = tmp_path / "must-not-be-used"
    refresh_roots: list[Path] = []

    def _fake_refresh_all(
        root: Path,
        output_root: Path,
        **kwargs: object,
    ) -> dict[str, object]:
        refresh_roots.append(output_root)
        assert output_root != requested_root
        rag_dir = output_root / "rag" / "manifests"
        write_test_rag_manifest(
            rag_dir / "chunks.jsonl",
            [
                {
                    "id": "chunk-read-only",
                    "title": "Read-only result",
                    "content": "bounded temporary refresh",
                    "source_path": "src/memory/DAILY_WORKFLOW.md",
                    "source_type": "doc",
                    "domain": "project",
                    "repo_zone": "canonical_project_docs",
                    "symbol_kind": "markdown_section",
                }
            ],
        )
        events_dir = output_root / "timeline" / "events"
        events_dir.mkdir(parents=True, exist_ok=True)
        (events_dir / "runs.jsonl").write_text(
            json.dumps(
                {
                    "id": "read-only-run",
                    "event_type": "run.manifest_registered",
                    "event_family": "run",
                    "severity": "info",
                    "occurred_at": "2026-07-30T00:00:00Z",
                    "source_refs": ["src/memory/DAILY_WORKFLOW.md"],
                    "payload": {"pipeline_name": "bounded temporary refresh"},
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return {"ok": True, "artifacts": []}

    monkeypatch.setenv("BIOETL_AI_MEMORY_MODE", "read-only")
    monkeypatch.setattr(workflow, "refresh_all", _fake_refresh_all)

    payload = workflow.pre_task_workflow(
        task_id="read-only-refresh",
        title="Read-only refresh",
        query="bounded temporary refresh",
        source_refs=[],
        refresh_output_root=requested_root,
        limit=5,
    )

    assert payload["ok"] is True
    assert payload["session_note"] is None
    assert refresh_roots
    assert not requested_root.exists()
    assert payload["refresh_output_root"] == str(refresh_roots[0])


def test_pre_task_workflow_skip_refresh_if_missing_preserves_catalog_results(
    tmp_path: Path,
) -> None:
    session_note_path = tmp_path / "session.md"

    payload = workflow.pre_task_workflow(
        task_id="task-skip-missing",
        title="Skip missing memory artifacts",
        query="sources",
        source_refs=["src/memory/README.md"],
        session_note_path=session_note_path,
        chunks_path=tmp_path / "missing-rag" / "chunks.jsonl",
        events_dir=tmp_path / "missing-timeline",
        run_refresh_if_missing=False,
        limit=5,
        profile="implementation",
    )

    assert payload["kind"] == "pre-task"
    assert payload["ok"] is False
    assert payload["refresh_report"] is None
    assert payload["retrieval"]["degraded"] is True
    assert payload["retrieval"]["profile"] == "implementation"
    assert payload["retrieval"]["results"]["catalog"]
    assert payload["retrieval"]["results"]["rag"] == []
    assert payload["retrieval"]["results"]["timeline"] == []
    assert [
        artifact["kind"] for artifact in payload["retrieval"]["missing_artifacts"]
    ] == ["rag_chunks", "timeline_events"]
    assert session_note_path.exists()


def test_pre_task_workflow_degraded_payload_returns_nonzero_exit_code() -> None:
    payload = {
        "kind": "pre-task",
        "task_id": "task-degraded",
        "ok": False,
        "retrieval": {
            "degraded": True,
            "results": {"catalog": [], "rag": [], "timeline": []},
        },
    }

    assert workflow._emit(payload, as_json=False) == 1


def test_pre_task_workflow_refreshes_if_event_projection_dir_is_empty(
    tmp_path: Path, monkeypatch
) -> None:
    refresh_calls: list[Path] = []
    session_note_path = tmp_path / "session-empty-events.md"
    chunks_path = tmp_path / "chunks.jsonl"
    write_test_rag_manifest(
        chunks_path,
        [
            {
                "id": "chunk-1",
                "title": "Local chunk",
                "content": "workflow memory",
                "source_path": "src/memory/query.py",
                "source_type": "code",
                "domain": "memory",
                "repo_zone": "canonical_runtime",
                "symbol_kind": "function",
            }
        ],
    )
    events_dir = tmp_path / "events"
    events_dir.mkdir()
    (events_dir / "README.md").write_text("Timeline projections live here.\n")

    def _fake_refresh_all(
        root: Path,
        output_root: Path,
        *,
        include_rag: bool = True,
        include_timeline: bool = True,
        include_graph_export: bool = False,
        rag_build_scope: str = "full",
        rag_focus_query: str | None = None,
        rag_max_sources: int | None = None,
        allow_partial: bool = False,
    ) -> dict[str, object]:
        refresh_calls.append(output_root)
        assert include_rag is False
        assert include_timeline is True
        assert rag_build_scope == "workflow"
        assert rag_focus_query == "workflow memory"
        assert rag_max_sources == 160
        assert allow_partial is True
        rag_dir = output_root / "rag" / "manifests"
        write_test_rag_manifest(
            rag_dir / "chunks.jsonl",
            [
                json.loads(line)
                for line in chunks_path.read_text(encoding="utf-8").splitlines()
            ],
        )
        refreshed_events = output_root / "timeline" / "events"
        refreshed_events.mkdir(parents=True, exist_ok=True)
        (refreshed_events / "runs.jsonl").write_text(
            json.dumps(
                {
                    "id": "run-1",
                    "event_type": "run.completed",
                    "event_family": "run",
                    "severity": "info",
                    "occurred_at": "2026-04-20T00:00:00Z",
                    "source_refs": ["data/output/control/run_manifest/m1.json"],
                    "payload": {"pipeline_name": "workflow memory"},
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return {"ok": True, "artifacts": []}

    monkeypatch.setattr(workflow, "refresh_all", _fake_refresh_all)

    payload = workflow.pre_task_workflow(
        task_id="task-empty-events",
        title="Refresh empty events",
        query="workflow memory",
        source_refs=["src/memory/README.md"],
        session_note_path=session_note_path,
        refresh_output_root=tmp_path / "refresh",
        chunks_path=chunks_path,
        events_dir=events_dir,
        limit=5,
    )

    assert refresh_calls == [tmp_path / "refresh"]
    assert payload["refresh_output_root"] == str(tmp_path / "refresh")
    assert len(payload["retrieval"]["results"]["timeline"]) == 1


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
        rag_build_scope: str = "full",
        rag_focus_query: str | None = None,
        rag_max_sources: int | None = None,
        allow_partial: bool = False,
    ) -> dict[str, object]:
        refresh_calls.append((root, output_root))
        assert include_rag is True
        assert include_timeline is True
        assert rag_build_scope == "workflow"
        assert rag_focus_query == "Wire memory into daily engineering"
        assert rag_max_sources == 160
        assert allow_partial is True
        return {"ok": True, "artifacts": [{"kind": "rag"}]}

    def _fake_prune(*, apply: bool = False) -> dict[str, object]:
        prune_calls.append(apply)
        return {"apply": apply, "candidate_count": 0, "removed_count": 0}

    def _fake_promote_note(
        source: Path,
        *,
        target_kind: str,
        summary: str,
        move: bool = False,
    ) -> Path:
        target = tmp_path / "curated" / f"{target_kind}.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        promoted_targets.append(target)
        assert summary == "Completed the daily workflow integration."
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
        validation_timeout_seconds=0,
    )

    assert payload["ok"] is True
    assert payload["degraded"] is False
    assert summary_note_path.exists()
    assert refresh_calls
    assert prune_calls == [False]
    assert promoted_targets
    assert payload["promoted_note"] == str(promoted_targets[0])

    note = parse_markdown_note(summary_note_path)
    assert note.metadata["task_id"] == "task-summary"
    assert note.metadata["confidence"] == "episodic"


def test_post_task_workflow_returns_degraded_payload_when_validation_times_out(
    tmp_path: Path,
    monkeypatch,
) -> None:
    def _fake_validation_runner(
        *,
        timeout_seconds: float | None,
        repo_root: Path,
    ) -> dict[str, object]:
        assert timeout_seconds == 15.0
        assert repo_root.exists()
        return {
            "status": "timed_out",
            "issues": [],
            "timeout_seconds": 15.0,
        }

    monkeypatch.setattr(workflow, "_run_post_task_validation", _fake_validation_runner)

    summary_note_path = tmp_path / "summary-timeout.md"
    payload = workflow.post_task_workflow(
        task_id="task-timeout",
        title="Timeout during memory validation",
        summary="Summary note should still be written.",
        source_refs=["src/memory/README.md"],
        summary_note_path=summary_note_path,
        validation_timeout_seconds=15.0,
    )

    assert payload == {
        "kind": "post-task",
        "task_id": "task-timeout",
        "title": "Timeout during memory validation",
        "summary_note": str(summary_note_path),
        "ok": False,
        "degraded": True,
        "validation_status": "timed_out",
        "validation_issues": [],
        "validation_timeout_seconds": 15.0,
    }
    assert summary_note_path.exists()


def test_post_task_workflow_timeout_payload_returns_nonzero_exit_code() -> None:
    payload = {
        "kind": "post-task",
        "task_id": "task-timeout",
        "summary_note": "summary.md",
        "ok": False,
        "degraded": True,
        "validation_status": "timed_out",
    }

    assert workflow._emit(payload, as_json=False) == 1


def test_post_task_cli_parser_uses_bounded_refresh_timeout_default() -> None:
    args = workflow._build_parser().parse_args(
        [
            "post-task",
            "--task-id",
            "task-refresh-default",
            "--title",
            "Refresh default",
            "--summary",
            "Verify the configured refresh timeout default.",
        ]
    )

    assert (
        args.refresh_timeout_seconds
        == workflow.DEFAULT_POST_TASK_REFRESH_TIMEOUT_SECONDS
        == 120.0
    )


def test_post_task_workflow_returns_degraded_payload_when_refresh_times_out(
    tmp_path: Path,
    monkeypatch,
) -> None:
    def _fake_validation_runner(
        *,
        timeout_seconds: float | None,
        repo_root: Path,
    ) -> dict[str, object]:
        return {"status": "completed", "issues": []}

    def _fake_subprocess_run(*args: object, **kwargs: object) -> object:
        raise subprocess.TimeoutExpired(
            cmd=kwargs.get("args", ["memory.tooling.refresh_all"]),
            timeout=kwargs.get("timeout", 0.01),
        )

    monkeypatch.setattr(workflow, "_run_post_task_validation", _fake_validation_runner)
    monkeypatch.setattr(workflow.subprocess, "run", _fake_subprocess_run)

    summary_note_path = tmp_path / "summary-refresh-timeout.md"
    payload = workflow.post_task_workflow(
        task_id="task-refresh-timeout",
        title="Bounded post-task refresh",
        summary="Summary note should still be written.",
        source_refs=["src/memory/README.md"],
        refresh_output_root=tmp_path / "refresh",
        summary_note_path=summary_note_path,
        validation_timeout_seconds=15.0,
        refresh_timeout_seconds=0.01,
    )

    assert payload["ok"] is True
    assert payload["degraded"] is True
    assert payload["refresh_report"]["status"] == "timed_out"
    assert payload["refresh_report"]["timeout_seconds"] == 0.01
    assert summary_note_path.exists()


def test_smoke_workflow_exercises_pre_and_post_without_persistent_refresh(
    monkeypatch,
) -> None:
    monkeypatch.setattr(workflow, "validate_memory_scaffold", lambda: [])

    payload = workflow.smoke_workflow(validation_timeout_seconds=0)

    assert payload["kind"] == "smoke"
    assert payload["ok"] is True
    assert payload["pre_task_ok"] is True
    assert payload["post_task_ok"] is True
    assert payload["post_task_validation_status"] == "completed"
    assert payload["generated_artifacts"] == "temporary_directory_removed"
    assert payload["actor"] == {
        "runtime": workflow._SMOKE_RUNTIME,
        "agent": workflow._SMOKE_AGENT,
    }


def test_smoke_workflow_injects_provenance_when_env_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Smoke must not require manual BIOETL_AI_* env (AI-MEM-C1-001 / #7484)."""
    monkeypatch.delenv("BIOETL_AI_RUNTIME", raising=False)
    monkeypatch.delenv("BIOETL_AI_AGENT", raising=False)
    monkeypatch.setattr(workflow, "validate_memory_scaffold", lambda: [])

    payload = workflow.smoke_workflow(validation_timeout_seconds=0)

    assert payload["ok"] is True
    assert payload["actor"]["runtime"] == "smoke"
    assert payload["actor"]["agent"] == "memory-workflow-smoke"
    # Smoke must restore caller environment (no leak of smoke identity).
    assert "BIOETL_AI_RUNTIME" not in os.environ
    assert "BIOETL_AI_AGENT" not in os.environ


def test_smoke_workflow_restores_caller_provenance_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BIOETL_AI_RUNTIME", "caller-runtime")
    monkeypatch.setenv("BIOETL_AI_AGENT", "caller-agent")
    monkeypatch.setenv("BIOETL_AI_MEMORY_MODE", "read-only")
    monkeypatch.setattr(workflow, "validate_memory_scaffold", lambda: [])

    payload = workflow.smoke_workflow(validation_timeout_seconds=0)

    assert payload["ok"] is True
    assert os.environ["BIOETL_AI_RUNTIME"] == "caller-runtime"
    assert os.environ["BIOETL_AI_AGENT"] == "caller-agent"
    assert os.environ["BIOETL_AI_MEMORY_MODE"] == "read-only"


def test_smoke_workflow_succeeds_when_ambient_memory_mode_is_read_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Smoke must write temp notes even if shell default is read-only."""
    monkeypatch.setenv("BIOETL_AI_MEMORY_MODE", "read-only")
    monkeypatch.setattr(workflow, "validate_memory_scaffold", lambda: [])

    payload = workflow.smoke_workflow(validation_timeout_seconds=0)

    assert payload["ok"] is True
    assert payload["pre_task_ok"] is True
    assert payload["post_task_ok"] is True
    assert os.environ["BIOETL_AI_MEMORY_MODE"] == "read-only"


def test_compact_prune_report_accepts_minimal_stub_payload() -> None:
    report = workflow._compact_prune_report(
        {
            "apply": False,
            "candidate_count": 0,
            "removed_count": 0,
        }
    )

    assert report == {
        "apply": False,
        "candidate_count": 0,
        "removed_count": 0,
    }


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
