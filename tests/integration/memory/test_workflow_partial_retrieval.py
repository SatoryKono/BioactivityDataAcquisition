"""Strict pre-task reads preserve a healthy layer during partial degradation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from memory.tooling.workflow import pre_task_workflow
from tests.helpers.memory_manifests import write_test_rag_manifest

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("rag_ready", [False, True])
@pytest.mark.parametrize("timeline_ready", [False, True])
def test_read_only_pre_task_preserves_available_layers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    rag_ready: bool,
    timeline_ready: bool,
) -> None:
    monkeypatch.setenv("BIOETL_AI_MEMORY_MODE", "read-only")
    monkeypatch.setenv("BIOETL_AI_RUNTIME", "test-runtime")
    monkeypatch.setenv("BIOETL_AI_AGENT", "test-agent")
    chunks = tmp_path / "rag" / "chunks.jsonl"
    events = tmp_path / "events"
    if rag_ready:
        write_test_rag_manifest(
            chunks,
            [
                {
                    "id": "chunk-1",
                    "content": "memory_subsystem",
                    "source_path": "src/memory/query.py",
                    "source_type": "code",
                }
            ],
        )
    if timeline_ready:
        events.mkdir()
        (events / "runs.jsonl").write_text(
            json.dumps(
                {
                    "id": "run-1",
                    "event_family": "run",
                    "event_type": "run.completed",
                    "payload": {"pipeline_name": "memory_subsystem"},
                }
            )
            + "\n",
            encoding="utf-8",
        )
    before = sorted(tmp_path.rglob("*"))

    result = pre_task_workflow(
        task_id="partial-context",
        title="Read partial context",
        query="memory_subsystem",
        source_refs=[],
        chunks_path=chunks,
        events_dir=events,
        create_session_note=False,
        run_refresh_if_missing=False,
        limit=1,
    )

    assert result["ok"] is (rag_ready and timeline_ready)
    assert bool(result["retrieval"]["results"]["rag"]) is rag_ready
    assert bool(result["retrieval"]["results"]["timeline"]) is timeline_ready
    assert result["retrieval"]["results"]["catalog"]
    assert result["session_note"] is None
    assert result["refresh_report"] is None
    assert sorted(tmp_path.rglob("*")) == before
