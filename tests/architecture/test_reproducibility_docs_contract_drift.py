"""Architecture tests for reproducibility docs/contract drift guardrails."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


@pytest.mark.architecture
def test_chembl_molecule_schema_demotes_occurrence_provenance_from_row_contract() -> (
    None
):
    text = _read("docs/04-reference/schemas/domain/chembl/molecule-schema.md")

    assert "## System Fields (Persisted-Row Contract)" in text
    assert (
        "Occurrence-scoped provenance (`_run_id`, `_run_type`, `_source_batch_id`,"
        in text
    )
    assert "| `_run_id`" not in text
    assert '|  "_run_id":' not in text
    assert '|  "_run_type":' not in text
    assert '|  "_ingestion_ts":' not in text


@pytest.mark.architecture
def test_publication_provider_docs_mark_occurrence_provenance_as_sidecar_only() -> None:
    targets = (
        "docs/04-reference/providers/crossref/publication.md",
        "docs/04-reference/providers/openalex/publication.md",
        "docs/04-reference/providers/semanticscholar/publication.md",
    )

    for relative_path in targets:
        text = _read(relative_path)
        assert "persisted Silver/Gold row contract" in text, relative_path
        assert "sidecar/control-plane" in text, relative_path


@pytest.mark.architecture
def test_normalization_matrix_declares_non_contract_scope_and_drops_storage_wording() -> (
    None
):
    text = _read(
        "docs/reports/generated/pipeline_normalization_field_matrix/pipeline_normalization_field_matrix.md"
    )

    assert (
        "This matrix is a normalization inventory, not a persisted-row publication contract."
        in text
    )
    assert (
        "System/meta field retained for storage but excluded from content_hash."
        not in text
    )
    assert (
        "Technical field is passed through unchanged when no explicit profile rule is defined."
        not in text
    )
