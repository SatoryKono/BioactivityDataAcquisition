# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

DIAGNOSTICS_ROOT = (
    Path(__file__).resolve().parents[5]
    / "src"
    / "bioetl"
    / "application"
    / "services"
    / "control_plane"
    / "manifest"
    / "diagnostics"
)


def test_snapshot_support_pass_through_facade_stays_removed() -> None:
    assert not (DIAGNOSTICS_ROOT / "snapshot_support.py").exists()
