"""Request-profile helpers for bibliographic provider registration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.composition.providers._config_helpers import _normalize_optional_override
from bioetl.composition.providers._models import ProviderSettingsProtocol

if TYPE_CHECKING:
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


@dataclass(frozen=True)
class MailtoBatchProfile:
    """Resolved mailto + batch settings for polite-pool biblio providers."""

    mailto: str | None
    batch_size: int


@dataclass(frozen=True)
class OpenAlexRequestProfile:
    """Resolved OpenAlex request credentials and batch settings."""

    api_key: str | None
    mailto: str | None
    batch_size: int


@dataclass(frozen=True)
class PubMedRequestProfile:
    """Resolved PubMed request credentials for data-source assembly."""

    email: str | None
    api_key: str | None


@dataclass(frozen=True)
class SemanticScholarRequestProfile:
    """Resolved Semantic Scholar request settings."""

    api_key: str
    batch_size: int


def _resolve_biblio_contact_email(
    settings: ProviderSettingsProtocol,
    pipeline_config: PipelineYamlConfig,
) -> str | None:
    """Resolve pipeline email override with settings fallback."""
    configured_email = _normalize_optional_override(pipeline_config.source.email)
    return configured_email or settings.default_email


def _resolve_pubmed_request_profile(
    settings: ProviderSettingsProtocol,
    pipeline_config: PipelineYamlConfig,
) -> PubMedRequestProfile:
    """Resolve PubMed email from pipeline and API key from typed Settings."""
    settings_api_key = (
        settings.pubmed_api_key.get_secret_value() if settings.pubmed_api_key else None
    )
    return PubMedRequestProfile(
        email=_resolve_biblio_contact_email(settings, pipeline_config),
        api_key=settings_api_key,
    )


def _resolve_mailto_batch_profile(
    settings: ProviderSettingsProtocol,
    pipeline_config: PipelineYamlConfig,
    *,
    batch_size: int,
) -> MailtoBatchProfile:
    """Resolve polite-pool mailto and batch size for a biblio provider."""
    return MailtoBatchProfile(
        mailto=_resolve_biblio_contact_email(settings, pipeline_config),
        batch_size=batch_size,
    )


def _resolve_openalex_request_profile(
    settings: ProviderSettingsProtocol,
    pipeline_config: PipelineYamlConfig,
    *,
    batch_size: int,
) -> OpenAlexRequestProfile:
    """Resolve OpenAlex API key from Settings, legacy mailto, and batch size."""
    settings_api_key = (
        settings.openalex_api_key.get_secret_value()
        if settings.openalex_api_key
        else None
    )
    return OpenAlexRequestProfile(
        api_key=settings_api_key,
        mailto=_resolve_biblio_contact_email(settings, pipeline_config),
        batch_size=batch_size,
    )


def _resolve_semanticscholar_request_profile(
    settings: ProviderSettingsProtocol,
    *,
    batch_size: int,
) -> SemanticScholarRequestProfile:
    """Resolve Semantic Scholar API key and batch defaults."""
    api_key = (
        settings.semanticscholar_api_key.get_secret_value()
        if settings.semanticscholar_api_key
        else ""
    )
    return SemanticScholarRequestProfile(
        api_key=api_key,
        batch_size=batch_size,
    )


__all__ = [
    "MailtoBatchProfile",
    "OpenAlexRequestProfile",
    "PubMedRequestProfile",
    "SemanticScholarRequestProfile",
    "_resolve_biblio_contact_email",
    "_resolve_mailto_batch_profile",
    "_resolve_openalex_request_profile",
    "_resolve_pubmed_request_profile",
    "_resolve_semanticscholar_request_profile",
]
