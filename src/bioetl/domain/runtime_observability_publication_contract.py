"""Explicit contract for runtime observability event publication architecture."""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = [
    "CANONICAL_DOMAIN_EVENT_EMITTER",
    "CANONICAL_LIFECYCLE_EMITTER",
    "CANONICAL_RUNTIME_OBSERVABILITY_EMITTERS",
    "RuntimeObservabilityPublicationContract",
    "RuntimeObservabilityPublicationRoute",
    "get_runtime_observability_publication_contract",
    "is_canonical_runtime_observability_emitter",
]

CANONICAL_LIFECYCLE_EMITTER = "PipelineObserver.emit_event"
CANONICAL_DOMAIN_EVENT_EMITTER = "PipelineObserver.emit_domain_event"
CANONICAL_RUNTIME_OBSERVABILITY_EMITTERS: tuple[str, ...] = (
    CANONICAL_LIFECYCLE_EMITTER,
    CANONICAL_DOMAIN_EVENT_EMITTER,
)


@dataclass(frozen=True, slots=True)
class RuntimeObservabilityPublicationRoute:
    """One canonical event-publication route."""

    emitter: str
    input_type: str
    event_vocabulary: str
    mapping_module: str | None = None
    layer_owner: str = "application"
    notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RuntimeObservabilityPublicationContract:
    """Immutable source of truth for runtime observability publication."""

    lifecycle_route: RuntimeObservabilityPublicationRoute
    domain_event_route: RuntimeObservabilityPublicationRoute
    forbidden_patterns: tuple[str, ...] = field(
        default_factory=lambda: (
            "no dedicated runtime event bus for observability emission",
            "no direct logger-only publication for lifecycle/domain events",
            "no ad-hoc event vocabulary outside PipelineEvent or explicit domain mapping",
        )
    )

    @property
    def canonical_emitters(self) -> tuple[str, ...]:
        """Return the canonical publication emitters."""
        return (
            self.lifecycle_route.emitter,
            self.domain_event_route.emitter,
        )


def get_runtime_observability_publication_contract() -> (
    RuntimeObservabilityPublicationContract
):
    """Return the explicit runtime observability publication contract."""
    return RuntimeObservabilityPublicationContract(
        lifecycle_route=RuntimeObservabilityPublicationRoute(
            emitter=CANONICAL_LIFECYCLE_EMITTER,
            input_type="PipelineEvent string vocabulary",
            event_vocabulary="bioetl.domain.events.PipelineEvent",
            layer_owner="application",
            notes=(
                "ordinary lifecycle and phase events must publish through PipelineObserver",
                "structured logs/metrics/spans are side effects of this canonical emitter",
            ),
        ),
        domain_event_route=RuntimeObservabilityPublicationRoute(
            emitter=CANONICAL_DOMAIN_EVENT_EMITTER,
            input_type="typed DomainEvent aggregate events",
            event_vocabulary="bioetl.domain.events.PipelineEvent + explicit custom names",
            mapping_module="bioetl.domain.observability_event_mapping",
            layer_owner="application+domain",
            notes=(
                "typed aggregate events must map through bioetl.domain.observability_event_mapping",
                "runtime emission reuses PipelineObserver instead of introducing a separate event bus",
            ),
        ),
    )


def is_canonical_runtime_observability_emitter(emitter: str) -> bool:
    """Return whether one emitter name is part of the frozen runtime contract."""
    return emitter in CANONICAL_RUNTIME_OBSERVABILITY_EMITTERS
