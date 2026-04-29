"""Canonical composition-side builders for explicit transformer dependencies."""

from __future__ import annotations

from collections.abc import Collection
from typing import Protocol

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
from bioetl.domain.services import DataNormalizationService, IdentityService


class ContractPolicyLoader(Protocol):
    """Callable contract for loading pipeline contract policy."""

    def __call__(self, provider: str, entity: str) -> ContractPolicyProtocol:
        """Load contract policy for provider/entity."""
        ...


def build_transformer_dependencies(
    *,
    provider: str,
    entity_type: str | None,
    tracer: TracingPort | None = None,
    metrics: MetricsPort | None = None,
    identity_service: IdentityService | None = None,
    pii_hasher: PiiHasherPort | None = None,
    data_normalizer: DataNormalizationPort | None = None,
    contract_policy: ContractPolicyProtocol | None = None,
    content_hash_include_fields: Collection[str] | None = None,
    content_hash_exclude_fields: Collection[str] | None = None,
    contract_policy_loader: ContractPolicyLoader | None = None,
    structural_policy: StructuralPolicyProtocol | None = None,
) -> TransformerDependencyContext:
    """Build explicit collaborator bundle for transformer construction in composition."""

    resolved_contract_policy = contract_policy
    if resolved_contract_policy is None:
        resolved_contract_policy = _load_contract_policy(
            provider=provider,
            entity_type=entity_type,
            contract_policy_loader=contract_policy_loader,
        )

    resolved_identity_service = identity_service
    if resolved_identity_service is None:
        resolved_identity_service = IdentityService(
            content_hash_include_fields=(
                set(content_hash_include_fields)
                if content_hash_include_fields
                else None
            ),
            content_hash_exclude_fields=set(content_hash_exclude_fields or ()),
        )

    return TransformerDependencyContext(
        tracer=resolve_tracing_port(tracer=tracer),
        metrics=resolve_metrics_port(metrics=metrics),
        identity_service=resolved_identity_service,
        pii_hasher=pii_hasher if pii_hasher is not None else NoOpPiiHasher(),
        data_normalizer=(
            data_normalizer
            if data_normalizer is not None
            else DataNormalizationService()
        ),
        contract_policy=resolved_contract_policy,
        structural_policy=(
            structural_policy
            if structural_policy is not None
            else NoOpStructuralPolicy()
        ),
    )


def _load_contract_policy(
    *,
    provider: str,
    entity_type: str | None,
    contract_policy_loader: ContractPolicyLoader | None,
) -> ContractPolicyProtocol:
    """Load configured contract policy or degrade to the canonical fallback."""

    if entity_type is None or contract_policy_loader is None:
        return DefaultContractPolicy()
    try:
        return contract_policy_loader(provider, entity_type)
    except ValueError:
        return DefaultContractPolicy()
