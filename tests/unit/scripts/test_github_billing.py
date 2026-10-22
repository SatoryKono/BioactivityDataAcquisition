import pytest
import os
from datetime import date
from scripts.engineering.finances.github_billing_schema import GitHubBillingRecord
from scripts.engineering.finances.github_billing_pipeline import calculate_totals, extract_workflow_attribution
from scripts.engineering.finances.github_billing_validator import validate_billing_report

def test_github_billing_schema_validation():
    # Valid record
    record = GitHubBillingRecord(
        date=date(2026, 9, 15),
        product="Actions",
        sku="Compute - Ubuntu",
        repository="SatoryKono/BioactivityDataAcquisition",
        workflow_path=".github/workflows/ci.yml",
        quantity=100.5,
        unit_type="minutes",
        gross_amount=10.05,
        discount_amount=0.0,
        net_amount=10.05
    )
    assert record.currency == "USD"
    assert record.net_amount == 10.05

def test_calculate_totals():
    records = [
        GitHubBillingRecord(
            date=date(2026, 9, 15), product="Actions", sku="Compute - Ubuntu",
            quantity=100, unit_type="minutes", gross_amount=10, discount_amount=0, net_amount=10
        ),
        GitHubBillingRecord(
            date=date(2026, 9, 15), product="Shared Storage", sku="Standard",
            quantity=50, unit_type="gb-hours", gross_amount=5, discount_amount=0, net_amount=5
        ),
        GitHubBillingRecord(
            date=date(2026, 9, 15), product="Copilot", sku="Business",
            quantity=1, unit_type="users", gross_amount=19, discount_amount=0, net_amount=19
        )
    ]

    totals = calculate_totals(records)
    assert totals["actions_compute"] == 10.0
    assert totals["shared_storage"] == 5.0
    assert totals["copilot"] == 19.0
    assert totals["lfs"] == 0.0
    assert totals["other"] == 0.0

def test_extract_workflow_attribution():
    records = [
        GitHubBillingRecord(
            date=date(2026, 9, 15), product="Actions", sku="Compute - Ubuntu",
            workflow_path=".github/workflows/ci.yml",
            quantity=100, unit_type="minutes", gross_amount=10, discount_amount=0, net_amount=10
        ),
        GitHubBillingRecord(
            date=date(2026, 9, 15), product="Actions", sku="Compute - Windows",
            workflow_path=".github/workflows/ci.yml",
            quantity=50, unit_type="minutes", gross_amount=5, discount_amount=0, net_amount=5
        ),
        GitHubBillingRecord(
            date=date(2026, 9, 15), product="Actions", sku="Compute - Ubuntu",
            workflow_path=None,
            quantity=10, unit_type="minutes", gross_amount=1, discount_amount=0, net_amount=1
        )
    ]

    attribution = extract_workflow_attribution(records)
    assert attribution[".github/workflows/ci.yml"] == 15.0
    assert attribution["unattributed"] == 1.0

def test_validate_billing_report(tmp_path):
    csv_file = tmp_path / "billing.csv"
    csv_content = """date,product,sku,repository,workflow_path,quantity,unit_type,gross_amount,discount_amount,net_amount,currency
2026-09-15,Actions,Compute - Ubuntu,SatoryKono/BioactivityDataAcquisition,.github/workflows/ci.yml,100,minutes,10,0,10,USD
2026-09-16,Shared Storage,Standard,,,50,gb-hours,5,0,5,USD
"""
    csv_file.write_text(csv_content, encoding="utf-8")

    records = validate_billing_report(str(csv_file))
    assert len(records) == 2
    assert records[0].workflow_path == ".github/workflows/ci.yml"
    assert records[1].product == "Shared Storage"
    assert records[1].repository is None
    assert records[1].workflow_path is None
