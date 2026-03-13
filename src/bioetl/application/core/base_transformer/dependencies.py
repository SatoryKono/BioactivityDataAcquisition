"""Explicit dependency bundle and compatibility resolver for transformers."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.application.core.base_transformer.contract_policy import (
    _DefaultContractPolicy,
)
from bioetl.domain.ports import (
    ContractPolicyPort,
    DataNormalizationPort,
    MetricsPort,
    NoOpMetrics,
    NoOpPiiHasher,
    NoOpTracing,
    PiiHasherPort,
    TracingPort,
)
from bioetl.domain.services import DataNormalizationService, IdentityService


@dataclass(frozen=True, slots=True)
class TransformerDependencyContext:
    """Resolved collaborator bundle for transformer runtime behavior."""

    tracer: TracingPort
    metrics: MetricsPort
    identity_service: IdentityService
    pii_hasher: PiiHasherPort
    data_normalizer: DataNormalizationPort
    contract_policy: ContractPolicyPort


def build_compat_transformer_dependencies() -> TransformerDependencyContext:
    """Build compatibility defaults for direct/test transformer construction."""
    return TransformerDependencyContext(
        tracer=NoOpTracing(),
        metrics=NoOpMetrics(),
        identity_service=IdentityService(),
        pii_hasher=NoOpPiiHasher(),
        data_normalizer=DataNormalizationService(),
        contract_policy=_DefaultContractPolicy(),
    )


def resolve_transformer_dependencies(
    *,
    dependencies: TransformerDependencyContext | None = None,
    tracer: TracingPort | None = None,
    metrics: MetricsPort | None = None,
    identity_service: IdentityService | None = None,
    pii_hasher: PiiHasherPort | None = None,
    data_normalizer: DataNormalizationPort | None = None,
    contract_policy: ContractPolicyPort | None = None,
) -> TransformerDependencyContext:
    """Resolve transformer collaborators without constructing them in ``BaseTransformer``."""

    if dependencies is not None:
        return dependencies

    compat_defaults: TransformerDependencyContext | None = None

    def _compat_defaults() -> TransformerDependencyContext:
        nonlocal compat_defaults
        if compat_defaults is None:
            compat_defaults = build_compat_transformer_dependencies()
        return compat_defaults

    return TransformerDependencyContext(
        tracer=tracer if tracer is not None else _compat_defaults().tracer,
        metrics=metrics if metrics is not None else _compat_defaults().metrics,
        identity_service=(
            identity_service
            if identity_service is not None
            else _compat_defaults().identity_service
        ),
        pii_hasher=(
            pii_hasher if pii_hasher is not None else _compat_defaults().pii_hasher
        ),
        data_normalizer=(
            data_normalizer
            if data_normalizer is not None
            else _compat_defaults().data_normalizer
        ),
        contract_policy=(
            contract_policy
            if contract_policy is not None
            else _compat_defaults().contract_policy
        ),
    )
