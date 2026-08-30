"""P1 #9808 — profile precedence (DOCX гл.4.3)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from scripts.ai.prompts.compile import compile_one

pytestmark = pytest.mark.unit

PROMPTS_ROOT = (
    Path(__file__).resolve().parents[2] / "docs" / "00-project" / "ai" / "prompts"
)
PROFILES_DIR = PROMPTS_ROOT / "profiles"


def _load_profile(name: str) -> dict:
    return (
        yaml.safe_load((PROFILES_DIR / f"{name}.yaml").read_text(encoding="utf-8"))
        or {}
    )


def test_audit_readonly_profile_fail_closed() -> None:
    data = _load_profile("audit-readonly")
    assert data["MODE"] == "audit"
    for key in ("ALLOW_ISSUE_WRITE", "ALLOW_PUSH", "ALLOW_MERGE", "ALLOW_CLOSE"):
        assert data[key] is False, f"{key} must be false in audit-readonly"


def test_full_write_profile_allows_mutations() -> None:
    data = _load_profile("full-write")
    assert data["MODE"] == "full"
    for key in ("ALLOW_ISSUE_WRITE", "ALLOW_PUSH", "ALLOW_MERGE", "ALLOW_CLOSE"):
        assert data[key] is True, f"{key} must be true in full-write"


def test_differential_profile_audit_mode() -> None:
    data = _load_profile("differential")
    assert data["AUDIT_MODE"] == "differential"
    assert data["MODE"] == "audit"


def test_compile_respects_profile_mode() -> None:
    readonly = compile_one("docs", "audit-readonly")
    full = compile_one("docs", "full-write")
    diff = compile_one("docs", "differential")
    for r in (readonly, full, diff):
        assert r["error"] is None, r["error"]
    assert readonly["params"]["MODE"] == "audit"  # type: ignore[index]
    assert full["params"]["MODE"] == "full"  # type: ignore[index]
    assert diff["params"]["AUDIT_MODE"] == "differential"  # type: ignore[index]
    # ALLOW_* precedence follows profile, not overlay
    assert readonly["params"]["ALLOW_ISSUE_WRITE"] is False  # type: ignore[index]
    assert full["params"]["ALLOW_ISSUE_WRITE"] is True  # type: ignore[index]
