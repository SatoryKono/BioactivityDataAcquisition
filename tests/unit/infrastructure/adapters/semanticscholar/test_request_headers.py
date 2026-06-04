"""Tests for Semantic Scholar request-header helpers."""

from __future__ import annotations

import pytest

from bioetl.infrastructure.adapters.semanticscholar.request_headers import (
    build_semanticscholar_headers,
)

pytestmark = pytest.mark.unit


def test_build_semanticscholar_headers_includes_content_type_and_api_key() -> None:
    headers = build_semanticscholar_headers(
        "real-api-key",
        include_content_type=True,
        skip_placeholder_api_key=True,
    )

    assert headers == {
        "User-Agent": "BioETL/1.0",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "x-api-key": "real-api-key",
    }


def test_build_semanticscholar_headers_skips_placeholder_api_key() -> None:
    headers = build_semanticscholar_headers(
        "your-api-key-here",
        include_content_type=False,
        skip_placeholder_api_key=True,
    )

    assert headers == {
        "User-Agent": "BioETL/1.0",
        "Accept": "application/json",
    }


def test_build_semanticscholar_headers_keeps_placeholder_when_not_skipping() -> None:
    headers = build_semanticscholar_headers(
        "your-api-key-here",
        include_content_type=False,
        skip_placeholder_api_key=False,
    )

    assert headers["x-api-key"] == "your-api-key-here"
