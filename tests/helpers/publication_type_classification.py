"""Explicit test helper for publication type classification initialization."""

from __future__ import annotations

from pathlib import Path


def initialize_test_publication_type_classification() -> None:
    """Load the published classification asset into the domain lookup tables."""
    from bioetl.domain.mapping.publication_type_classification import (
        initialize_classification,
    )
    from bioetl.infrastructure.config.publication_type_classification_loader import (
        PublicationTypeClassificationLoader,
    )

    repo_root = Path(__file__).resolve().parents[2]
    data = PublicationTypeClassificationLoader(repo_root / "configs").load()
    initialize_classification(data)
