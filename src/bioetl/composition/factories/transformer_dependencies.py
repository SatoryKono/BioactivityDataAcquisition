"""Canonical transformer collaborator wiring for composition-owned defaults."""

from __future__ import annotations

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
from bioetl.domain.ports import (
    ContractPolicyProtocol,
    DataNormalizationPort,
    MetricsPort,
    PiiHasherPort,
    TracingPort,
)
from bioetl.domain.ports.noop import NoOpPiiHasher
from bioetl.domain.services import DefaultDataNormalizer, EntityIdentityGenerator

__all__ = ["build_transformer_dependencies"]


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
        pii_hasher=pii_hasher if pii_hasher is not None else NoOpPiiHasher(),
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
