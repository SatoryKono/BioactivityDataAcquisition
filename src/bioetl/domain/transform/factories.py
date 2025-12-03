"""
Factories for normalization components.
"""
from bioetl.domain.transform.normalizers import CUSTOM_FIELD_NORMALIZERS
from bioetl.domain.transform.impl.registry import NormalizerRegistry
from bioetl.infrastructure.config.models import NormalizationConfig


def create_normalizer_registry(
    config: NormalizationConfig,
) -> NormalizerRegistry:
    """
    Creates and configures a NormalizerRegistry based on configuration.
    """
    registry = NormalizerRegistry()

    # Register built-in custom normalizers
    for name, func in CUSTOM_FIELD_NORMALIZERS.items():
        registry.register(name, func)

    # Configure lists
    registry.set_case_sensitive_fields(config.case_sensitive_fields)
    registry.set_id_fields(config.id_fields)

    return registry


def default_normalizer_registry() -> NormalizerRegistry:
    """
    Creates a default registry with minimal configuration.
    """
    return create_normalizer_registry(NormalizationConfig())
