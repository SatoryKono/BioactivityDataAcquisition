# pyright: reportConstantRedefinition=false
# basedpyright residual burn-down (shrink-only product surface).
"""Initialized publication controlled-vocabulary registry for application use."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "PublicationControlledVocabularyRegistry",
    "initialize_publication_controlled_vocabulary",
    "is_publication_controlled_vocabulary_initialized",
    "publication_controlled_vocabulary_values",
]


@dataclass(frozen=True, slots=True)
class PublicationControlledVocabularyRegistry:
    """Normalized provider/field → allowed token registry."""

    allowed_values_by_field: dict[tuple[str, str], frozenset[str]]

    def allowed_values(self, provider: str, field_name: str) -> frozenset[str]:
        """Return allowed normalized values for one provider field."""
        return self.allowed_values_by_field.get(
            (provider.lower(), field_name),
            frozenset(),
        )


_REGISTRY: PublicationControlledVocabularyRegistry | None = None


def initialize_publication_controlled_vocabulary(
    registry: PublicationControlledVocabularyRegistry,
) -> None:
    """Install the controlled-vocabulary registry for runtime consumers."""
    global _REGISTRY
    _REGISTRY = registry


def is_publication_controlled_vocabulary_initialized() -> bool:
    """Return whether the publication controlled-vocabulary registry is ready."""
    return _REGISTRY is not None


def publication_controlled_vocabulary_values(
    provider: str,
    field_name: str,
) -> frozenset[str]:
    """Return allowed values for one provider field, or empty when uninitialized."""
    if _REGISTRY is None:
        return frozenset()
    return _REGISTRY.allowed_values(provider, field_name)
