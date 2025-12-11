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

from bioetl.infrastructure.validation.factories import (
    PanderaSchemaProviderFactory,
    PanderaValidatorFactory,
    create_schema_provider_factory,
    create_validator_factory,
)
from bioetl.infrastructure.validation.impl.pandera_validator import PanderaValidatorImpl
from bioetl.infrastructure.validation.schema_generator import (
    PanderaSchemaGenerator,
    YamlColumnOrderLoader,
    generate_schema_from_column_order,
    load_column_order_from_yaml,
)

__all__ = [
    "PanderaSchemaProviderFactory",
    "PanderaValidatorFactory",
    "PanderaValidatorImpl",
    "create_schema_provider_factory",
    "create_validator_factory",
    # Schema generation
    "PanderaSchemaGenerator",
    "YamlColumnOrderLoader",
    "generate_schema_from_column_order",
    "load_column_order_from_yaml",
]
