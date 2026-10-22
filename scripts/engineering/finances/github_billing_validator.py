"""Read a normalized GitHub billing CSV into typed records."""

from __future__ import annotations

import csv
from pathlib import Path

from scripts.engineering.finances.github_billing_schema import GitHubBillingRecord

REQUIRED_COLUMNS = (
    "date",
    "product",
    "sku",
    "repository",
    "workflow_path",
    "quantity",
    "unit_type",
    "gross_amount",
    "discount_amount",
    "net_amount",
    "currency",
)


def _blank_to_none(value: str | None) -> str | None:
    """Treat a blank CSV cell as an absent optional identifier."""
    if value is None:
        return None
    text = value.strip()
    return text or None


def validate_billing_report(file_path: str) -> list[GitHubBillingRecord]:
    """Load billing rows and reject an empty file or a header-only CSV."""
    with Path(file_path).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        if not fieldnames:
            raise ValueError("billing report is empty or missing a header")
        missing = [name for name in REQUIRED_COLUMNS if name not in fieldnames]
        if missing:
            raise ValueError(
                "billing report header is missing required columns: "
                + ", ".join(missing)
            )
        records: list[GitHubBillingRecord] = []
        for row in reader:
            row["repository"] = _blank_to_none(row.get("repository"))
            row["workflow_path"] = _blank_to_none(row.get("workflow_path"))
            records.append(GitHubBillingRecord.model_validate(row))
    if not records:
        raise ValueError("billing report contains a header but no data rows")
    return records
