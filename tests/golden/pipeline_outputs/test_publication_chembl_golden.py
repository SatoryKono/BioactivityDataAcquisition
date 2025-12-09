"""Golden snapshot for publication_chembl pipeline outputs."""

from pathlib import Path

from .test_pipeline_outputs_helpers import load_expected_records

expected_publication_records = (
    load_expected_records(
        Path("data/_output/publication/document.csv"),
        sort_key="document_chembl_id",
    )
)

__all__ = ["expected_publication_records"]
