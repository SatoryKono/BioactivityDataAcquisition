# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
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


def _pipeline_config(*, email: str = "") -> SimpleNamespace:
    return SimpleNamespace(source=SimpleNamespace(email=email))


def test_resolve_pubmed_request_profile_uses_pipeline_email_and_settings_api_key() -> (
    None
):
    settings = MagicMock()
    settings.default_email = "default@example.org"
    settings.pubmed_api_key = MagicMock()
    settings.pubmed_api_key.get_secret_value.return_value = "settings-key"

    result = _resolve_pubmed_request_profile(
        settings,
        _pipeline_config(email="pipeline@example.org"),
    )

    assert result.email == "pipeline@example.org"
    assert result.api_key == "settings-key"



def test_resolve_pubmed_request_profile_ignores_pipeline_source_api_key() -> None:
    """REQ-SECRET-001: credentials stay on Settings, not pipeline.source.api_key."""
    settings = MagicMock()
    settings.default_email = "default@example.org"
    settings.pubmed_api_key = MagicMock()
    settings.pubmed_api_key.get_secret_value.return_value = "settings-key"

    pipeline = SimpleNamespace(
        source=SimpleNamespace(email="pipeline@example.org", api_key="pipeline-key"),
    )

    result = _resolve_pubmed_request_profile(settings, pipeline)

    assert result.email == "pipeline@example.org"
    assert result.api_key == "settings-key"


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


def test_resolve_openalex_request_profile_uses_settings_api_key() -> None:
    settings = MagicMock()
    settings.default_email = "default@example.org"
    settings.openalex_api_key = MagicMock()
    settings.openalex_api_key.get_secret_value.return_value = "settings-openalex-key"

    result = _resolve_openalex_request_profile(
        settings,
        _pipeline_config(email="pipeline@example.org"),
        batch_size=50,
    )

    assert result.api_key == "settings-openalex-key"
    assert result.mailto == "pipeline@example.org"
    assert result.batch_size == 50


def test_resolve_openalex_request_profile_ignores_pipeline_source_api_key() -> None:
    """REQ-SECRET-001: OpenAlex key stays on Settings, not pipeline.source.api_key."""
    settings = MagicMock()
    settings.default_email = "default@example.org"
    settings.openalex_api_key = MagicMock()
    settings.openalex_api_key.get_secret_value.return_value = "settings-openalex-key"
    pipeline = SimpleNamespace(
        source=SimpleNamespace(email="pipeline@example.org", api_key="test-token"),
    )

    result = _resolve_openalex_request_profile(
        settings,
        pipeline,
        batch_size=50,
    )

    assert result.api_key == "settings-openalex-key"
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
