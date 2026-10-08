"""PubMed publication-term enricher wiring for composition registration."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from bioetl.application.pipelines.pubmed.publication_term_enricher import (
    PubMedPublicationTermEnrichmentService,
)
from bioetl.composition.providers._registration_biblio_adapters import (
    _build_pubmed_adapter_from_settings,
)
from bioetl.composition.providers._registration_contracts import (
    resolve_provider_assembly_support,
)
from bioetl.domain.exceptions import BioETLError
from bioetl.infrastructure.adapters.pubmed import PubMedAdapter

if TYPE_CHECKING:
    from bioetl.composition.providers._models import ProviderSettingsProtocol
    from bioetl.composition.providers._registration_contracts import (
        ProviderAssemblySupport,
    )
    from bioetl.domain.ports import LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

__all__ = [
    "create_pubmed_publication_term_enricher",
]


def _resolve_pubmed_email(
    settings: ProviderSettingsProtocol | None,
    pipeline_config: PipelineYamlConfig | None,
) -> str | None:
    if pipeline_config is not None:
        source = getattr(pipeline_config, "source", None)
        raw_email = getattr(source, "email", None) if source is not None else None
        if isinstance(raw_email, str) and raw_email.strip():
            return raw_email.strip()
    default_email = (
        None if settings is None else getattr(settings, "default_email", None)
    )
    if isinstance(default_email, str) and default_email.strip():
        return default_email.strip()
    return None


def create_pubmed_publication_term_enricher(
    *,
    settings: ProviderSettingsProtocol,
    logger: LoggerPort,
    metrics: MetricsPort | None = None,
    assembly_support: ProviderAssemblySupport | None = None,
    pipeline_config: PipelineYamlConfig | None = None,
) -> PubMedPublicationTermEnrichmentService | None:
    """Build a PubMed enricher, or skip when email/adapter assembly is unavailable."""
    email = _resolve_pubmed_email(settings, pipeline_config)
    if email is None:
        logger.warning(
            "publication_term_pubmed_enricher_skipped",
            reason="missing_pubmed_email",
        )
        return None
    try:
        support = resolve_provider_assembly_support(assembly_support)
        http_client = support.create_http_client(
            "pubmed", settings, metrics=metrics, logger=logger
        )
        adapter = _build_pubmed_adapter_from_settings(
            adapter_cls=PubMedAdapter,
            http_client=cast("UnifiedHTTPClient", http_client),
            logger=logger,
            settings=settings,
            email=email,
            metrics=metrics,
        )
    except (BioETLError, OSError, RuntimeError, ValueError) as exc:
        logger.warning(
            "publication_term_pubmed_enricher_unavailable",
            error=str(exc),
        )
        return None
    return PubMedPublicationTermEnrichmentService(
        pubmed_source=adapter,
        logger=logger,
    )
