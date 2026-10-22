"""Unit tests for GitHub billing validation and totals."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from scripts.engineering.finances.github_billing_pipeline import (
    calculate_totals,
    extract_workflow_attribution,
)
from scripts.engineering.finances.github_billing_schema import GitHubBillingRecord
from scripts.engineering.finances.github_billing_validator import (
    validate_billing_report,
)

pytestmark = pytest.mark.unit

_HEADER = (
    "date,product,sku,repository,workflow_path,quantity,unit_type,"
    "gross_amount,discount_amount,net_amount,currency"
)


def _record(**overrides: object) -> GitHubBillingRecord:
    payload: dict[str, object] = {
        "date": date(2026, 9, 15),
        "product": "Actions",
        "sku": "Compute - Ubuntu",
        "repository": "SatoryKono/BioactivityDataAcquisition",
        "workflow_path": ".github/workflows/ci.yml",
        "quantity": 100,
        "unit_type": "minutes",
        "gross_amount": Decimal("10"),
        "discount_amount": Decimal("0"),
        "net_amount": Decimal("10"),
        "currency": "USD",
    }
    payload.update(overrides)
    return GitHubBillingRecord.model_validate(payload)


def test_github_billing_schema_validation() -> None:
    """A complete row keeps decimal money and the supplied currency."""
    record = _record(gross_amount=Decimal("10.05"), net_amount=Decimal("10.05"))

    assert record.currency == "USD"
    assert record.net_amount == Decimal("10.05")


def test_money_fields_reject_float() -> None:
    """Binary floats are not accepted as billing amounts."""
    with pytest.raises(ValidationError, match="reject float"):
        _record(net_amount=10.05)


def test_currency_is_required() -> None:
    """A missing currency is not treated as USD."""
    with pytest.raises(ValidationError):
        GitHubBillingRecord.model_validate(
            {
                "date": date(2026, 9, 15),
                "product": "Actions",
                "sku": "Actions Linux",
                "quantity": 1,
                "unit_type": "minutes",
                "gross_amount": "1",
                "discount_amount": "0",
                "net_amount": "1",
            }
        )


def test_calculate_totals() -> None:
    """Known products land in their category buckets."""
    records = [
        _record(),
        _record(
            product="Shared Storage",
            sku="Standard",
            quantity=50,
            unit_type="gb-hours",
            gross_amount=Decimal("5"),
            net_amount=Decimal("5"),
            workflow_path=None,
        ),
        _record(
            product="Copilot",
            sku="Business",
            quantity=1,
            unit_type="users",
            gross_amount=Decimal("19"),
            net_amount=Decimal("19"),
            workflow_path=None,
        ),
    ]

    totals = calculate_totals(records, "USD")

    assert totals["actions_compute"] == Decimal("10")
    assert totals["shared_storage"] == Decimal("5")
    assert totals["copilot"] == Decimal("19")
    assert totals["lfs"] == Decimal("0")
    assert totals["other"] == Decimal("0")


def test_official_actions_runner_sku_is_compute() -> None:
    """GitHub usage reports bill runners as ``Actions Linux``, not ``Compute``."""
    record = _record(
        sku="Actions Linux", net_amount=Decimal("0.80"), gross_amount=Decimal("0.80")
    )
    storage = _record(
        sku="Actions storage", net_amount=Decimal("0.20"), gross_amount=Decimal("0.20")
    )

    totals = calculate_totals([record, storage], "USD")
    attribution = extract_workflow_attribution([record, storage], "USD")

    assert totals["actions_compute"] == Decimal("0.80")
    assert totals["other"] == Decimal("0.20")
    assert attribution[(record.repository, record.workflow_path)] == Decimal("0.80")


def test_decimal_totals_do_not_use_binary_float() -> None:
    """Cent amounts that are inexact in binary stay exact in the total."""
    records = [
        _record(net_amount=Decimal("0.10"), gross_amount=Decimal("0.10")),
        _record(net_amount=Decimal("0.20"), gross_amount=Decimal("0.20")),
    ]

    totals = calculate_totals(records, "USD")

    assert totals["actions_compute"] == Decimal("0.30")


def test_mixed_currency_is_rejected() -> None:
    """Rows in different currencies are not added together."""
    records = [_record(), _record(currency="EUR")]

    with pytest.raises(ValueError, match="report currency"):
        calculate_totals(records, "USD")


def test_extract_workflow_attribution_splits_repositories() -> None:
    """The same workflow path in two repositories stays two buckets."""
    records = [
        _record(repository="org/one", net_amount=Decimal("10")),
        _record(repository="org/two", sku="Compute - Windows", net_amount=Decimal("5")),
        _record(repository=None, workflow_path=None, net_amount=Decimal("1")),
        _record(
            repository=None,
            workflow_path=".github/workflows/ci.yml",
            net_amount=Decimal("2"),
        ),
    ]

    attribution = extract_workflow_attribution(records, "USD")

    assert attribution[("org/one", ".github/workflows/ci.yml")] == Decimal("10")
    assert attribution[("org/two", ".github/workflows/ci.yml")] == Decimal("5")
    assert attribution[(None, "unattributed")] == Decimal("1")
    assert attribution[(None, ".github/workflows/ci.yml")] == Decimal("2")


def test_validate_billing_report(tmp_path: Path) -> None:
    """A non-empty normalized CSV round-trips optional identifiers."""
    csv_file = tmp_path / "billing.csv"
    csv_file.write_text(
        _HEADER
        + "\n"
        + "2026-09-15,Actions,Compute - Ubuntu,SatoryKono/BioactivityDataAcquisition,"
        + ".github/workflows/ci.yml,100,minutes,10,0,10,USD\n"
        + "2026-09-16,Shared Storage,Standard,,,50,gb-hours,5,0,5,USD\n",
        encoding="utf-8",
    )

    records = validate_billing_report(str(csv_file))

    assert len(records) == 2
    assert records[0].workflow_path == ".github/workflows/ci.yml"
    assert records[0].net_amount == Decimal("10")
    assert records[1].product == "Shared Storage"
    assert records[1].repository is None
    assert records[1].workflow_path is None


def test_validate_billing_report_rejects_empty_and_header_only(tmp_path: Path) -> None:
    """Absence of a billing export is not a zero-spend report."""
    empty_file = tmp_path / "empty.csv"
    header_only = tmp_path / "header.csv"
    missing_currency = tmp_path / "missing-currency.csv"
    empty_file.write_text("", encoding="utf-8")
    header_only.write_text(_HEADER + "\n", encoding="utf-8")
    missing_currency.write_text(
        "date,product,sku,repository,workflow_path,quantity,unit_type,"
        "gross_amount,discount_amount,net_amount\n"
        "2026-09-15,Actions,Actions Linux,org/one,.github/workflows/ci.yml,"
        "1,minutes,1,0,1\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="empty or missing a header"):
        validate_billing_report(str(empty_file))
    with pytest.raises(ValueError, match="no data rows"):
        validate_billing_report(str(header_only))
    with pytest.raises(ValueError, match="currency"):
        validate_billing_report(str(missing_currency))
