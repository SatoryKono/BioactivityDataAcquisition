"""Architecture gates for semantic Domain I/O taint inventory."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.engineering.qa.report_domain_io_taint_inventory import build_payload

ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = ROOT / "reports" / "quality" / "domain-io-taint-inventory.json"

pytestmark = pytest.mark.architecture


def test_domain_io_taint_inventory_artifact_matches_generator() -> None:
    """Committed Domain I/O taint evidence must match the current source tree."""
    expected = build_payload(ROOT)
    actual = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))

    assert actual == expected


def test_domain_io_taint_inventory_has_no_unreviewed_violations() -> None:
    payload = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))

    assert payload["violation_count"] == 0
    assert payload["violations"] == []


def test_domain_io_taint_inventory_records_explicit_schema_boundary_exceptions() -> None:
    payload = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    exception_kinds = {
        exception["kind"] for exception in payload.get("allowed_exceptions", [])
    }

    assert {"import:pandera", "import:pandas"} <= exception_kinds
