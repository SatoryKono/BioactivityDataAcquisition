"""Unit tests for OpenAlex adapter helper mixin."""

from __future__ import annotations

import pytest

from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)
from bioetl.infrastructure.adapters.openalex.client_helpers_adapter_mixin import (
    OpenAlexAdapterHelpersMixin,
)

pytestmark = pytest.mark.unit

LEGACY_HTTP_DOI = "http" + "://doi.org/10.1000/xyz"


class _OpenAlexHelpersHarness(OpenAlexAdapterHelpersMixin):
    def __init__(self, mailto: str = "bioetl@example.org") -> None:
        self.mailto = mailto
        self._request_collector = APIRequestCollector()


def test_normalize_doi_supports_known_prefixes() -> None:
    assert _OpenAlexHelpersHarness._normalize_doi("https://doi.org/10.1000/xyz") == (
        "10.1000/xyz"
    )
    assert _OpenAlexHelpersHarness._normalize_doi(LEGACY_HTTP_DOI) == ("10.1000/xyz")
    assert _OpenAlexHelpersHarness._normalize_doi("doi:10.1000/xyz") == "10.1000/xyz"
    assert _OpenAlexHelpersHarness._normalize_doi(" 10.1000/xyz ") == "10.1000/xyz"
    assert _OpenAlexHelpersHarness._normalize_doi("") is None


def test_escape_title_for_search_normalizes_separators() -> None:
    escaped = _OpenAlexHelpersHarness._escape_title_for_search("A: B, C | D")
    assert escaped == "A+B+C+D"


def test_extract_doi_from_record_handles_url_and_plain_values() -> None:
    assert (
        _OpenAlexHelpersHarness._extract_doi_from_record(
            {"doi": "https://doi.org/10.1000/XYZ"}
        )
        == "10.1000/xyz"
    )
    assert _OpenAlexHelpersHarness._extract_doi_from_record({"doi": "10.1000/XYZ"}) == (
        "10.1000/xyz"
    )
    assert _OpenAlexHelpersHarness._extract_doi_from_record({"doi": ""}) is None


def test_health_helpers_return_expected_defaults() -> None:
    harness = _OpenAlexHelpersHarness()
    assert harness._fallback_health_status() == HealthStatus.UNHEALTHY
    assert harness._get_health_endpoint() == "/works"
    assert harness._build_base_params() == {"mailto": "bioetl@example.org"}
