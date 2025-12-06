"""Golden records for pipeline output regression tests."""

from .activity_chembl_golden import expected_activity_records
from .assay_chembl_golden import expected_assay_records
from .document_chembl_golden import expected_document_records
from .target_chembl_golden import expected_target_records
from .testitem_chembl_golden import expected_testitem_records

__all__ = [
    "expected_activity_records",
    "expected_assay_records",
    "expected_target_records",
    "expected_document_records",
    "expected_testitem_records",
]
