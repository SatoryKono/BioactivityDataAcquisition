"""Unit tests for shared ChEMBL API model behavior."""

from __future__ import annotations

from bioetl.infrastructure.adapters.chembl.models_common import (
    ChemblPublicationApiRecord,
)


def test_chembl_publication_api_record_normalizes_integer_pubmed_id() -> None:
    record = ChemblPublicationApiRecord(
        document_chembl_id="CHEMBL_DOC_1",
        pubmed_id=12345678,
    )

    assert record.pubmed_id == "12345678"
