"""Pipeline schema contracts and registry.

This module defines pipeline schema contracts that map pipeline identifiers
to their input/output schema names. Contracts are loaded from external
configuration (YAML) via an injected loader.

Architecture notes:
    The domain layer does not import infrastructure. External loaders are
    injected via the PipelineContractLoaderPortABC port. A loader MUST be
    configured before using contract functions.

Example:
    >>> # Set up loader (typically done in application bootstrap)
    >>> from bioetl.infrastructure.config import get_default_contract_loader
    >>> set_contract_loader(get_default_contract_loader())
    >>> contract = get_pipeline_contract("chembl.activity")
    >>> print(contract.schema_out)  # "activity"
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.ports.pipeline_contract_loader import (
        PipelineContractLoaderPortABC,
    )


class ContractLoaderNotConfiguredError(RuntimeError):
    """Raised when contract loader is not configured."""

    def __init__(self) -> None:
        super().__init__(
            "Pipeline contract loader is not configured. "
            "Call set_contract_loader() during application bootstrap."
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
    """Clear contract loader."""
    _CONTRACT_LOADER_CTX.set(None)


def _require_loader() -> "PipelineContractLoaderPortABC":
    """Get loader or raise if not configured."""
    loader = get_contract_loader()
    if loader is None:
        raise ContractLoaderNotConfiguredError()
    return loader


# =============================================================================
# Public API
# =============================================================================


def get_pipeline_contract(
    pipeline_code: str, *, default_entity: str | None = None
) -> PipelineSchemaModel:
    """Return schema contract for pipeline.

    Loads contract from the configured external loader. If the contract
    is not found, returns a default contract based on the pipeline code.

    Args:
        pipeline_code: Pipeline identifier (e.g., "chembl.activity").
        default_entity: Fallback entity name if contract not found.

    Returns:
        PipelineSchemaModel with schema names for the pipeline.

    Raises:
        ContractLoaderNotConfiguredError: If no loader is configured.

    Example:
        >>> contract = get_pipeline_contract("chembl.activity")
        >>> print(contract.schema_out)  # "activity"
        >>> print(contract.schema_in)   # "activity_input"
    """
    loader = _require_loader()
    return loader.get_contract(pipeline_code, default_entity=default_entity)


def list_pipeline_codes() -> list[str]:
    """List all available pipeline codes from the configured loader.

    Returns:
        List of pipeline code strings.

    Raises:
        ContractLoaderNotConfiguredError: If no loader is configured.
    """
    loader = _require_loader()
    return loader.list_pipeline_codes()


def has_pipeline_contract(pipeline_code: str) -> bool:
    """Check if a contract exists for the given pipeline.

    Args:
        pipeline_code: Pipeline identifier to check.

    Returns:
        True if contract is explicitly defined.

    Raises:
        ContractLoaderNotConfiguredError: If no loader is configured.
    """
    loader = _require_loader()
    return loader.has_contract(pipeline_code)


__all__ = [
    "ContractLoaderNotConfiguredError",
    "PipelineSchemaModel",
    "get_pipeline_contract",
    "list_pipeline_codes",
    "has_pipeline_contract",
    "set_contract_loader",
    "get_contract_loader",
    "clear_contract_loader",
]
