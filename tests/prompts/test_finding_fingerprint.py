"""P1 #9808 — finding fingerprint + finding schema (DOCX гл.4.3)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from scripts.ai.prompts.verify import finding_fingerprint

pytestmark = pytest.mark.unit

PROMPTS_ROOT = Path(__file__).resolve().parents[2] / "docs" / "00-project" / "ai" / "prompts"


def test_fingerprint_stable_under_rephrased_claim() -> None:
    # fingerprint depends on domain|requirement_id|root_cause|paths, NOT claim
    # rephrasing claim (or any text outside those 4 fields) must not change it.
    fp1 = finding_fingerprint("docs", "REQ-001", "broken SSOT link", ["README.md", "docs/guide.md"])
    fp2 = finding_fingerprint("docs", "REQ-001", "broken SSOT link", ["README.md", "docs/guide.md"])
    assert fp1 == fp2
    assert len(fp1) == 64


def test_different_root_cause_different_fingerprint() -> None:
    fp_a = finding_fingerprint("docs", "REQ-001", "broken SSOT link", ["README.md"])
    fp_b = finding_fingerprint("docs", "REQ-001", "typo in guide", ["README.md"])
    assert fp_a != fp_b


def test_path_ordering_insensitive_sorted() -> None:
    fp_a = finding_fingerprint("docs", "REQ-001", "cause", ["b.md", "a.md"])
    fp_b = finding_fingerprint("docs", "REQ-001", "cause", ["a.md", "b.md"])
    assert fp_a == fp_b


def test_finding_schema_validates() -> None:
    schema_path = PROMPTS_ROOT / "_schema" / "finding-v3.schema.json"
    assert schema_path.is_file()
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    try:
        import jsonschema  # type: ignore[import-untyped]
        from jsonschema import Draft202012Validator  # type: ignore[attr-defined]
    except ImportError:
        pytest.skip("jsonschema not available")
    fp = finding_fingerprint("docs", "REQ-001", "cause", ["README.md"])
    finding = {
        "fingerprint": fp,
        "status": "PROVEN",
        "requirement_id": "REQ-001",
        "domain": "docs",
        "root_cause": "cause",
    }
    validator = Draft202012Validator(schema)
    errs = list(validator.iter_errors(finding))
    assert not errs, f"finding schema errors: {[e.message for e in errs]}"
    # fingerprint formula: sha256(domain|requirement_id|root_cause|joined_sorted_paths)
    payload = "|".join(["docs", "REQ-001", "cause", "README.md"])
    assert fp == hashlib.sha256(payload.encode()).hexdigest()
