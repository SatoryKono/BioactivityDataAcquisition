"""Canonical transformer collaborator wiring for composition-owned defaults."""

from __future__ import annotations

import os

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
from bioetl.domain.behavior import DefaultDataNormalizer, EntityIdentityGenerator
from bioetl.domain.ports import (
    ContractPolicyProtocol,
    DataNormalizationPort,
    MetricsPort,
    PiiHasherPort,
    TracingPort,
)
from bioetl.domain.ports.noop import NoOpPiiHasher
from bioetl.infrastructure.security.pii_hasher import Sha256PiiHasher

__all__ = ["build_transformer_dependencies"]


def _default_pii_hasher() -> PiiHasherPort:
    """Prefer salted SHA-256 hasher; fall back to NoOp only when salt is unset.

    Production deployments MUST set BIOETL_PII_SALT_CURRENT (or inject
    Sha256PiiHasher via composition). Unit tests without salt still construct
    transformers safely.
    """
    if not os.environ.get("BIOETL_PII_SALT_CURRENT", "").strip():
        return NoOpPiiHasher()
    return Sha256PiiHasher.from_env()


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
