"""Tests for deterministic RAG manifest generation."""

from __future__ import annotations

import pytest

import json
from datetime import date, datetime
from pathlib import Path

from memory.rag.chunking import (
    infer_domain,
    infer_source_type,
    split_config_sections,
    split_markdown_sections,
    split_python_symbols,
)
from memory.rag import indexing as rag_indexing
from memory.rag.indexing import build_rag_manifests, write_rag_manifests
from memory.rag.retrieval import filter_chunks, load_chunk_manifest


pytestmark = pytest.mark.unit


def test_split_markdown_sections_respects_headings() -> None:
    text = """---
title: Demo
---

# Title
Intro paragraph.

## Details
Detail line.
"""
    sections = split_markdown_sections(text)
    assert [section.title for section in sections] == ["Title", "Details"]
    assert sections[0].level == 1
    assert "Intro paragraph." in sections[0].content


def test_infer_source_metadata_from_repo_paths() -> None:
    assert (
        infer_source_type(Path("docs/02-architecture/decisions/ADR-043-example.md"))
        == "adr"
    )
    assert (
        infer_source_type(Path("docs/05-operations/runbooks/example.md")) == "runbook"
    )
    assert infer_source_type(Path("docs/plans/example.md")) == "plan"
    assert infer_source_type(Path("docs/00-project/overview.md")) == "doc"
    assert infer_source_type(Path(".devin/wiki.json")) == "devin_wiki"
    assert infer_source_type(Path("src/memory/query.py")) == "memory"
    assert infer_source_type(Path("src/bioetl/application/service.py")) == "code"
    assert infer_source_type(Path("tests/unit/test_service.py")) == "test"
    assert infer_source_type(Path("configs/app.yaml")) == "config"
    assert infer_source_type(Path(".github/workflows/tests.yml")) == "workflow"
    assert infer_source_type(Path("grafana/dashboards/main.json")) == "dashboard"
    assert infer_source_type(Path("scripts/engineering/dev/run.sh")) == "script"
    assert (
        infer_domain(Path("docs/02-architecture/decisions/ADR-043-example.md"))
        == "architecture"
    )
    assert infer_domain(Path("docs/05-operations/runbooks/example.md")) == "operations"
    assert infer_domain(Path(".github/workflows/tests.yml")) == "operations"
    assert infer_domain(Path(".devin/wiki.json")) == "project"
    assert infer_domain(Path("docs/00-project/overview.md")) == "project"
    assert infer_domain(Path("src/memory/query.py")) == "memory_subsystem"
    assert infer_domain(Path("src/bioetl/application/service.py")) == "runtime"
    assert infer_domain(Path("tests/unit/test_service.py")) == "quality"
    assert infer_domain(Path("configs/app.yaml")) == "configuration"


def test_split_python_symbols_extracts_module_preamble_and_top_level_symbols() -> None:
    text = '''"""Module."""

from __future__ import annotations

import os


class Demo:
    pass


def run() -> None:
    return None
'''
    sections = split_python_symbols(text)
    assert [section.title for section in sections] == ["module-preamble", "Demo", "run"]
    assert [section.symbol_kind for section in sections] == [
        "module_preamble",
        "class",
        "function",
    ]


def test_split_config_sections_extracts_top_level_keys() -> None:
    text = """
version: 1
sources:
  enabled: true
"""
    sections = split_config_sections(text, Path("configs/example.yaml"))
    assert [section.title for section in sections] == ["version", "sources"]
    assert all(section.symbol_kind == "config_section" for section in sections)


def test_split_config_sections_serializes_dates_deterministically() -> None:
    payload = {
        "release_date": date(2026, 4, 29),
        "generated_at": datetime(2026, 4, 29, 12, 34, 56),
    }
    text = json.dumps(
        {
            "release_date": payload["release_date"].isoformat(),
            "generated_at": payload["generated_at"].isoformat(),
        }
    )
    sections = split_config_sections(text, Path("configs/example.json"))
    assert [section.title for section in sections] == ["release_date", "generated_at"]
    assert sections[0].content == json.dumps("2026-04-29", ensure_ascii=True)
    assert sections[1].content == json.dumps("2026-04-29T12:34:56", ensure_ascii=True)


def test_build_rag_manifests_indexes_devin_wiki_pages(tmp_path: Path) -> None:
    (tmp_path / ".devin").mkdir(parents=True)
    (tmp_path / ".devin" / "wiki.json").write_text(
        json.dumps(
            {
                "repo_notes": [{"content": "Navigation seed for onboarding."}],
                "pages": [
                    {
                        "title": "BioETL Overview",
                        "purpose": "High-level project map.",
                        "page_notes": [{"content": "Top-level wiki page."}],
                    },
                    {
                        "title": "Architecture",
                        "purpose": "Hexagonal architecture and medallion overview.",
                        "parent": "BioETL Overview",
                        "page_notes": [],
                    },
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    catalog, chunks = build_rag_manifests(tmp_path)

    assert catalog["source_count"] == 1
    assert catalog["sources"][0]["source_type"] == "devin_wiki"
    assert catalog["sources"][0]["repo_zone"] == "derived_navigation_context"
    assert catalog["sources"][0]["section_count"] == 3

    page_chunk = next(chunk for chunk in chunks if chunk["title"] == "Architecture")
    assert page_chunk["source_type"] == "devin_wiki"
    assert page_chunk["symbol_kind"] == "wiki_page"
    assert page_chunk["source_path"] == ".devin/wiki.json#architecture"
    assert "Parent: BioETL Overview" in page_chunk["content"]
    assert "devin-wiki-page::architecture" in page_chunk["related_refs"]
    assert "doc_artifact:.devin/wiki.json" in page_chunk["graph_node_refs"]


def test_build_rag_manifests_indexes_docs_code_tests_and_configs(
    tmp_path: Path,
) -> None:
    (tmp_path / ".devin").mkdir(parents=True)
    (tmp_path / "docs/00-project").mkdir(parents=True)
    (tmp_path / "docs/02-architecture/decisions").mkdir(parents=True)
    (tmp_path / "docs/plans").mkdir(parents=True)
    (tmp_path / "docs/05-operations/runbooks").mkdir(parents=True)
    (tmp_path / "docs/99-archive").mkdir(parents=True)
    (tmp_path / "src/bioetl/application").mkdir(parents=True)
    (tmp_path / "tests/unit").mkdir(parents=True)
    (tmp_path / "configs").mkdir(parents=True)
    (tmp_path / ".github/workflows").mkdir(parents=True)
    (tmp_path / "grafana/dashboards").mkdir(parents=True)
    (tmp_path / "scripts/engineering/dev").mkdir(parents=True)

    (tmp_path / "docs/00-project/overview.md").write_text(
        "# Overview\nAlpha\n", encoding="utf-8"
    )
    (tmp_path / "docs/02-architecture/decisions/ADR-999-test.md").write_text(
        "# ADR Test\nDecision body.\n",
        encoding="utf-8",
    )
    (tmp_path / "docs/plans/memory-plan.md").write_text(
        "# Memory Plan\nImplementation steps.\n",
        encoding="utf-8",
    )
    (tmp_path / "docs/05-operations/runbooks/sample.md").write_text(
        "# Runbook\nRecovery steps.\n",
        encoding="utf-8",
    )
    (tmp_path / "src/bioetl/application/service.py").write_text(
        "class Demo:\n    pass\n\n\ndef run() -> None:\n    return None\n",
        encoding="utf-8",
    )
    (tmp_path / "tests/unit/test_service.py").write_text(
        "def test_demo() -> None:\n    assert True\n",
        encoding="utf-8",
    )
    (tmp_path / "configs/app.yaml").write_text(
        "version: 1\nfeature_flags:\n  enabled: true\n",
        encoding="utf-8",
    )
    (tmp_path / ".github/workflows/tests.yml").write_text(
        "name: Tests\njobs:\n  unit:\n    runs-on: ubuntu-latest\n",
        encoding="utf-8",
    )
    (tmp_path / "grafana/dashboards/main.json").write_text(
        '{"title": "Main", "panels": []}\n',
        encoding="utf-8",
    )
    (tmp_path / "scripts/engineering/dev/run.sh").write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\n",
        encoding="utf-8",
    )
    (tmp_path / ".devin/wiki.json").write_text(
        json.dumps(
            {
                "repo_notes": [],
                "pages": [
                    {
                        "title": "BioETL Overview",
                        "purpose": "High-level introduction to the project.",
                        "page_notes": [],
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "docs/99-archive/ignored.md").write_text("# Ignore\n", encoding="utf-8")

    catalog, chunks = build_rag_manifests(tmp_path)

    assert catalog["source_count"] == 11
    assert {item["source_type"] for item in catalog["sources"]} == {
        "doc",
        "adr",
        "plan",
        "runbook",
        "devin_wiki",
        "code",
        "test",
        "config",
        "workflow",
        "dashboard",
        "script",
    }
    assert all("99-archive" not in chunk["source_path"] for chunk in chunks)
    assert {
        chunk["repo_zone"] for chunk in chunks if chunk["source_type"] == "code"
    } == {"canonical_runtime"}
    assert any(chunk["symbol_kind"] == "config_section" for chunk in chunks)
    code_chunk = next(
        chunk
        for chunk in chunks
        if chunk["source_type"] == "code" and chunk["symbol_kind"] == "class"
    )
    assert (
        "module_surface:src/bioetl/application/service.py"
        in code_chunk["graph_node_refs"]
    )
    assert (
        "class_surface:src.bioetl.application.service.Demo"
        in code_chunk["graph_node_refs"]
    )
    assert "module::src.bioetl.application.service" in code_chunk["related_refs"]
    assert "class::src.bioetl.application.service.Demo" in code_chunk["related_refs"]
    test_chunk = next(chunk for chunk in chunks if chunk["source_type"] == "test")
    assert "test_artifact:tests/unit/test_service.py" in test_chunk["graph_node_refs"]
    assert "test_surface:unit tests" in test_chunk["graph_node_refs"]
    assert "test-artifact::tests/unit/test_service.py" in test_chunk["related_refs"]
    assert "test-suite::unit tests" in test_chunk["related_refs"]
    config_chunk = next(chunk for chunk in chunks if chunk["source_type"] == "config")
    assert "config::configs/app.yaml" in config_chunk["related_refs"]
    workflow_chunk = next(
        chunk for chunk in chunks if chunk["source_type"] == "workflow"
    )
    assert "workflow::.github/workflows/tests.yml" in workflow_chunk["related_refs"]
    assert (
        "operational_artifact:.github/workflows/tests.yml"
        in workflow_chunk["graph_node_refs"]
    )
    devin_chunk = next(
        chunk for chunk in chunks if chunk["source_type"] == "devin_wiki"
    )
    assert devin_chunk["repo_zone"] == "derived_navigation_context"
    assert devin_chunk["confidence"] == "derived"


def test_write_and_reload_rag_manifests(tmp_path: Path) -> None:
    (tmp_path / "docs/00-project").mkdir(parents=True)
    (tmp_path / "src/bioetl/application").mkdir(parents=True)
    (tmp_path / "configs").mkdir(parents=True)
    (tmp_path / "docs/00-project/overview.md").write_text(
        "# Overview\nAlpha\n\n## Scope\nBeta\n",
        encoding="utf-8",
    )
    (tmp_path / "src/bioetl/application/service.py").write_text(
        "def run() -> None:\n    return None\n",
        encoding="utf-8",
    )
    (tmp_path / "configs/app.yaml").write_text("version: 1\n", encoding="utf-8")

    output_dir = tmp_path / "out"
    catalog_path, chunks_path = write_rag_manifests(tmp_path, output_dir)

    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    chunks = load_chunk_manifest(chunks_path)

    assert catalog["source_count"] == 3
    assert catalog["chunk_count"] == 4
    assert len(chunks) == 4
    assert len(filter_chunks(chunks, source_type="doc", query="scope")) == 1
    assert (
        len(
            filter_chunks(
                chunks, source_type="code", symbol_kind="function", query="run"
            )
        )
        == 1
    )
    assert (
        len(
            filter_chunks(
                chunks, source_type="config", repo_zone="unclassified", query="version"
            )
        )
        == 1
    )


def test_write_rag_manifests_retries_when_source_changes_during_build(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "docs/00-project/overview.md"
    source.parent.mkdir(parents=True)
    source.write_text("# Overview\nBefore\n", encoding="utf-8")
    original_builder = rag_indexing._build_standard_source_records
    build_calls = 0

    def _build_then_mutate(*args: object, **kwargs: object) -> object:
        nonlocal build_calls
        result = original_builder(*args, **kwargs)
        build_calls += 1
        if build_calls == 1:
            source.write_text("# Overview\nAfter\n", encoding="utf-8")
        return result

    monkeypatch.setattr(
        rag_indexing,
        "_build_standard_source_records",
        _build_then_mutate,
    )

    catalog_path, _ = write_rag_manifests(tmp_path, tmp_path / "out")
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))

    assert build_calls == 2
    assert catalog["sources"][0]["content_hash"] == rag_indexing.content_hash(
        "# Overview\nAfter\n"
    )


def test_source_reconciliation_rebuilds_only_changed_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    changing = tmp_path / "docs/00-project/changing.md"
    stable = tmp_path / "docs/00-project/stable.md"
    changing.parent.mkdir(parents=True)
    changing.write_text("# Changing\nBefore\n", encoding="utf-8")
    stable.write_text("# Stable\nContent\n", encoding="utf-8")
    original_builder = rag_indexing._build_standard_source_records
    build_calls: dict[str, int] = {}

    def _build_then_mutate(
        root: Path,
        rel_path: Path,
        **kwargs: object,
    ) -> object:
        result = original_builder(root, rel_path, **kwargs)
        rel_path_str = rel_path.as_posix()
        build_calls[rel_path_str] = build_calls.get(rel_path_str, 0) + 1
        if rel_path_str.endswith("changing.md") and build_calls[rel_path_str] == 1:
            changing.write_text("# Changing\nAfter\n", encoding="utf-8")
        return result

    monkeypatch.setattr(
        rag_indexing,
        "_build_standard_source_records",
        _build_then_mutate,
    )

    write_rag_manifests(tmp_path, tmp_path / "out")

    assert build_calls == {
        "docs/00-project/changing.md": 2,
        "docs/00-project/stable.md": 1,
    }


def test_write_rag_manifests_retries_when_source_disappears_during_build(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "docs/00-project/overview.md"
    replacement = tmp_path / "docs/00-project/replacement.md"
    source.parent.mkdir(parents=True)
    source.write_text("# Overview\nBefore\n", encoding="utf-8")
    original_builder = rag_indexing._build_standard_source_records
    build_calls = 0

    def _build_then_replace(*args: object, **kwargs: object) -> object:
        nonlocal build_calls
        result = original_builder(*args, **kwargs)
        build_calls += 1
        if build_calls == 1:
            source.unlink()
            replacement.write_text("# Replacement\nAfter\n", encoding="utf-8")
        return result

    monkeypatch.setattr(
        rag_indexing,
        "_build_standard_source_records",
        _build_then_replace,
    )

    catalog_path, _ = write_rag_manifests(tmp_path, tmp_path / "out")
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))

    assert build_calls == 2
    assert catalog["sources"][0]["source_path"] == ("docs/00-project/replacement.md")


def test_build_rag_manifests_fails_on_missing_tracked_source_paths(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    (tmp_path / "docs/00-project").mkdir(parents=True)
    existing_doc = tmp_path / "docs/00-project/overview.md"
    existing_doc.write_text("# Overview\nAlpha\n", encoding="utf-8")

    monkeypatch.setattr(
        rag_indexing,
        "iter_rag_sources",
        lambda root, **_: [
            Path("docs/00-project/overview.md"),
            Path("src/bioetl/interfaces/cli/commands/_inspection_output.py"),
        ],
    )

    with pytest.raises(FileNotFoundError, match=r"_inspection_output\.py"):
        build_rag_manifests(tmp_path)


def test_build_rag_manifests_workflow_scope_limits_to_focus_matches(
    tmp_path: Path,
) -> None:
    (tmp_path / "src/bioetl/application/pipelines").mkdir(parents=True)
    (tmp_path / "src/memory/tooling").mkdir(parents=True)
    (tmp_path / "tests/unit").mkdir(parents=True)
    (tmp_path / "docs/00-project").mkdir(parents=True)

    (tmp_path / "src/bioetl/application/pipelines/chembl_activity.py").write_text(
        "def run_chembl_activity() -> None:\n    return None\n",
        encoding="utf-8",
    )
    (tmp_path / "src/bioetl/application/pipelines/pubchem_compound.py").write_text(
        "def run_pubchem_compound() -> None:\n    return None\n",
        encoding="utf-8",
    )
    (tmp_path / "src/memory/tooling/workflow.py").write_text(
        "def workflow_refresh() -> None:\n    return None\n",
        encoding="utf-8",
    )
    (tmp_path / "tests/unit/test_memory_flow.py").write_text(
        "def test_memory() -> None:\n    assert True\n",
        encoding="utf-8",
    )
    (tmp_path / "docs/00-project/overview.md").write_text(
        "# Overview\nContext\n",
        encoding="utf-8",
    )

    catalog, chunks = build_rag_manifests(
        tmp_path,
        build_scope="workflow",
        focus_query="chembl_activity",
        max_sources=2,
    )

    assert catalog["build_scope"] == "workflow"
    assert catalog["focus_query"] == "chembl_activity"
    assert catalog["source_count"] == 2
    assert "src/bioetl/application/pipelines/chembl_activity.py" in {
        item["source_path"] for item in catalog["sources"]
    }
    assert all(
        "tests/unit/test_memory_flow.py" != chunk["source_path"] for chunk in chunks
    )


def test_write_rag_manifests_persists_build_scope_metadata(tmp_path: Path) -> None:
    (tmp_path / "src/memory/tooling").mkdir(parents=True)
    (tmp_path / "src/memory/tooling/workflow.py").write_text(
        "def workflow_refresh() -> None:\n    return None\n",
        encoding="utf-8",
    )

    output_dir = tmp_path / "out"
    catalog_path, _ = write_rag_manifests(
        tmp_path,
        output_dir,
        build_scope="workflow",
        focus_query="workflow",
        max_sources=1,
    )

    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))

    assert catalog["build_scope"] == "workflow"
    assert catalog["focus_query"] == "workflow"
    assert catalog["source_count"] == 1


def test_write_rag_manifests_restores_previous_pair_when_publish_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "docs/00-project").mkdir(parents=True)
    (tmp_path / "docs/00-project/overview.md").write_text(
        "# Overview\nCurrent\n",
        encoding="utf-8",
    )
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    catalog_path = output_dir / "corpus_catalog.json"
    chunks_path = output_dir / "chunks.jsonl"
    catalog_path.write_text('{"old":"catalog"}\n', encoding="utf-8")
    chunks_path.write_text('{"old":"chunks"}\n', encoding="utf-8")
    original_replace = rag_indexing.os.replace

    def _fail_new_chunks_publish(source: Path, target: Path) -> None:
        source_path = Path(source)
        target_path = Path(target)
        if (
            source_path.name == "chunks.jsonl"
            and source_path.parent.name.startswith(".rag-manifests-")
            and target_path == chunks_path
        ):
            raise OSError("simulated second-file publication failure")
        original_replace(source, target)

    monkeypatch.setattr(rag_indexing.os, "replace", _fail_new_chunks_publish)

    with pytest.raises(OSError, match="second-file publication failure"):
        write_rag_manifests(tmp_path, output_dir)

    assert catalog_path.read_text(encoding="utf-8") == '{"old":"catalog"}\n'
    assert chunks_path.read_text(encoding="utf-8") == '{"old":"chunks"}\n'
    assert not list(tmp_path.glob(".rag-manifests-*"))


def test_workflow_manifest_cannot_publish_to_canonical_repo_directory(
    tmp_path: Path,
) -> None:
    source = tmp_path / "src/memory/tooling/workflow.py"
    source.parent.mkdir(parents=True)
    source.write_text("def run() -> None:\n    return None\n", encoding="utf-8")
    canonical_dir = tmp_path / "src/memory/derived/rag/manifests"

    with pytest.raises(ValueError, match="workflow-scoped RAG manifests"):
        write_rag_manifests(
            tmp_path,
            canonical_dir,
            build_scope="workflow",
            focus_query="workflow",
            max_sources=1,
        )
