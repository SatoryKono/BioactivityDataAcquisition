# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Architecture guard for reviewed ChEMBL JSON ordering policy identity."""

from __future__ import annotations

import pytest

from bioetl.domain.normalization.profiles.chembl_json_ordering_policy import (
    CHEMBL_JSON_ORDERING_POLICY_HASH,
    CHEMBL_JSON_ORDERING_POLICY_VERSION,
)


pytestmark = pytest.mark.architecture


def test_chembl_json_ordering_policy_changes_require_explicit_version_and_hash_review() -> (
    None
):
    assert CHEMBL_JSON_ORDERING_POLICY_VERSION == "2026.06.01"
    assert (
        CHEMBL_JSON_ORDERING_POLICY_HASH
        == "0232382fa78a706b3f92ec77bc06ca4966826236e9dfcb142022c457138107f9"
    )
