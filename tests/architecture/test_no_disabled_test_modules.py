"""Architecture guard: no tracked ``*.disabled`` test modules.

Disabling a test by renaming it to ``*.disabled`` hides it from pytest
collection (``python_files = ["test_*.py"]``) *and* from the reviewed skip
inventory (``tests/architecture/test_test_skip_inventory.py`` scans ``.py``
suppression calls only). Such files become ungoverned dead assets with no
owner or expiry. Disabled tests MUST instead use a governed
``@pytest.mark.skip``/``skipif`` in a collected ``.py`` module, or be removed.
"""

from __future__ import annotations

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
TESTS_ROOT = ROOT / "tests"

pytestmark = pytest.mark.architecture


def _disabled_test_modules() -> list[str]:
    return sorted(
        path.relative_to(ROOT).as_posix()
        for path in TESTS_ROOT.rglob("*.disabled")
    )


def test_no_tracked_disabled_test_modules() -> None:
    offenders = _disabled_test_modules()

    assert not offenders, (
        "Tracked *.disabled test modules bypass pytest collection and the "
        "reviewed skip inventory. Remove them or convert to a governed "
        "@pytest.mark.skip/skipif in a collected .py module:\n"
        + "\n".join(offenders)
    )
