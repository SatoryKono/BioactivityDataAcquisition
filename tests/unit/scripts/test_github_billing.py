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
    split_inclusive_source_period,
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
    assert totals["shared_storage"] == Decimal("0.20")
    assert totals["other"] == Decimal("0")
    assert attribution[(record.repository, record.workflow_path)] == Decimal("0.80")


def test_cache_and_custom_image_storage_stay_outside_shared_pool() -> None:
    """Artifact and package storage share a pool; cache and images do not."""
    records = [
        _record(
            product="Packages",
            sku="Packages storage",
            net_amount=Decimal("1"),
            gross_amount=Decimal("1"),
        ),
        _record(
            sku="Actions cache storage",
            net_amount=Decimal("2"),
            gross_amount=Decimal("2"),
        ),
        _record(
            sku="actions_custom_image_storage",
            net_amount=Decimal("3"),
            gross_amount=Decimal("3"),
        ),
    ]

    totals = calculate_totals(records, "USD")

    assert totals["shared_storage"] == Decimal("1")
    assert totals["other"] == Decimal("5")


def test_net_must_equal_gross_minus_discount() -> None:
    """A row cannot report a net amount that disagrees with gross and discount."""
    with pytest.raises(ValidationError, match="must equal net_amount"):
        _record(
            gross_amount=Decimal("10"),
            discount_amount=Decimal("0"),
            net_amount=Decimal("0"),
        )


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
        _record(
            repository="org/two",
            sku="Compute - Windows",
            gross_amount=Decimal("5"),
            net_amount=Decimal("5"),
        ),
        _record(
            repository=None,
            workflow_path=None,
            gross_amount=Decimal("1"),
            net_amount=Decimal("1"),
        ),
        _record(
            repository=None,
            workflow_path=".github/workflows/ci.yml",
            gross_amount=Decimal("2"),
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

    duplicate_header = tmp_path / "duplicate-header.csv"
    extra_cell = tmp_path / "extra-cell.csv"
    duplicate_header.write_text(
        "date,product,sku,repository,workflow_path,quantity,unit_type,"
        "gross_amount,discount_amount,net_amount,net_amount,currency\n"
        "2026-09-15,Actions,Actions Linux,org/one,.github/workflows/ci.yml,"
        "1,minutes,1,0,1,0,USD\n",
        encoding="utf-8",
    )
    extra_cell.write_text(
        _HEADER + "\n"
        "2026-09-15,Actions,Actions Linux,org/one,.github/workflows/ci.yml,"
        "1,minutes,1,0,1,USD,extra\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="repeats columns"):
        validate_billing_report(str(duplicate_header))
    with pytest.raises(ValueError, match="more cells"):
        validate_billing_report(str(extra_cell))


def test_validate_billing_report_accepts_cr_only_line_endings(tmp_path: Path) -> None:
    """CSV exports using CR as the record separator remain readable."""
    cr_only = tmp_path / "cr-only.csv"
    cr_only.write_text(
        _HEADER + "\r" + "2026-09-15,Actions,Actions Linux,org/one,"
        ".github/workflows/ci.yml,1,minutes,1,0,1,USD\r",
        encoding="utf-8",
        newline="",
    )

    records = validate_billing_report(str(cr_only))

    assert len(records) == 1
    assert records[0].net_amount == Decimal("1")


@pytest.mark.parametrize("amount", ["", "SECRET_AMOUNT_777"])
def test_invalid_money_cell_is_redacted(tmp_path: Path, amount: str) -> None:
    """Blank and malformed money cells become redacted validation errors."""
    csv_file = tmp_path / "invalid-money.csv"
    csv_file.write_text(
        _HEADER
        + "\n"
        + "2026-09-15,Actions,Actions Linux,org/one,.github/workflows/ci.yml,"
        + f"1,minutes,{amount},0,0,USD\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="failed validation") as exc:
        validate_billing_report(str(csv_file))

    if amount:
        assert amount not in str(exc.value)


def test_cache_sku_stays_outside_shared_pool_when_product_says_shared() -> None:
    """A shared-storage product label does not absorb cache or custom images."""
    records = [
        _record(
            product="Shared Storage",
            sku="Actions cache storage",
            net_amount=Decimal("2"),
            gross_amount=Decimal("2"),
        ),
        _record(
            product="Shared Storage",
            sku="actions_custom_image_storage",
            net_amount=Decimal("3"),
            gross_amount=Decimal("3"),
        ),
        _record(
            product="Shared Storage",
            sku="Standard",
            net_amount=Decimal("5"),
            gross_amount=Decimal("5"),
        ),
    ]

    totals = calculate_totals(records, "USD")

    assert totals["shared_storage"] == Decimal("5")
    assert totals["other"] == Decimal("5")
    assert sum(totals.values(), Decimal("0")) == Decimal("10")


def test_unknown_sku_preserves_net_and_is_not_attributed() -> None:
    """An unrecognized SKU stays in other and does not invent a workflow."""
    compute = _record(net_amount=Decimal("4.00"), gross_amount=Decimal("4.00"))
    unknown = _record(
        sku="Actions metered bandwidth",
        net_amount=Decimal("1.25"),
        gross_amount=Decimal("1.25"),
        workflow_path=".github/workflows/not-compute.yml",
    )
    copilot = _record(
        product="Copilot",
        sku="Business",
        net_amount=Decimal("19"),
        gross_amount=Decimal("19"),
        workflow_path=None,
    )
    lfs = _record(
        product="Git LFS",
        sku="Bandwidth",
        net_amount=Decimal("0.40"),
        gross_amount=Decimal("0.40"),
        workflow_path=None,
    )
    records = [compute, unknown, copilot, lfs]

    totals = calculate_totals(records, "USD")
    attribution = extract_workflow_attribution(records, "USD")

    assert totals["actions_compute"] == Decimal("4.00")
    assert totals["other"] == Decimal("1.25")
    assert totals["copilot"] == Decimal("19")
    assert totals["lfs"] == Decimal("0.40")
    assert sum(totals.values(), Decimal("0")) == sum(
        (record.net_amount for record in records),
        Decimal("0"),
    )
    assert sum(attribution.values(), Decimal("0")) == Decimal("4.00")
    assert (compute.repository, compute.workflow_path) in attribution
    assert (unknown.repository, unknown.workflow_path) not in attribution


def test_split_inclusive_source_period_keeps_edges_and_outside_rows() -> None:
    """Both R1 windows stay source slices; rows outside them are preserved."""
    september = _record(
        date=date(2026, 9, 30),
        net_amount=Decimal("1"),
        gross_amount=Decimal("1"),
    )
    october_start = _record(
        date=date(2026, 10, 1),
        net_amount=Decimal("2"),
        gross_amount=Decimal("2"),
    )
    october_end = _record(
        date=date(2026, 10, 19),
        net_amount=Decimal("4"),
        gross_amount=Decimal("4"),
    )
    later = _record(
        date=date(2026, 10, 20),
        net_amount=Decimal("8"),
        gross_amount=Decimal("8"),
    )
    records = [september, october_start, october_end, later]

    september_inside, september_outside = split_inclusive_source_period(
        records,
        period_start=date(2026, 9, 1),
        period_end=date(2026, 9, 30),
    )
    october_inside, october_outside = split_inclusive_source_period(
        records,
        period_start=date(2026, 10, 1),
        period_end=date(2026, 10, 19),
    )
    single_day, _single_outside = split_inclusive_source_period(
        records,
        period_start=date(2026, 10, 19),
        period_end=date(2026, 10, 19),
    )
    empty_inside, empty_outside = split_inclusive_source_period(
        [],
        period_start=date(2026, 9, 1),
        period_end=date(2026, 9, 30),
    )

    assert [row.date for row in september_inside] == [date(2026, 9, 30)]
    assert september_inside[0] is september
    assert [row.date for row in october_inside] == [
        date(2026, 10, 1),
        date(2026, 10, 19),
    ]
    assert [row.date for row in single_day] == [date(2026, 10, 19)]
    assert sum(
        (row.net_amount for row in september_inside),
        Decimal("0"),
    ) + sum(
        (row.net_amount for row in september_outside),
        Decimal("0"),
    ) == Decimal("15")
    assert sum((row.net_amount for row in october_outside), Decimal("0")) == Decimal(
        "9"
    )
    assert empty_inside == ()
    assert empty_outside == ()


def test_split_inclusive_source_period_rejects_reversed_bounds() -> None:
    """A reversed window is a caller error and does not describe any row."""
    with pytest.raises(ValueError, match="period end is before period start"):
        split_inclusive_source_period(
            [_record()],
            period_start=date(2026, 10, 19),
            period_end=date(2026, 10, 1),
        )


def test_summarized_report_without_workflow_path_is_rejected(tmp_path: Path) -> None:
    """A summarized usage report is not detailed workflow attribution."""
    summarized = tmp_path / "summarized.csv"
    summarized.write_text(
        "date,product,sku,repository,quantity,unit_type,"
        "gross_amount,discount_amount,net_amount,currency\n"
        "2026-09-15,Actions,Actions Linux,org/one,1,minutes,1.10,0,1.10,USD\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="workflow_path") as exc:
        validate_billing_report(str(summarized))

    assert "1.10" not in str(exc.value)


def test_schema_and_csv_errors_do_not_echo_money(tmp_path: Path) -> None:
    """Validation failures name the constraint and omit financial cells."""
    with pytest.raises(ValidationError, match="must equal net_amount") as schema_exc:
        _record(
            gross_amount=Decimal("12.34"),
            discount_amount=Decimal("1.11"),
            net_amount=Decimal("9.99"),
        )

    mismatch = tmp_path / "mismatch.csv"
    extra = tmp_path / "extra.csv"
    malformed = tmp_path / "nul.csv"
    non_utf8 = tmp_path / "latin.csv"
    blank_currency = tmp_path / "blank-currency.csv"
    blank_amount = tmp_path / "blank-amount.csv"
    nonnumeric_amount = tmp_path / "nonnumeric-amount.csv"
    mismatch.write_text(
        _HEADER + "\n"
        "2026-09-15,Actions,Actions Linux,org/one,.github/workflows/ci.yml,"
        "1,minutes,12.34,1.11,9.99,USD\n",
        encoding="utf-8",
    )
    extra.write_text(
        _HEADER + "\n"
        "2026-09-15,Actions,Actions Linux,org/one,.github/workflows/ci.yml,"
        "1,minutes,12.34,0,12.34,USD,77.77\n",
        encoding="utf-8",
    )
    malformed.write_bytes(b"date,product\0sku\n")
    non_utf8.write_bytes(b"\xff\xfe not utf-8 billing 12.34")
    blank_currency.write_text(
        _HEADER + "\n"
        "2026-09-15,Actions,Actions Linux,org/one,.github/workflows/ci.yml,"
        "1,minutes,4.50,0,4.50,   \n",
        encoding="utf-8",
    )
    blank_amount.write_text(
        _HEADER + "\n"
        "2026-09-15,Actions,Actions Linux,org/one,.github/workflows/ci.yml,"
        "1,minutes,,0,0,USD\n",
        encoding="utf-8",
    )
    nonnumeric_amount.write_text(
        _HEADER + "\n"
        "2026-09-15,Actions,Actions Linux,org/one,.github/workflows/ci.yml,"
        "1,minutes,SECRET_AMOUNT_777,0,0,USD\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="failed validation") as mismatch_exc:
        validate_billing_report(str(mismatch))
    with pytest.raises(ValueError, match="more cells") as extra_exc:
        validate_billing_report(str(extra))
    with pytest.raises(ValueError, match="malformed") as malformed_exc:
        validate_billing_report(str(malformed))
    with pytest.raises(ValueError, match="UTF-8") as utf8_exc:
        validate_billing_report(str(non_utf8))
    with pytest.raises(ValueError, match="failed validation") as blank_exc:
        validate_billing_report(str(blank_currency))
    with pytest.raises(ValueError, match="failed validation") as blank_amount_exc:
        validate_billing_report(str(blank_amount))
    with pytest.raises(ValueError, match="failed validation") as nonnumeric_exc:
        validate_billing_report(str(nonnumeric_amount))

    leaked_tokens = ("12.34", "1.11", "9.99", "77.77", "4.50")
    messages = (
        str(schema_exc.value),
        str(mismatch_exc.value),
        str(extra_exc.value),
        str(malformed_exc.value),
        str(utf8_exc.value),
        str(blank_exc.value),
        str(blank_amount_exc.value),
        str(nonnumeric_exc.value),
    )
    for message in messages:
        for token in leaked_tokens:
            assert token not in message
    assert "USD" not in str(blank_exc.value)
    assert "SECRET_AMOUNT_777" not in str(nonnumeric_exc.value)


def test_awaiting_manifest_does_not_claim_currency_or_filters() -> None:
    """A missing export does not prove USD, empty filters, or an after window."""
    import json

    manifest_path = (
        Path(__file__).resolve().parents[3]
        / "reports"
        / "engineering"
        / "finances"
        / "billing_manifest.json"
    )
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert payload["status"] == "AWAITING_DATA"
    assert payload["financial_effect"] == "не установлен"
    assert payload["schema_version"] == "1.1"
    assert payload["currency"] is None
    assert payload["filters_applied"] is None
    assert payload["timezone"] is None
    assert payload["exported_at"] is None
    assert payload["normalization_version"] is None
    assert payload["source"] is None
    assert payload["calculation_command"] is None
    assert payload["expected_checksum"] == "PENDING"
    assert payload["billing_access_owner"] is None
    assert payload["calculation_confirmed_by"] is None
    assert payload["comparable_after"] == {
        "status": "NOT_AGREED",
        "tracked_by": "#12366",
    }
    assert payload["periods"] == [
        {
            "role": "source",
            "start": "2026-09-01",
            "end": "2026-09-30",
            "status": "PENDING",
        },
        {
            "role": "source",
            "start": "2026-10-01",
            "end": "2026-10-19",
            "status": "PENDING",
        },
    ]
    assert "USD" not in json.dumps(payload)
