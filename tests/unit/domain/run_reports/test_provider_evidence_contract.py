"""Saved provider facts must never turn missing or inapplicable probes into OK."""

import pytest

from bioetl.domain.run_reports.selected_status import (
    _clean_candidate_name,
    provider_check_rows,
    provider_selector_options,
)

pytestmark = pytest.mark.unit


def test_cached_bronze_does_not_claim_remote_probe():
    report = {"identity": {"provider": "pubmed"}, "io": {"use_cached_bronze": True}}
    assert provider_check_rows(report) == [
        {
            "provider": "pubmed",
            "check_result": "N/A",
            "evidence": "N/A",
            "observed_at": None,
        }
    ]


@pytest.mark.parametrize("verdict, expected", [("N/A", "N/A"), ("invented", "UNKNOWN")])
def test_saved_probe_verdict_is_bounded_by_supported_evidence(verdict, expected):
    report = {
        "observations": {
            "Provider": {"verdict": verdict, "facts": {"provider": "pubmed"}}
        }
    }
    row = provider_check_rows(report)[0]
    assert row["check_result"] == expected
    assert row["evidence"] == ("N/A" if expected == "N/A" else "PRESENT")
    assert provider_selector_options(report) == [{"text": "pubmed", "value": "pubmed"}]


@pytest.mark.parametrize("candidate", [None, 42, "—", "", "   ", " pubmed "])
def test_selector_excludes_missing_placeholder_and_duplicate_names(candidate):
    assert _clean_candidate_name(candidate, ["pubmed"]) == ""
