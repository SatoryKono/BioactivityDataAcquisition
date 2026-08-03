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
"""Basename collision inventory + request_metadata rename guard (TEST-SYS-10 / #7032)."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

_REPO = Path(__file__).resolve().parents[2]
_INV = _REPO / "reports/quality/test-basename-collision-inventory.json"
_ADAPTERS = _REPO / "tests/unit/infrastructure/adapters"


@pytest.mark.architecture
def test_request_metadata_basenames_are_provider_prefixed() -> None:
    legacy = list(_ADAPTERS.rglob("test_request_metadata.py"))
    assert not legacy, (
        "Provider-prefixed names required after TEST-SYS-10: "
        + ", ".join(p.relative_to(_REPO).as_posix() for p in legacy)
    )
    renamed = list(_ADAPTERS.rglob("test_*_request_metadata.py"))
    assert len(renamed) >= 7


@pytest.mark.architecture
def test_basename_collision_inventory_exists_and_is_honest() -> None:
    assert _INV.is_file()
    payload = json.loads(_INV.read_text(encoding="utf-8"))
    by_base: dict[str, list[str]] = defaultdict(list)
    for path in (_REPO / "tests").rglob("test_*.py"):
        by_base[path.name].append(path.relative_to(_REPO).as_posix())
    live_dups = {k: v for k, v in by_base.items() if len(v) > 1}
    assert payload["duplicate_basename_count"] == len(live_dups)
    # High-churn family must no longer collide.
    assert "test_request_metadata.py" not in live_dups
