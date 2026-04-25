"""Ownership tests for ChEMBL transformer/profile normalization boundaries."""

from __future__ import annotations

from pathlib import Path


def test_pure_bao_and_organism_normalization_is_not_transformer_owned() -> None:
    transformer_dir = Path("src/bioetl/application/pipelines/chembl")
    transformer_sources = {
        path.name: path.read_text(encoding="utf-8")
        for path in transformer_dir.glob("*_transformer.py")
    }

    for filename, source in transformer_sources.items():
        assert "normalize_bao_identifier" not in source, filename
        assert "normalize_chembl_organism_name" not in source, filename

    assay_profile_source = Path(
        "src/bioetl/domain/normalization/profiles/chembl_assay.py"
    ).read_text(encoding="utf-8")
    assert "normalize_bao_label" in assay_profile_source
