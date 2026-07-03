"""Unit tests for publication controlled-vocabulary loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.infrastructure.config.publication_controlled_vocabulary_loader import (
    PublicationControlledVocabularyLoader,
)


@pytest.mark.unit
def test_loader_builds_trimmed_registry_with_inheritance(tmp_path: Path) -> None:
    vocab_dir = tmp_path / "vocab"
    vocab_dir.mkdir(parents=True)
    (vocab_dir / "publication_controlled.yaml").write_text(
        """
version: 1.0.0
providers:
  crossref:
    publication_type:
      preserve_unknown: true
      values:
        - "  Journal-Article  "
        - Dataset
  openalex:
    publication_type:
      preserve_unknown: true
      values:
        - " Article "
    type_crossref:
      preserve_unknown: true
      inherits: providers.crossref.publication_type
  pubmed:
    publication_status:
      preserve_unknown: false
      values:
        - ppublish
""".strip()
        + "\n",
        encoding="utf-8",
    )

    registry = PublicationControlledVocabularyLoader(tmp_path).load()

    assert registry.allowed_values("crossref", "publication_type") == frozenset(
        {"Journal-Article", "Dataset"}
    )
    assert registry.allowed_values("openalex", "publication_type") == frozenset(
        {"Article"}
    )
    assert registry.allowed_values("openalex", "type_crossref") == frozenset(
        {"Journal-Article", "Dataset"}
    )
    assert registry.allowed_values("pubmed", "publication_status") == frozenset()
