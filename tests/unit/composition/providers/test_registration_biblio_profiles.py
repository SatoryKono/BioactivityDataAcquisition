"""Unit tests for bibliographic request-profile helpers."""

from __future__ import annotations

import pytest

from types import SimpleNamespace
from unittest.mock import MagicMock

from bioetl.composition.providers._registration_biblio_profiles import (
    _resolve_mailto_batch_profile,
    _resolve_openalex_request_profile,
    _resolve_pubmed_request_profile,
    _resolve_semanticscholar_request_profile,
)


pytestmark = pytest.mark.unit


def _pipeline_config(*, email: str = "", api_key: str = "") -> SimpleNamespace:
    return SimpleNamespace(source=SimpleNamespace(email=email, api_key=api_key))


def test_resolve_pubmed_request_profile_prefers_pipeline_overrides() -> None:
    settings = MagicMock()
    settings.default_email = "default@example.org"
    settings.pubmed_api_key = MagicMock()
    settings.pubmed_api_key.get_secret_value.return_value = "settings-key"

    result = _resolve_pubmed_request_profile(
        settings,
        _pipeline_config(email="pipeline@example.org", api_key="pipeline-key"),
    )

    assert result.email == "pipeline@example.org"
    assert result.api_key == "pipeline-key"


def test_resolve_mailto_batch_profile_uses_settings_fallback_and_provider_batch() -> (
    None
):
    settings = MagicMock()
    settings.default_email = "default@example.org"

    result = _resolve_mailto_batch_profile(
        settings,
        _pipeline_config(email=""),
        batch_size=55,
    )

    assert result.mailto == "default@example.org"
    assert result.batch_size == 55


def test_resolve_openalex_request_profile_prefers_pipeline_api_key() -> None:
    settings = MagicMock()
    settings.default_email = "default@example.org"
    settings.openalex_api_key = MagicMock()
    settings.openalex_api_key.get_secret_value.return_value = "settings-openalex-key"
    pipeline_token = "test-token"

    result = _resolve_openalex_request_profile(
        settings,
        _pipeline_config(
            email="pipeline@example.org",
            api_key=pipeline_token,
        ),
        batch_size=50,
    )

    assert result.api_key == pipeline_token
    assert result.mailto == "pipeline@example.org"
    assert result.batch_size == 50


def test_resolve_semanticscholar_request_profile_uses_empty_key_when_unconfigured() -> (
    None
):
    settings = MagicMock()
    settings.semanticscholar_api_key = None

    result = _resolve_semanticscholar_request_profile(
        settings,
        batch_size=100,
    )

    assert result.api_key == ""
    assert result.batch_size == 100
