"""Unified adapter error -> domain error mapping (facade)."""

from __future__ import annotations

from bioetl.domain.exceptions import ExternalServiceError
from bioetl.domain.ports import LoggerPort
from bioetl.infrastructure.errors import (
    DomainErrorMappingInput,
    DomainInfraExceptionMapper,
)

__all__ = ["AdapterErrorMapper", "DomainErrorMappingInput"]


def _create_default_domain_infra_exception_mapper(
    *,
    logger: LoggerPort,
) -> DomainInfraExceptionMapper:
    """Create default exception mapper for non-DI call sites.

    Args:
        logger: Structured logger injected into the mapper for error logging.

    Returns:
        Default DomainInfraExceptionMapper instance.
    """
    return DomainInfraExceptionMapper(logger=logger)


class AdapterErrorMapper:
    """Backward-compatible facade over the unified domain/infra exception mapper."""

    def __init__(
        self,
        *,
        logger: LoggerPort,
        mapper: DomainInfraExceptionMapper | None = None,
    ) -> None:
        """Initialize AdapterErrorMapper.

        Args:
            logger: Structured logger used by the default mapper when none is provided.
            mapper: Optional pre-built DomainInfraExceptionMapper; creates a default one if None.
        """
        self._mapper = (
            mapper
            if mapper is not None
            else _create_default_domain_infra_exception_mapper(logger=logger)
        )

    def map_to_domain_error(
        self,
        payload: DomainErrorMappingInput,
    ) -> ExternalServiceError:
        """Map adapter error context to a domain external-service exception.

        Args:
            payload: DomainErrorMappingInput with error context (provider, status code, message, etc.).

        Returns:
            ExternalServiceError wrapping the original exception with domain context.
        """
        return self._mapper.map_to_domain_error(payload)
