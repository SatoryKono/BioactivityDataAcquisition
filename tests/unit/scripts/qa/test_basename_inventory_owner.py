from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.engineering.qa import report_test_governance_audit as owner

pytestmark = pytest.mark.unit


@pytest.fixture
def inventory_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    paths = b"tests/z/test_same.py\0tests/a/test_same.py\0tests/a/test_unique.py\0tests/a/helper.py\0"
    monkeypatch.setattr(owner.subprocess, "check_output", lambda *_a, **_k: paths)
    (tmp_path / "reports/quality").mkdir(parents=True)
    return tmp_path


def test_basename_owner_writes_deterministic_complete_groups(
    inventory_root: Path,
) -> None:
    assert owner._basename_inventory(inventory_root, check=False) == 0
    destination = (
        inventory_root / "reports/quality/test-basename-collision-inventory.json"
    )
    assert json.loads(destination.read_text()) == {
        "duplicate_basename_count": 1,
        "duplicate_basenames": {
            "test_same.py": ["tests/a/test_same.py", "tests/z/test_same.py"]
        },
    }
    original = destination.read_bytes()
    assert owner._basename_inventory(inventory_root, check=True) == 0
    assert destination.read_bytes() == original


def test_basename_owner_check_rejects_wrong_members_without_writing(
    inventory_root: Path,
) -> None:
    destination = (
        inventory_root / "reports/quality/test-basename-collision-inventory.json"
    )
    destination.write_text('{"duplicate_basename_count": 1, "duplicate_basenames": {}}')
    original = destination.read_bytes()
    assert owner._basename_inventory(inventory_root, check=True) == 1
    assert destination.read_bytes() == original
