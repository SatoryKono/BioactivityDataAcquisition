"""Sunset enforcement for backward-compatibility shims.

Tracks all known compat items (files, functions, classes) with a sunset date.
Before sunset: item MUST exist (premature removal breaks the plan).
After sunset: item MUST be removed (forces cleanup).

Sunset date: 2026-06-30 (see PLAN-001).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

SUNSET_DATE = date(2026, 6, 30)

# ---------------------------------------------------------------------------
# Category 1: Pipeline factory compat files (facade + helpers)
# ---------------------------------------------------------------------------
COMPAT_FILES: dict[str, Path] = {}

# ---------------------------------------------------------------------------
# Category 2: Aggregate StoragePort (backward-compat facade over narrow ports)
# ---------------------------------------------------------------------------
COMPAT_MODULES: dict[str, Path] = {
    "aggregate_port.py (StoragePort)": Path(
        "src/bioetl/domain/ports/storage/aggregate_port.py"
    ),
    "domain normalization_authors compat wrapper": Path(
        "src/bioetl/domain/normalization_authors.py"
    ),
    "domain normalization_pages compat wrapper": Path(
        "src/bioetl/domain/normalization_pages.py"
    ),
    "domain normalization_dates compat wrapper": Path(
        "src/bioetl/domain/normalization_dates.py"
    ),
    "domain normalization_chembl compat wrapper": Path(
        "src/bioetl/domain/normalization_chembl.py"
    ),
    "domain services doi_normalization compat wrapper": Path(
        "src/bioetl/domain/services/doi_normalization.py"
    ),
    "domain services pmid_normalization compat wrapper": Path(
        "src/bioetl/domain/services/pmid_normalization.py"
    ),
    "domain services date_normalization compat wrapper": Path(
        "src/bioetl/domain/services/date_normalization.py"
    ),
    "domain services text_normalization compat wrapper": Path(
        "src/bioetl/domain/services/text_normalization.py"
    ),
    "domain services _date_helpers compat wrapper": Path(
        "src/bioetl/domain/services/_date_helpers.py"
    ),
}


@pytest.mark.parametrize("name,path", COMPAT_FILES.items(), ids=COMPAT_FILES.keys())
def test_compat_file_sunset(name: str, path: Path) -> None:
    """Before sunset: compat file MUST exist. After sunset: MUST be removed."""
    today = date.today()
    exists = path.exists()

    if today <= SUNSET_DATE:
        assert exists, (
            f"Compat file {name} was removed before sunset date {SUNSET_DATE}. "
            f"If intentional, remove this test entry."
        )
    else:
        assert not exists, (
            f"Compat file {name} still exists after sunset date {SUNSET_DATE}. "
            f"Migrate callers to canonical imports and remove the file."
        )


@pytest.mark.parametrize("name,path", COMPAT_MODULES.items(), ids=COMPAT_MODULES.keys())
def test_compat_module_sunset(name: str, path: Path) -> None:
    """Before sunset: compat module MUST exist. After sunset: MUST be removed."""
    today = date.today()
    exists = path.exists()

    if today <= SUNSET_DATE:
        assert exists, (
            f"Compat module {name} was removed before sunset date {SUNSET_DATE}. "
            f"If intentional, remove this test entry."
        )
    else:
        assert not exists, (
            f"Compat module {name} still exists after sunset date {SUNSET_DATE}. "
            f"Migrate consumers to narrow ports and remove the aggregate."
        )
