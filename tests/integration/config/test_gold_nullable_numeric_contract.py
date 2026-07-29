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
"""Contract checks for documented Gold nullable numeric governance."""

from __future__ import annotations

import pytest

from pathlib import Path

from scripts.engineering.qa.check_gold_nullable_numeric_compatibility import (
    NULLABLE_NUMERIC_SPECS,
    validate_nullable_numeric_compatibility,
)


pytestmark = pytest.mark.integration


def test_gold_nullable_numeric_contract_gate_passes_current_repo() -> None:
    findings = validate_nullable_numeric_compatibility(Path("."))

    assert not findings, "\n".join(finding.message for finding in findings)


def test_nullable_numeric_specs_cover_audit_categories() -> None:
    categories = {spec.category for spec in NULLABLE_NUMERIC_SPECS}

    assert {
        "publication_year_and_citations",
        "molecule_descriptors",
        "activity_measurements",
    } <= categories


def test_nullable_numeric_specs_cover_representative_fields() -> None:
    fields = {field for spec in NULLABLE_NUMERIC_SPECS for field in spec.fields}

    assert {
        "publication_year",
        "citations_received",
        "citations_made",
        "molecular_weight",
        "logp",
        "xlogp",
        "polar_surface_area",
        "tpsa",
        "hba_count",
        "hbd_count",
        "standard_value",
        "pchembl_value",
    } <= fields
