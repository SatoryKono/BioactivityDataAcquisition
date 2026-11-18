"""ESearch accepts JSON integer counts as well as NCBI's decimal strings."""

from __future__ import annotations

import pytest

from bioetl.infrastructure.adapters.pubmed._errors import parse_esearch_payload

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("count", [0, 1, 12000])
def test_esearch_payload_preserves_json_integer_count(count: int) -> None:
    ids = ["12345678"] if count else []
    payload = {"esearchresult": {"idlist": ids, "count": count}}

    assert parse_esearch_payload(payload) == (ids, count)


@pytest.mark.parametrize(
    "count", [None, True, False, 1.5, [], {}, "unknown", "1.5", ""]
)
def test_esearch_payload_treats_unusable_count_as_unknown(count: object) -> None:
    payload = {"esearchresult": {"idlist": ["12345678"], "count": count}}

    assert parse_esearch_payload(payload) == (["12345678"], None)
