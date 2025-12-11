"""Pipeline schema contracts and registry.

This module defines pipeline schema contracts that map pipeline identifiers
to their input/output schema names. The contracts can be loaded from:

1. External configuration (YAML) via injected loader - preferred
2. Hardcoded fallback dictionary - for backward compatibility

Architecture notes:
    The domain layer does not import infrastructure. External loaders are
    injected via the PipelineContractLoaderPortABC port. If no loader is
    configured, the module falls back to PIPELINE_CONTRACTS dictionary.

Example:
    >>> # Using default (hardcoded) contracts
    >>> contract = get_pipeline_contract("chembl.activity")
    >>> print(contract.schema_out)  # "activity"

    >>> # With injected loader (set up by application layer)
    >>> from bioetl.infrastructure.config import get_default_contract_loader
    >>> set_contract_loader(get_default_contract_loader())
    >>> contract = get_pipeline_contract("chembl.activity")
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.ports.pipeline_contract_loader import (
        PipelineContractLoaderPortABC,
    )


@dataclass(frozen=True)
class PipelineSchemaModel:
    """Schema description for pipeline.

    Attributes:
        pipeline_code: Unique pipeline identifier (e.g., "chembl.activity").
        schema_out: Primary output schema name.
        schema_in: Input schema name (optional, defaults to schema_out).
        output_schema: Final output schema name (optional, defaults to schema_out).
    """

    pipeline_code: str
    schema_out: str
    schema_in: str | None = None
    output_schema: str | None = None

    def get_output_schema(self) -> str:
        """Return schema for writing (fallback to schema_out)."""
        return self.output_schema or self.schema_out


def _default_contract(code: str, entity: str | None) -> PipelineSchemaModel:
    """Create default contract for unknown pipeline.

    Args:
        code: Pipeline code to use as base.
        entity: Optional entity name override.

    Returns:
        Default PipelineSchemaModel with entity-based schema names.
    """
    schema_name = entity or code
    return PipelineSchemaModel(
        pipeline_code=code,
        schema_out=schema_name,
        schema_in=schema_name,
        output_schema=schema_name,
    )


# =============================================================================
# Hardcoded fallback contracts (backward compatibility)
# =============================================================================
# NOTE: These contracts are maintained for backward compatibility.
# New pipelines should be added to configs/pipeline_contracts.yaml instead.
# This dictionary will be deprecated in a future version.

PIPELINE_CONTRACTS: dict[str, PipelineSchemaModel] = {
    "chembl.activity": PipelineSchemaModel(
        pipeline_code="chembl.activity",
        schema_out="activity",
        schema_in="activity_input",
        output_schema="activity_output",
    ),
    "chembl.assay": PipelineSchemaModel(
        pipeline_code="chembl.assay",
        schema_out="assay",
        schema_in="assay_input",
        output_schema="assay_output",
    ),
    "chembl.document": PipelineSchemaModel(
        pipeline_code="chembl.document",
        schema_out="document",
        schema_in="document_input",
        output_schema="document_output",
    ),
    "chembl.target": PipelineSchemaModel(
        pipeline_code="chembl.target",
        schema_out="target",
        schema_in="target_input",
        output_schema="target_output",
    ),
    "chembl.molecule": PipelineSchemaModel(
        pipeline_code="chembl.molecule",
        schema_out="molecule",
        schema_in="molecule_input",
        output_schema="molecule_output",
    ),
}


# =============================================================================
# Contract loader injection (dependency inversion)
# =============================================================================

_CONTRACT_LOADER_CTX: ContextVar[PipelineContractLoaderPortABC | None] = ContextVar(
    "_contract_loader_ctx", default=None
)


def set_contract_loader(loader: PipelineContractLoaderPortABC | None) -> None:
    """Inject contract loader for external configuration support.

    This function allows the application layer to inject a loader that
    reads contracts from external sources (YAML, database, etc.).

    Args:
        loader: Contract loader implementation, or None to clear.

    Example:
        >>> from bioetl.infrastructure.config import get_default_contract_loader
        >>> set_contract_loader(get_default_contract_loader())
    """
    _CONTRACT_LOADER_CTX.set(loader)


def get_contract_loader() -> PipelineContractLoaderPortABC | None:
    """Get currently configured contract loader.

    Returns:
        Current loader or None if not configured.
    """
    return _CONTRACT_LOADER_CTX.get()


def clear_contract_loader() -> None:
    """Clear contract loader, reverting to hardcoded fallback."""
    _CONTRACT_LOADER_CTX.set(None)


# =============================================================================
# Public API
# =============================================================================


def get_pipeline_contract(
    pipeline_code: str, *, default_entity: str | None = None
) -> PipelineSchemaModel:
    """Return schema contract for pipeline.

    This function first tries to load the contract from an injected loader
    (if configured), then falls back to the hardcoded PIPELINE_CONTRACTS
    dictionary.

    Args:
        pipeline_code: Pipeline identifier (e.g., "chembl.activity").
        default_entity: Fallback entity name if contract not found.

    Returns:
        PipelineSchemaModel with schema names for the pipeline.

    Example:
        >>> contract = get_pipeline_contract("chembl.activity")
        >>> print(contract.schema_out)  # "activity"
        >>> print(contract.schema_in)   # "activity_input"
    """
    # Try injected loader first
    loader = get_contract_loader()
    if loader is not None:
        return loader.get_contract(pipeline_code, default_entity=default_entity)

    # Fallback to hardcoded contracts
    if pipeline_code in PIPELINE_CONTRACTS:
        return PIPELINE_CONTRACTS[pipeline_code]

    return _default_contract(pipeline_code, default_entity)


def list_pipeline_codes() -> list[str]:
    """List all available pipeline codes.

    Returns contracts from injected loader if configured, otherwise
    from hardcoded dictionary.

    Returns:
        List of pipeline code strings.
    """
    loader = get_contract_loader()
    if loader is not None:
        return loader.list_pipeline_codes()

    return list(PIPELINE_CONTRACTS.keys())


def has_pipeline_contract(pipeline_code: str) -> bool:
    """Check if a contract exists for the given pipeline.

    Args:
        pipeline_code: Pipeline identifier to check.

    Returns:
        True if contract is explicitly defined.
    """
    loader = get_contract_loader()
    if loader is not None:
        return loader.has_contract(pipeline_code)

    return pipeline_code in PIPELINE_CONTRACTS


__all__ = [
    "PipelineSchemaModel",
    "PIPELINE_CONTRACTS",
    "get_pipeline_contract",
    "list_pipeline_codes",
    "has_pipeline_contract",
    "set_contract_loader",
    "get_contract_loader",
    "clear_contract_loader",
]
