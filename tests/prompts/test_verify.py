"""Contract verify for generated prompt catalog (P1 #9808)."""

from __future__ import annotations

import pytest
from scripts.ai.prompts.compile import compile_one
from scripts.ai.prompts.verify import (
    VerifyReport,
    _parse_params_header,
    _parse_provenance_header,
    check_fingerprint_stability,
    format_report,
    verify_all,
)

pytestmark = pytest.mark.unit


def test_verify_all_catalog_ok() -> None:
    report = verify_all(golden=False)
    assert report.ok, format_report(report)
    assert report.stats["generated_files"] > 0
    assert report.stats["errors"] == 0


def test_fingerprint_stability_check_is_silent_on_ok() -> None:
    report = VerifyReport()
    check_fingerprint_stability(report)
    assert report.ok
    assert not report.errors


def test_header_parsers_accept_compile_output() -> None:
    result = compile_one("docs", "audit-readonly")
    assert result["error"] is None
    text = result["rendered_text"]
    assert isinstance(text, str)
    provenance = _parse_provenance_header(text)
    params = _parse_params_header(text)
    assert provenance is not None
    assert "prompt_sha8" in provenance
    assert provenance["profile"] == "audit-readonly"
    assert params is not None
    assert params["MODE"] == "audit"
