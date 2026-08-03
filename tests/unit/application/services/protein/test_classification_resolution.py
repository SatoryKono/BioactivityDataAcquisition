# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
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
