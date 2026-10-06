"""P1 #9808 — overlay/profile schema (DOCX гл.4.3)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

PROMPTS_ROOT = (
    Path(__file__).resolve().parents[2] / "docs" / "00-project" / "ai" / "prompts"
)
DOMAINS_PATH = PROMPTS_ROOT / "domains.yaml"
SCHEMA_PATH = PROMPTS_ROOT / "_schema" / "domain-overlay.schema.json"


def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _domains() -> dict:
    payload = yaml.safe_load(DOMAINS_PATH.read_text(encoding="utf-8")) or {}
    domains = payload.get("domains") or {}
    assert isinstance(domains, dict)
    return domains


def _validate(data: dict) -> list[str]:
    try:
        from jsonschema import Draft202012Validator  # type: ignore[import-untyped]
    except ImportError:
        pytest.skip("jsonschema not available")
    validator = Draft202012Validator(_load_schema())
    return [
        e.message
        for e in sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    ]


def test_all_24_overlays_validate() -> None:
    schema_text = SCHEMA_PATH.read_text(encoding="utf-8")
    assert schema_text  # schema exists
    domains = _domains()
    assert len(domains) == 24, f"expected 24 domains, got {len(domains)}"
    for name, data in sorted(domains.items()):
        errs = _validate(data)
        assert not errs, f"{name} schema errors: {errs}"


def test_overlay_with_allow_issue_write_must_fail_schema() -> None:
    valid = dict(_domains()["docs"])
    bad = dict(valid)
    bad["ALLOW_ISSUE_WRITE"] = True
    errs = _validate(bad)
    assert errs, "ALLOW_ISSUE_WRITE overlay must fail schema/lint"
    assert any(
        "ALLOW" in e or "not" in e.lower() or "additional" in e.lower() for e in errs
    )


def test_missing_required_field_must_fail() -> None:
    valid = dict(_domains()["docs"])
    bad = dict(valid)
    bad.pop("OBJECT", None)
    errs = _validate(bad)
    assert errs, "missing OBJECT must fail schema"
    assert any("OBJECT" in e or "required" in e.lower() for e in errs)
