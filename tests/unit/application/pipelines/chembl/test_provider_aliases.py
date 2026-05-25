"""Tests for ChEMBL provider-native alias normalization."""

from __future__ import annotations

from bioetl.application.pipelines.chembl.provider_aliases import (
    normalize_provider_aliases,
)


def test_normalize_provider_aliases_copies_provider_native_values() -> None:
    """Provider-native payload fields should populate canonical internal fields."""
    record = {"assay_chembl_id": "CHEMBL123"}

    normalized = normalize_provider_aliases(record, {"assay_id": "assay_chembl_id"})

    assert normalized["assay_id"] == "CHEMBL123"
    assert normalized["assay_chembl_id"] == "CHEMBL123"
    assert "assay_id" not in record


def test_normalize_provider_aliases_preserves_existing_canonical_values() -> None:
    """Already canonical staged payloads should not be overwritten."""
    record = {"assay_id": "CANONICAL", "assay_chembl_id": "PROVIDER"}

    normalized = normalize_provider_aliases(record, {"assay_id": "assay_chembl_id"})

    assert normalized is record
    assert normalized["assay_id"] == "CANONICAL"
