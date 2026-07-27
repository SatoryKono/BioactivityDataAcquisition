"""Windows/cloud-drive architecture scan policy guard (#6640)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.architecture

_REPO = Path(__file__).resolve().parents[2]
_POLICY = _REPO / "configs/quality/architecture_windows_scan_policy.yaml"


def test_windows_architecture_scan_policy_is_complete() -> None:
    payload = yaml.safe_load(_POLICY.read_text(encoding="utf-8"))
    assert payload["authority"]["linux_ci"] == "authoritative"
    assert payload["session_scan_index"]["helper"].endswith(
        "architecture_scan_index.py"
    )
    assert payload["session_scan_index"]["network_drive_worker_cap"] == 1
    assert "unit-fast" in payload["local_windows_policy"]["prefer_lanes"]
    assert (
        "layering_guards_on_linux_ci"
        in payload["local_windows_policy"]["must_not_weaken"]
    )
