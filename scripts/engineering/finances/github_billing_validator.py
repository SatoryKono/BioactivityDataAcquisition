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


def _duplicate_columns(fieldnames: list[str]) -> list[str]:
    """Return header names that appear more than once, in first-seen order."""
    seen: set[str] = set()
    duplicates: list[str] = []
    for name in fieldnames:
        if name in seen:
            if name not in duplicates:
                duplicates.append(name)
            continue
        seen.add(name)
    return duplicates


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
        duplicates = _duplicate_columns(list(fieldnames))
        if duplicates:
            raise ValueError(
                "billing report header repeats columns: " + ", ".join(duplicates)
            )
        records: list[GitHubBillingRecord] = []
        for row in reader:
            extra_cells = row.get(None)
            if extra_cells:
                raise ValueError(
                    "billing report row has more cells than the header: "
                    + ", ".join(extra_cells)
                )
            row["repository"] = _blank_to_none(row.get("repository"))
            row["workflow_path"] = _blank_to_none(row.get("workflow_path"))
            records.append(GitHubBillingRecord.model_validate(row))
    if not records:
        raise ValueError("billing report contains a header but no data rows")
    return records
