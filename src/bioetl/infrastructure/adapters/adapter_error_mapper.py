"""Unified adapter error -> domain error mapping (facade)."""

from __future__ import annotations

from bioetl.domain.exceptions import ExternalServiceError
from bioetl.domain.ports import LoggerPort
from bioetl.infrastructure.errors import (
    DomainErrorMappingInput,
    DomainInfraExceptionMapper,
)

__all__ = ["AdapterErrorMapper", "DomainErrorMappingInput"]


class AdapterErrorMapper:
    """Backward-compatible facade over the unified domain/infra exception mapper."""

    def __init__(self, *, logger: LoggerPort) -> None:
        self._mapper = DomainInfraExceptionMapper(logger=logger)

    def map_to_domain_error(
        self,
        payload: DomainErrorMappingInput,
    ) -> ExternalServiceError:
        """Map adapter error context to a domain external-service exception."""
        return self._mapper.map_to_domain_error(payload)
