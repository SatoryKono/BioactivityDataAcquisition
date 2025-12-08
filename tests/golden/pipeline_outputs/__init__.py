"""Golden records for pipeline output regression tests."""

from .test_activity_chembl_golden import expected_activity_records
from .test_assay_chembl_golden import expected_assay_records
from .test_document_chembl_golden import expected_document_records
from .test_target_chembl_golden import expected_target_records
from .test_molecule_chembl_golden import expected_molecule_records

__all__ = [
    "expected_activity_records",
    "expected_assay_records",
    "expected_target_records",
    "expected_document_records",
    "expected_molecule_records",
]
