"""Canonical transformer collaborator wiring for composition-owned defaults."""

from __future__ import annotations

from bioetl.application.core.base_transformer.contract_policy import (
    DefaultContractPolicy,
)
from bioetl.application.core.base_transformer.structural_policy import (
    NoOpStructuralPolicy,
    StructuralPolicyProtocol,
)
from bioetl.application.core.base_transformer.types import (
    TransformerDependencyContext,
)
from bioetl.domain.ports import (
    ContractPolicyPort,
    DataNormalizationPort,
    MetricsPort,
    PiiHasherPort,
    TracingPort,
)
from bioetl.domain.ports.noop import (
    NoOpMetrics,
    NoOpPiiHasher,
    NoOpTracing,
)
from bioetl.domain.services import DataNormalizationService, IdentityService

__all__ = ["build_transformer_dependencies"]


def build_transformer_dependencies(
    *,
    tracer: TracingPort | None = None,
    metrics: MetricsPort | None = None,
    identity_service: IdentityService | None = None,
    pii_hasher: PiiHasherPort | None = None,
    data_normalizer: DataNormalizationPort | None = None,
    contract_policy: ContractPolicyPort | None = None,
    structural_policy: StructuralPolicyProtocol | None = None,
) -> TransformerDependencyContext:
    """Build explicit transformer collaborators in the composition layer."""
    return TransformerDependencyContext(
        tracer=tracer if tracer is not None else NoOpTracing(),
        metrics=metrics if metrics is not None else NoOpMetrics(),
        identity_service=(
            identity_service if identity_service is not None else IdentityService()
        ),
        pii_hasher=pii_hasher if pii_hasher is not None else NoOpPiiHasher(),
        data_normalizer=(
            data_normalizer
            if data_normalizer is not None
            else DataNormalizationService()
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
