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
"""Seed-id extraction respects a disabled input filter."""

from __future__ import annotations

import pytest

from bioetl.composition.providers.registration_bio import (
    _extract_uniprot_mapping_seed_ids,
)
from bioetl.domain.filtering.input_config import InputFilterConfig


pytestmark = pytest.mark.unit


def test_disabled_filter_does_not_return_seed_ids() -> None:
    config = InputFilterConfig(enabled=False, direct_filter_ids=("P12345",))
    assert _extract_uniprot_mapping_seed_ids(config) is None


def test_enabled_filter_returns_seed_ids() -> None:
    config = InputFilterConfig(
        enabled=True,
        filter_field="accession",
        direct_filter_ids=("P12345",),
    )
    assert _extract_uniprot_mapping_seed_ids(config) == ["P12345"]
