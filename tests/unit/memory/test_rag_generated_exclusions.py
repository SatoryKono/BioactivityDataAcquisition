"""Generated memory must not recursively enter filesystem-fallback RAG builds."""

from pathlib import Path

import pytest

from memory.rag.filters import iter_rag_sources

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "relative",
    [
        "derived/rag/manifests/chunks.jsonl",
        "derived/rag/manifests/corpus_catalog.json",
        "rag/manifests/corpus_catalog.json",
        "derived/timeline/events/timeline_manifest.json",
        "timeline/events/timeline_manifest.json",
        "curated/archive/lessons/historical.md",
    ],
)
def test_fallback_sources_exclude_generated_and_archived_memory(
    tmp_path: Path, relative: str
) -> None:
    memory = tmp_path / "src/memory"
    memory.mkdir(parents=True)
    (memory / "query.py").write_text('"""Canonical source."""\n', encoding="utf-8")
    excluded = memory / relative
    excluded.parent.mkdir(parents=True, exist_ok=True)
    excluded.write_text("{}\n", encoding="utf-8")

    sources = iter_rag_sources(tmp_path, selected_ids=("memory_implementation",))

    assert sources == [Path("src/memory/query.py")]
