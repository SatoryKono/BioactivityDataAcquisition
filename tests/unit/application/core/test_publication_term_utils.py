"""Unit tests for publication term entity ID utility."""

from __future__ import annotations

from bioetl.application.core.publication_term_utils import (
    compute_publication_term_entity_id,
)


def test_compute_publication_term_entity_id_is_idempotent() -> None:
    """Repeated calls with same args must return identical ID."""
    first = compute_publication_term_entity_id("CHEMBL123", "MESH_HEADING", "Aspirin")
    second = compute_publication_term_entity_id("CHEMBL123", "MESH_HEADING", "Aspirin")
    assert first == second
    assert len(first) == 16
