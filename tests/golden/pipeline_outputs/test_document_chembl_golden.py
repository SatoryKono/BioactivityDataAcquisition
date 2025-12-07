"""Golden snapshot for document_chembl pipeline outputs."""

from pathlib import Path

from .test_pipeline_outputs_helpers import load_expected_records

expected_document_records = load_expected_records(
    Path("data/output/document/document.csv"), sort_key="document_chembl_id"
)

__all__ = ["expected_document_records"]
