"""Infrastructure validation components (Pandera-based).

This module provides:
- Pandera-based validator implementations
- Schema factories for dependency injection
- ChEMBL Pandera schemas (in submodule `schemas.chembl`)

Usage:
    # For validators and factories
    from bioetl.infrastructure.validation import (
        PanderaValidatorFactory,
        PanderaSchemaProviderFactory,
    )

    # For ChEMBL schemas
    from bioetl.infrastructure.validation.schemas.chembl import (
        ActivityTableSchema,
        AssayTableSchema,
    )

    # For base schema classes
    from bioetl.infrastructure.validation.schemas import (
        BaseGeneratedColumnsModel,
        build_output_column_order,
    )
"""

# New naming convention; Deprecated aliases for backward compatibility
from bioetl.infrastructure.validation.factories import (
    PanderaSchemaProviderFactory,
    PanderaValidatorFactory,
    create_schema_provider_factory,
    create_validator_factory,
    default_schema_provider_factory,
    default_validator_factory,
)
from bioetl.infrastructure.validation.impl.pandera_validator import PanderaValidatorImpl

__all__ = [
    "PanderaSchemaProviderFactory",
    "PanderaValidatorFactory",
    "PanderaValidatorImpl",
    # New naming convention
    "create_schema_provider_factory",
    "create_validator_factory",
    # Deprecated aliases
    "default_schema_provider_factory",
    "default_validator_factory",
]
