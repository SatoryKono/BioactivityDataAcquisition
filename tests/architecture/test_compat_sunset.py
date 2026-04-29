"""Sunset enforcement for backward-compatibility shims.

Tracks active sunset items and removed shims. Active items count toward the
compatibility debt scorecard. Removed shims stay under an absence guard so the
compatibility surface cannot reappear silently.

Sunset date: 2026-06-30 (see PLAN-001).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

SUNSET_DATE = date(2026, 6, 30)

# Active sunset items. The 2026-04-29 removal wave retired all previously
# tracked entries early with explicit maintainer approval.
COMPAT_FILES: dict[str, Path] = {}
COMPAT_MODULES: dict[str, Path] = {}

REMOVED_COMPAT_MODULES: dict[str, Path] = {
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
    "application checkpoint legacy wrapper": Path(
        "src/bioetl/application/core/lifecycle/_checkpoint_legacy.py"
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


@pytest.mark.parametrize(
    "name,path",
    REMOVED_COMPAT_MODULES.items(),
    ids=REMOVED_COMPAT_MODULES.keys(),
)
def test_removed_compat_module_stays_removed(name: str, path: Path) -> None:
    """Removed compatibility modules must not be reintroduced."""
    assert not path.exists(), (
        f"Removed compatibility module {name} exists again at {path}. "
        "Use the canonical narrow-port or normalization surface instead."
    )
