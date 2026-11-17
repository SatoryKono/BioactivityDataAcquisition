"""Combined retrieval keeps healthy layers without rebuilding missing ones."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import memory.query as memory_query
from memory.query import main, query_all
from tests.helpers.memory_manifests import write_test_retrieval_layers

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("rag_ready", [False, True])
@pytest.mark.parametrize("timeline_ready", [False, True])
def test_all_preserves_available_layers_without_refresh(
    tmp_path: Path, rag_ready: bool, timeline_ready: bool
) -> None:
    chunks, events = write_test_retrieval_layers(
        tmp_path, rag_ready=rag_ready, timeline_ready=timeline_ready
    )
    before = sorted(tmp_path.rglob("*"))

    payload = query_all(
        query="memory_subsystem",
        chunks_path=chunks,
        events_dir=events,
        auto_refresh=False,
        limit=1,
    )

    assert bool(payload["results"]["rag"]) is rag_ready
    assert bool(payload["results"]["timeline"]) is timeline_ready
    assert payload["results"]["catalog"]
    assert payload["degraded"] is not (rag_ready and timeline_ready)
    assert {item["kind"] for item in payload["missing_artifacts"]} == (
        ({"rag_chunks"} if not rag_ready else set())
        | ({"timeline_events"} if not timeline_ready else set())
    )
    assert payload["refresh_report"] is None
    assert sorted(tmp_path.rglob("*")) == before


def test_all_cli_reports_degradation_as_json_with_nonzero_exit(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(
        [
            "all",
            "memory_subsystem",
            "--chunks-path",
            str(tmp_path / "chunks.jsonl"),
            "--events-dir",
            str(tmp_path / "events"),
            "--json",
        ]
    )

    output = capsys.readouterr()
    assert code == 1
    assert output.err == ""
    assert json.loads(output.out)["degraded"] is True


def test_invalid_rag_pair_does_not_hide_healthy_timeline(tmp_path: Path) -> None:
    chunks, events = write_test_retrieval_layers(
        tmp_path, rag_ready=True, timeline_ready=True, query="memory"
    )
    chunks.write_text('{"content": "unverified"}\n', encoding="utf-8")

    payload = query_all(query="memory", chunks_path=chunks, events_dir=events)

    assert payload["degraded"] is True
    assert payload["results"]["rag"] == []
    assert payload["results"]["timeline"][0]["id"] == "run-1"
    assert [item["kind"] for item in payload["missing_artifacts"]] == ["rag_chunks"]


@pytest.mark.parametrize("requested_layer", ["rag", "timeline"])
def test_single_layer_queries_do_not_inspect_other_layer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, requested_layer: str
) -> None:
    chunks, events = write_test_retrieval_layers(
        tmp_path,
        rag_ready=requested_layer == "rag",
        timeline_ready=requested_layer == "timeline",
        query="memory",
    )
    if requested_layer == "rag":
        monkeypatch.setattr(
            memory_query,
            "timeline_events_ready",
            lambda _: pytest.fail("RAG query must not inspect the timeline"),
        )
        payload = memory_query.query_rag(
            memory_query.RagQueryOptions(query="memory", chunks_path=chunks)
        )
    else:
        monkeypatch.setattr(
            memory_query,
            "rag_chunks_ready",
            lambda _: pytest.fail("Timeline query must not inspect RAG"),
        )
        payload = memory_query.query_timeline(
            query="memory", event_family=None, event_type=None, events_dir=events
        )
    assert payload["count"] == 1
