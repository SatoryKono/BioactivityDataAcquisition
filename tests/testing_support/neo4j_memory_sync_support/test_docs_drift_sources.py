"""Focused tests for docs-to-code drift source selection."""

from __future__ import annotations

import pytest
from scripts.memory.sync import (
    GraphSnapshot,
    _add_reverse_module_doc_edges,
    _docs_drift_sources,
)

pytestmark = [pytest.mark.memory, pytest.mark.timeout(180)]


def test_docs_drift_sources_skip_file_structure_doc_artifacts(
    tmp_path, monkeypatch
) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    curated_path = docs_dir / "curated.md"
    curated_path.write_text(
        "This MUST describe src/bioetl/domain/context.py" + chr(10), encoding="utf-8"
    )
    skipped_path = docs_dir / "bulk.md"
    skipped_path.write_text(
        "This SHOULD NOT be read during drift source scan" + chr(10), encoding="utf-8"
    )

    snapshot = GraphSnapshot()
    curated = snapshot.add_node(
        "doc_artifact",
        "docs/curated.md",
        source_path="docs/curated.md",
        source_kind="doc_artifact",
    )
    snapshot.add_node(
        "doc_artifact",
        "docs/bulk.md",
        source_path="docs/bulk.md",
        source_kind="doc_artifact",
        repo_zone="docs",
    )

    import scripts.memory.sync as sync_module

    def guarded_read_text(path):
        if path == skipped_path:
            raise AssertionError("file-structure doc artifact should not be read")
        return path.read_text(encoding="utf-8")

    monkeypatch.setattr(sync_module, "_read_text", guarded_read_text)

    sources = list(_docs_drift_sources(snapshot, tmp_path, {}))

    assert sources == [
        (curated, "docs/curated.md", curated_path.read_text(encoding="utf-8"))
    ]


def test_reverse_module_doc_edges_include_curated_doc_sources() -> None:
    snapshot = GraphSnapshot()
    module = snapshot.add_node(
        "module_surface",
        "src/bioetl/domain/control_plane/run_manifest.py",
        source_path="src/bioetl/domain/control_plane/run_manifest.py",
    )
    doc_source = snapshot.add_node(
        "doc_source_surface",
        "docs/04-reference/contracts/run-manifest-ledger.md",
        source_path="docs/04-reference/contracts/run-manifest-ledger.md",
    )
    snapshot.add_relation(
        doc_source,
        "DESCRIBES",
        module,
        provenance="docs_code_drift",
        confidence="high",
    )

    _add_reverse_module_doc_edges(snapshot)

    relation_keys = {
        (
            relation.source.label,
            relation.source.name,
            relation.relation_type,
            relation.target.label,
            relation.target.name,
        )
        for relation in snapshot.relations.values()
    }
    assert (
        "module_surface",
        "src/bioetl/domain/control_plane/run_manifest.py",
        "DESCRIBED_IN",
        "doc_source_surface",
        "docs/04-reference/contracts/run-manifest-ledger.md",
    ) in relation_keys
