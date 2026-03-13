"""Sunset enforcement for backward-compatibility mixins.

These compat mixins were introduced during the composite merger/join planner
refactoring to preserve backward compatibility. After the sunset date, tests
invert and FAIL if the mixins still exist, enforcing their removal.

Sunset date: 2026-06-30 (see RF-014 in PLAN-001).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

SUNSET_DATE = date(2026, 6, 30)

COMPAT_MIXINS: dict[str, Path] = {
    "merger_compat_mixin.py": Path(
        "src/bioetl/application/composite/merger_compat_mixin.py"
    ),
    "join_planner_compat_mixin.py": Path(
        "src/bioetl/application/composite/join_planner_compat_mixin.py"
    ),
    "merger_compat_join_planner_mixin.py": Path(
        "src/bioetl/application/composite/merger_compat_join_planner_mixin.py"
    ),
}


@pytest.mark.parametrize("name,path", COMPAT_MIXINS.items(), ids=COMPAT_MIXINS.keys())
def test_compat_mixin_sunset(name: str, path: Path) -> None:
    """Before sunset: mixin MUST exist. After sunset: mixin MUST be removed."""
    today = date.today()
    exists = path.exists()

    if today <= SUNSET_DATE:
        assert exists, (
            f"Compat mixin {name} was removed before sunset date {SUNSET_DATE}. "
            f"If intentional, remove this test entry."
        )
    else:
        assert not exists, (
            f"Compat mixin {name} still exists after sunset date {SUNSET_DATE}. "
            f"Remove the mixin and inline any remaining logic."
        )
