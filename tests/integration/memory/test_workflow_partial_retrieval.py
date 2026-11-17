"""Strict pre-task reads preserve a healthy layer during partial degradation."""

from __future__ import annotations

from pathlib import Path

import pytest

from memory.tooling.workflow import pre_task_workflow
from tests.helpers.memory_manifests import (
    snapshot_test_memory_artifacts,
    write_test_retrieval_layers,
)

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
    chunks, events = write_test_retrieval_layers(
        tmp_path, rag_ready=rag_ready, timeline_ready=timeline_ready
    )
    before = snapshot_test_memory_artifacts(tmp_path)

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
    assert snapshot_test_memory_artifacts(tmp_path) == before
