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
"""Contracts chosen for the remaining domain validation findings."""

from __future__ import annotations

import pytest

from bioetl.domain._observability_contract_primitives import normalize_severity
from bioetl.domain.normalization.profiles._standard_profile_spec import (
    coerce_standard_profile_spec,
)


pytestmark = pytest.mark.unit


def test_severity_aliases_map_into_the_bounded_vocabulary() -> None:
    assert normalize_severity("warn", fallback="info") == "warning"
    assert normalize_severity("fatal", fallback="info") == "error"
    assert normalize_severity("critical", fallback="info") == "error"
    assert normalize_severity("exception", fallback="info") == "error"
    assert normalize_severity("nope", fallback="info") == "info"


def test_unknown_standard_profile_override_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown standard profile fields: not_a_field"):
        coerce_standard_profile_spec(
            None,
            {
                "profile_name": "activity",
                "description": "activity profile",
                "schema_fields": ("activity_id",),
                "meta_fields": (),
                "not_a_field": 1,
            },
        )
