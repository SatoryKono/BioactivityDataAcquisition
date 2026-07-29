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
"""Tests for governed open-access status normalization."""

from __future__ import annotations

import pytest

from bioetl.domain.normalization.open_access import normalize_governed_oa_status

pytestmark = pytest.mark.unit


def test_normalize_governed_oa_status_accepts_registry_values() -> None:
    assert normalize_governed_oa_status("Gold") == "gold"


def test_normalize_governed_oa_status_rejects_unknown_or_non_string_values() -> None:
    assert normalize_governed_oa_status("unknown") is None
    assert normalize_governed_oa_status(42) is None
