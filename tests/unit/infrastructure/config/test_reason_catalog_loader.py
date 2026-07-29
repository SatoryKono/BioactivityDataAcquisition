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
"""Owner tests for the run-report reason catalog infrastructure loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.domain.run_reports.reason_catalog import REASON_CATALOG_VERSION
from bioetl.infrastructure.config.reason_catalog_loader import (
    load_default_reason_catalog,
    load_reason_catalog_from_path,
    load_reason_catalog_from_text,
)

pytestmark = pytest.mark.unit


def test_load_reason_catalog_from_text_parses_entries() -> None:
    catalog = load_reason_catalog_from_text(
        """
version: reason_catalog_v1
unknown_code: unknown
reasons:
  - code: filter_reject
    family: filter
    default_outcome: rejected
    layer: silver
    description: Rejected by silver filter
"""
    )
    assert catalog is not None
    assert catalog.version == REASON_CATALOG_VERSION
    assert "filter_reject" in catalog.entries
    assert catalog.entries["filter_reject"].family == "filter"


def test_load_reason_catalog_from_path_reads_shipped_asset() -> None:
    path = Path("configs/contracts/reports/reason_catalog.v1.yaml")
    catalog = load_reason_catalog_from_path(path)
    assert catalog is not None
    assert catalog.version == REASON_CATALOG_VERSION
    assert catalog.unknown_code


def test_load_default_reason_catalog_returns_usable_catalog() -> None:
    catalog = load_default_reason_catalog()
    assert catalog.version
    assert catalog.unknown_code
    assert catalog.entries
