"""Read a normalized GitHub billing CSV into typed records."""

from __future__ import annotations

import csv
import io
from pathlib import Path

from pydantic import ValidationError

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


def _redacted_validation_error(exc: ValidationError) -> ValueError:
    """Name the failing field and error type without echoing cell values."""
    parts: list[str] = []
    for error in exc.errors():
        location = ".".join(str(item) for item in error.get("loc", ()))
        kind = str(error.get("type", "value_error"))
        parts.append(f"{location}: {kind}" if location else kind)
    detail = "; ".join(parts) if parts else "validation failed"
    return ValueError(f"billing report row failed validation ({detail})")


def _header_error(fieldnames: list[str] | None) -> ValueError | None:
    """Return a header error, or None when the normalized columns are usable."""
    if not fieldnames:
        return ValueError("billing report is empty or missing a header")
    missing = [name for name in REQUIRED_COLUMNS if name not in fieldnames]
    if missing:
        return ValueError(
            "billing report header is missing required columns: " + ", ".join(missing)
        )
    duplicates = _duplicate_columns(fieldnames)
    if duplicates:
        return ValueError(
            "billing report header repeats columns: " + ", ".join(duplicates)
        )
    return None


def _record_from_row(row: dict[str, str | None]) -> GitHubBillingRecord:
    """Validate one CSV row without copying its cell values into the error."""
    extra_cells = row.get(None)
    if extra_cells:
        raise ValueError("billing report row has more cells than the header")
    row["repository"] = _blank_to_none(row.get("repository"))
    row["workflow_path"] = _blank_to_none(row.get("workflow_path"))
    try:
        return GitHubBillingRecord.model_validate(row)
    except ValidationError as exc:
        raise _redacted_validation_error(exc) from None


def _load_records(raw: str) -> list[GitHubBillingRecord]:
    """Parse a normalized CSV payload into billing records."""
    reader = csv.DictReader(io.StringIO(raw, newline=""))
    header_error = _header_error(list(reader.fieldnames) if reader.fieldnames else None)
    if header_error is not None:
        raise header_error
    return [_record_from_row(row) for row in reader]


def validate_billing_report(file_path: str) -> list[GitHubBillingRecord]:
    """Load billing rows and reject an empty file or a header-only CSV.

    Raised errors name the constraint. They do not include cell values, so a
    public log cannot echo a financial row.
    """
    try:
        with Path(file_path).open(encoding="utf-8", newline="") as handle:
            raw = handle.read()
    except UnicodeDecodeError:
        raise ValueError("billing report is not valid UTF-8") from None
    if "\0" in raw:
        raise ValueError("billing report CSV is malformed")
    try:
        records = _load_records(raw)
    except csv.Error:
        raise ValueError("billing report CSV is malformed") from None
    if not records:
        raise ValueError("billing report contains a header but no data rows")
    return records
