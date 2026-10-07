"""Canonical transformer collaborator wiring for composition-owned defaults."""

from __future__ import annotations

from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.application.core.wiring.transformer import (
    DefaultContractPolicy,
    NoOpStructuralPolicy,
    StructuralPolicyProtocol,
    TransformerDependencyContext,
)
from bioetl.composition.observability_resolution import (
    resolve_metrics_port,
    resolve_tracing_port,
)
from bioetl.composition.runtime_builders.config_access import (
    _load_publication_type_classification_data,
    load_settings,
    resolve_configs_root,
)
from bioetl.domain.behavior import DefaultDataNormalizer, EntityIdentityGenerator
from bioetl.domain.ports import (
    ContractPolicyProtocol,
    DataNormalizationPort,
    MetricsPort,
    PiiHasherPort,
    TracingPort,
)
from bioetl.domain.ports.noop import NoOpPiiHasher
import bioetl.infrastructure.config.publication_controlled_vocabulary_loader as publication_vocabulary_loader
from bioetl.infrastructure.security.pii_hasher import Sha256PiiHasher

if TYPE_CHECKING:
    from bioetl.domain.mapping.publication_controlled_vocabulary import (
        PublicationControlledVocabularyRegistry,
    )

__all__ = [
    "build_transformer_dependencies",
    "load_publication_controlled_vocabulary",
    "publication_vocabulary_kwargs",
]


def _default_pii_hasher() -> PiiHasherPort:
    """Return the configured PII hasher, with a salt-free safe fallback."""
    settings = load_settings()
    if settings.pii_salt_current is None:
        return NoOpPiiHasher()
    return Sha256PiiHasher.from_settings(settings)


def build_transformer_dependencies(
    *,
    tracer: TracingPort | None = None,
    metrics: MetricsPort | None = None,
    identity_service: EntityIdentityGenerator | None = None,
    pii_hasher: PiiHasherPort | None = None,
    data_normalizer: DataNormalizationPort | None = None,
    contract_policy: ContractPolicyProtocol | None = None,
    structural_policy: StructuralPolicyProtocol | None = None,
) -> TransformerDependencyContext:
    """Build explicit transformer collaborators in the composition layer."""
    return TransformerDependencyContext(
        tracer=resolve_tracing_port(tracer=tracer),
        metrics=resolve_metrics_port(metrics=metrics),
        identity_service=(
            identity_service
            if identity_service is not None
            else EntityIdentityGenerator()
        ),
        pii_hasher=pii_hasher if pii_hasher is not None else _default_pii_hasher(),
        data_normalizer=(
            data_normalizer if data_normalizer is not None else DefaultDataNormalizer()
        ),
        contract_policy=(
            contract_policy if contract_policy is not None else DefaultContractPolicy()
        ),
        structural_policy=(
            structural_policy
            if structural_policy is not None
            else NoOpStructuralPolicy()
        ),
    )


@cache
def _load_publication_controlled_vocabulary_data(
    configs_root_key: str,
) -> PublicationControlledVocabularyRegistry:
    """Load publication controlled vocabulary once per configs root key."""

    return publication_vocabulary_loader.PublicationControlledVocabularyLoader(
        Path(configs_root_key)
    ).load()


def load_publication_controlled_vocabulary(
    configs_root: Path,
) -> PublicationControlledVocabularyRegistry:
    """Return the cached vocabulary for one configs root."""

    return _load_publication_controlled_vocabulary_data(str(configs_root))


_BASE_PUBLICATION_TRANSFORMER = (
    "bioetl.application.pipelines.common.base_publication_transformer",
    "BasePublicationTransformer",
)


def _accepts_publication_vocabulary(transformer_class: type[object]) -> bool:
    """Recognize publication transformers without importing their module."""

    lineage = getattr(transformer_class, "__mro__", ())
    if not isinstance(lineage, tuple):
        return False
    return any(
        (cls.__module__, cls.__name__) == _BASE_PUBLICATION_TRANSFORMER
        for cls in lineage
    )


def publication_vocabulary_kwargs(transformer_class: type[object]) -> dict[str, object]:
    """Pass the loaded vocabulary only into publication transformers."""

    if not _accepts_publication_vocabulary(transformer_class):
        return {}
    configs_root = resolve_configs_root(None)
    return {
        "publication_vocabulary": load_publication_controlled_vocabulary(configs_root),
        "publication_classification": _load_publication_type_classification_data(
            str(configs_root)
        ),
    }
