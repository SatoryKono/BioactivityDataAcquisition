"""Unit tests for CrossRef business-data builder helpers."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest


def _load_business_data_builder_module() -> object:
    module_path = (
        Path(__file__).resolve().parents[5]
        / "src"
        / "bioetl"
        / "application"
        / "pipelines"
        / "crossref"
        / "_business_data_builder.py"
    )
    spec = importlib.util.spec_from_file_location(
        "_test_crossref_business_data_builder_module",
        module_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module spec for {module_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


builder = _load_business_data_builder_module()


class _StubNormalizer:
    """Simple normalizer stub used by business-data builder tests."""

    def normalize_author_list(self, raw_authors: list[dict[str, object]]) -> str:
        return json.dumps([author.get("name") for author in raw_authors])

    def normalize_author_keys(self, raw_authors: list[dict[str, object]]) -> str:
        return json.dumps([author.get("ORCID") for author in raw_authors])

    def normalize_affiliations(self, affiliations: object) -> str | None:
        if affiliations is None:
            return None
        return json.dumps(affiliations)


@pytest.mark.parametrize(
    ("published_print", "published_online", "expected"),
    [
        ("2024-01-01", "2024-02-01", "2024-01-01"),
        (None, "2024-02-01", "2024-02-01"),
        (None, None, None),
    ],
)
def test_compute_publication_date_prefers_print(
    published_print: str | None,
    published_online: str | None,
    expected: str | None,
) -> None:
    assert (
        builder.compute_publication_date(published_print, published_online) == expected
    )


def test_hash_author_details_hashes_pii_and_preserves_non_pii() -> None:
    hashed = builder.hash_author_details(
        [
            {
                "given": "Ada",
                "family": "Lovelace",
                "name": "Ada Lovelace",
                "orcid": "0000-0001",
                "authenticated_orcid": True,
                "sequence": "first",
                "affiliations": [{"name": "Analytical Engine"}],
            },
            {
                "given": "",
                "family": None,
                "name": "Anonymous",
            },
        ],
        hash_pii_value=lambda value: f"hash:{value}" if value else None,
    )

    assert hashed == [
        {
            "given": "hash:Ada",
            "family": "hash:Lovelace",
            "name": "hash:Ada Lovelace",
            "orcid": "0000-0001",
            "authenticated_orcid": True,
            "sequence": "first",
            "affiliations": [{"name": "Analytical Engine"}],
        },
        {
            "given": None,
            "family": None,
            "name": "hash:Anonymous",
            "orcid": None,
            "authenticated_orcid": None,
            "sequence": None,
            "affiliations": [],
        },
    ]


@pytest.mark.parametrize(
    ("record", "expected"),
    [
        ({"published-print": {"date-parts": [[2024, 1, 1]]}}, 2024),
        ({"published-online": {"date-parts": [["2025", 2, 3]]}}, 2025),
        ({"issued": {"date-parts": [[1999]]}}, 1999),
        ({"published-print": {"date-parts": []}}, None),
        ({"published-print": {"date-parts": ["bad-shape"]}}, None),
        ({"issued": {"date-parts": [["not-a-year"]]}}, None),
        ({}, None),
    ],
)
def test_extract_publication_year_candidate_handles_supported_shapes(
    record: dict[str, object],
    expected: int | None,
) -> None:
    assert builder.extract_publication_year_candidate(record) == expected


def test_extract_author_bundle_normalizes_and_hashes_author_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        builder,
        "extract_authors",
        lambda record: [{"name": "Ada", "ORCID": "0000-0001"}],
    )
    monkeypatch.setattr(
        builder,
        "extract_author_details",
        lambda record: [
            {
                "given": "Ada",
                "family": "Lovelace",
                "name": "Ada Lovelace",
                "orcid": "0000-0001",
                "authenticated_orcid": True,
                "sequence": "first",
                "affiliations": ["Analytical Engine"],
            },
            {
                "given": "Grace",
                "family": "Hopper",
                "name": "Grace Hopper",
                "affiliations": [{"name": "US Navy"}],
            },
        ],
    )
    monkeypatch.setattr(builder, "extract_author_orcids", lambda record: ["0000-0001"])

    result = builder._extract_author_bundle(
        {},
        data_normalizer=_StubNormalizer(),
        hash_pii_value=lambda value: f"hash:{value}" if value else None,
        serialize_json=lambda value: json.dumps(value, sort_keys=True),
        serialize_json_list=lambda value: (
            json.dumps(value) if value is not None else None
        ),
    )

    assert result["authors"] == '["Ada"]'
    assert result["author_keys"] == '["0000-0001"]'
    assert result["author_orcids"] == '["0000-0001"]'
    assert '"given": "hash:Ada"' in (result["author_details"] or "")
    assert result["affiliation_list"] == json.dumps([{"name": "US Navy"}])


def test_extract_author_bundle_uses_string_affiliations_when_dicts_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(builder, "extract_authors", lambda record: [])
    monkeypatch.setattr(
        builder,
        "extract_author_details",
        lambda record: [{"affiliations": ["Org A", 123]}],
    )
    monkeypatch.setattr(builder, "extract_author_orcids", lambda record: [])

    result = builder._extract_author_bundle(
        {},
        data_normalizer=_StubNormalizer(),
        hash_pii_value=lambda value: value,
        serialize_json=lambda value: json.dumps(value),
        serialize_json_list=lambda value: (
            json.dumps(value) if value is not None else None
        ),
    )

    assert result["affiliation_list"] == json.dumps(["Org A"])


def test_extract_author_bundle_returns_none_for_non_list_affiliations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    normalizer = MagicMock()
    normalizer.normalize_author_list.return_value = "[]"
    normalizer.normalize_author_keys.return_value = "[]"
    normalizer.normalize_affiliations.return_value = None
    monkeypatch.setattr(builder, "extract_authors", lambda record: [])
    monkeypatch.setattr(
        builder,
        "extract_author_details",
        lambda record: [{"affiliations": "not-a-list"}],
    )
    monkeypatch.setattr(builder, "extract_author_orcids", lambda record: [])

    result = builder._extract_author_bundle(
        {},
        data_normalizer=normalizer,
        hash_pii_value=lambda value: value,
        serialize_json=lambda value: {"not": "a-string"},
        serialize_json_list=lambda value: (
            json.dumps(value) if value is not None else None
        ),
    )

    normalizer.normalize_affiliations.assert_called_once_with(None)
    assert result["author_details"] is None
    assert result["affiliation_list"] is None


def test_build_crossref_business_data_assembles_expected_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        builder,
        "extract_journal_info",
        lambda record: {"journal_name": "Journal of Tests"},
    )
    monkeypatch.setattr(builder, "extract_page_info", lambda record: {"pages": "1-10"})
    monkeypatch.setattr(
        builder,
        "extract_dates",
        lambda record: {
            "published_print": "2024-01-01",
            "published_online": "2024-02-02",
        },
    )
    monkeypatch.setattr(
        builder,
        "extract_content_domain",
        lambda record: {
            "content_domain_domains": ["biology"],
            "content_domain_crossmark_restriction": False,
        },
    )
    monkeypatch.setattr(
        builder,
        "extract_issn_by_type",
        lambda record: {"issn_print": "1111-1111", "issn_electronic": "2222-2222"},
    )
    monkeypatch.setattr(builder, "extract_published_date", lambda record: "2024-01-01")
    monkeypatch.setattr(
        builder, "extract_references", lambda record: [{"doi": "10.1/ref"}]
    )
    monkeypatch.setattr(
        builder,
        "extract_authors",
        lambda record: [{"name": "Ada", "ORCID": "0000-0001"}],
    )
    monkeypatch.setattr(
        builder,
        "extract_author_details",
        lambda record: [
            {
                "given": "Ada",
                "family": "Lovelace",
                "name": "Ada Lovelace",
                "orcid": "0000-0001",
                "authenticated_orcid": True,
                "sequence": "first",
                "affiliations": [{"name": "Analytical Engine"}],
            }
        ],
    )
    monkeypatch.setattr(builder, "extract_author_orcids", lambda record: ["0000-0001"])
    monkeypatch.setattr(
        builder, "extract_license_url", lambda record: "https://license.test"
    )
    monkeypatch.setattr(
        builder, "extract_first_string", lambda value: value[0] if value else None
    )

    record: dict[str, Any] = {
        "DOI": "10.1234/example",
        "type": "journal-article",
        "title": ["Example title"],
        "short-container-title": ["J Tests"],
        "subject": ["chemistry"],
        "language": "en",
        "is-referenced-by-count": 5,
        "references-count": 2,
        "_lookup_method": "doi",
        "_original_id": "10.1234/example",
        "alternative-id": ["alt-1"],
        "published-print": {"date-parts": [[2024, 1, 1]]},
    }

    result = builder.build_crossref_business_data(
        record,
        data_normalizer=_StubNormalizer(),
        validate_doi=lambda value: str(value),
        validate_publication_year=lambda value: (
            int(value) if value is not None else None
        ),
        classify_publication_type=lambda value: {
            "publication_category": f"classified:{value}"
        },
        serialize_json=lambda value: json.dumps(value, sort_keys=True),
        serialize_json_list=lambda value: (
            json.dumps(value) if value is not None else None
        ),
        hash_pii_value=lambda value: f"hash:{value}" if value else None,
    )

    assert result["doi"] == "10.1234/example"
    assert result["title"] == "Example title"
    assert result["authors"] == '["Ada"]'
    assert result["publication_year"] == 2024
    assert result["publication_date"] == "2024-01-01"
    assert result["publication_type"] == "journal-article"
    assert result["publication_category"] == "classified:journal-article"
    assert result["license_url"] == "https://license.test"
    assert result["references"] == '[{"doi": "10.1/ref"}]'
    assert result["_source"] == "crossref"
    assert result["_dq_warn"] is False
    assert result["_dq_error"] is False


def test_build_crossref_business_data_falls_back_to_online_publication_date(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(builder, "extract_journal_info", lambda record: {})
    monkeypatch.setattr(builder, "extract_page_info", lambda record: {})
    monkeypatch.setattr(
        builder,
        "extract_dates",
        lambda record: {"published_print": None, "published_online": "2024-02-02"},
    )
    monkeypatch.setattr(
        builder,
        "extract_content_domain",
        lambda record: {
            "content_domain_domains": [],
            "content_domain_crossmark_restriction": None,
        },
    )
    monkeypatch.setattr(builder, "extract_issn_by_type", lambda record: {})
    monkeypatch.setattr(builder, "extract_published_date", lambda record: None)
    monkeypatch.setattr(builder, "extract_references", lambda record: [])
    monkeypatch.setattr(builder, "extract_authors", lambda record: [])
    monkeypatch.setattr(builder, "extract_author_details", lambda record: [])
    monkeypatch.setattr(builder, "extract_author_orcids", lambda record: [])
    monkeypatch.setattr(builder, "extract_license_url", lambda record: None)
    monkeypatch.setattr(builder, "extract_first_string", lambda value: None)

    result = builder.build_crossref_business_data(
        {"DOI": "10.1234/example", "type": None, "subject": []},
        data_normalizer=_StubNormalizer(),
        validate_doi=lambda value: str(value),
        validate_publication_year=lambda value: value,
        classify_publication_type=lambda value: {},
        serialize_json=lambda value: json.dumps(value),
        serialize_json_list=lambda value: (
            json.dumps(value) if value is not None else None
        ),
        hash_pii_value=lambda value: value,
    )

    assert result["publication_date"] == "2024-02-02"


def test_build_crossref_business_data_requires_validated_doi() -> None:
    with pytest.raises(AssertionError, match="DOI should be validated"):
        builder.build_crossref_business_data(
            {"DOI": None},
            data_normalizer=_StubNormalizer(),
            validate_doi=lambda value: None,
            validate_publication_year=lambda value: None,
            classify_publication_type=lambda value: {},
            serialize_json=lambda value: json.dumps(value),
            serialize_json_list=lambda value: json.dumps(value),
            hash_pii_value=lambda value: value,
        )
