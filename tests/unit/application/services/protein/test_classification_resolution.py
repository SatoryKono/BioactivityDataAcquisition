"""Same-path owner tests for protein classification resolution."""

import pytest

from bioetl.application.services.protein.classification_resolution import (
    TargetProteinClassificationRecord,
)
from bioetl.domain.mapping.protein_class_target_type import (
    PROTEIN_CLASS_TARGET_TYPE_RULE_VERSION,
)

pytestmark = pytest.mark.unit


def test_missing_record_preserves_target_and_resolution_metadata() -> None:
    record = TargetProteinClassificationRecord.missing(
        "CHEMBL_TARGET",
        mapping_version="mapping-v1",
    )

    assert record.target_id == "CHEMBL_TARGET"
    assert record.classification_status == "missing_classification"
    assert record.canonical_l1 == "missing"
    assert record.l1_counts_for_target_type is False
    assert record.l1_mapping_version == "mapping-v1"
    assert record.target_type_rule_version == PROTEIN_CLASS_TARGET_TYPE_RULE_VERSION
