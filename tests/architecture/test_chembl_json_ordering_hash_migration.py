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
