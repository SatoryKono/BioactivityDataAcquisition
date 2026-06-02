"""Tests for PubChem property-URN vocabulary extraction."""

from __future__ import annotations

import pytest

from pathlib import Path

import yaml

from scripts.engineering.qa.extract_pubchem_property_vocab import (
    extract_pubchem_property_vocab,
)


pytestmark = pytest.mark.unit


def test_extract_pubchem_property_vocab_matches_expected_fixture_subset() -> None:
    payload = extract_pubchem_property_vocab(
        [Path("tests/fixtures/bronze/pubchem/compound/sample_ci_2026-04-24.jsonl")]
    )
    expected = yaml.safe_load(
        Path(
            "tests/fixtures/normalization/pubchem_property_vocab_expected.yaml"
        ).read_text(encoding="utf-8")
    )

    assert payload == expected
