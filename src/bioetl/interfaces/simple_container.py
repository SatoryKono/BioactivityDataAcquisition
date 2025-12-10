"""Simplified container for pipeline dependencies.

This container provides a streamlined approach to dependency injection
for the new architecture. It focuses on:
- SchemaBootstrapService for schema initialization
- SchemaContractProvider for schema metadata access
- RecordMapper for record transformation
- ResponseParser for API response parsing
"""

from __future__ import annotations

from typing import Callable

from bioetl.application.mappers.chembl.record_mapper import ChemblRecordMapper
from bioetl.application.mappers.contracts import RecordMapperABC
from bioetl.application.services.schema_bootstrap import (
    SchemaBootstrapService,
    create_schema_bootstrap_service,
)
from bioetl.application.services.schema_contract_provider import (
    SchemaContractProviderImpl,
)
from bioetl.domain.ports.parsing import ResponseParserPortABC
from bioetl.domain.ports.schema import SchemaContractProviderABC
from bioetl.infrastructure.clients.chembl.response_parser import (
    ChemblGenericResponseParser,
)


class SimplePipelineContainer:
    """Simplified container for pipeline dependencies.

    This container provides a streamlined approach to dependency injection
    for the new architecture. It focuses on:
    - SchemaBootstrapService for schema initialization
    - SchemaContractProvider for schema metadata access
    - RecordMapper for record transformation
    - ResponseParser for API response parsing

    Example:
        >>> container = SimplePipelineContainer()
        >>> container.bootstrap()
        >>> mapper = container.record_mapper
        >>> parser = container.response_parser
    """

    def __init__(self) -> None:
        """Initialize the container with lazy-initialized components."""
        self._schema_bootstrap: SchemaBootstrapService | None = None
        self._schema_contract_provider: SchemaContractProviderABC | None = None
        self._record_mapper: RecordMapperABC | None = None
        self._response_parser: ResponseParserPortABC | None = None
        self._bootstrapped: bool = False

    def bootstrap(self) -> None:
        """Initialize all application services.

        This method must be called before accessing container properties.
        It initializes the schema bootstrap service, registers schemas,
        and sets up the schema contract provider.

        Raises:
            RuntimeError: If bootstrap fails during initialization.
        """
        if self._bootstrapped:
            return

        # 1. Schema bootstrap
        self._schema_bootstrap = create_schema_bootstrap_service()
        schema_provider = self._schema_bootstrap.ensure_registered()

        # 2. Schema contract provider
        self._schema_contract_provider = SchemaContractProviderImpl(schema_provider)

        # 3. Inject into infrastructure (using internal function to avoid deprecation warning)
        # This maintains backward compatibility while we transition to explicit injection
        from bioetl.infrastructure.config.loader import _set_provider_internal

        _set_provider_internal(self._schema_contract_provider)

        self._bootstrapped = True

    @property
    def is_bootstrapped(self) -> bool:
        """Check if the container has been bootstrapped."""
        return self._bootstrapped

    @property
    def record_mapper(self) -> RecordMapperABC:
        """Get record mapper (lazy init).

        Returns:
            ChemblRecordMapper instance for mapping raw records to domain models.

        Note:
            This property uses lazy initialization and does not require
            bootstrap() to be called first.
        """
        if self._record_mapper is None:
            self._record_mapper = ChemblRecordMapper()
        return self._record_mapper

    @property
    def response_parser(self) -> ResponseParserPortABC:
        """Get generic response parser.

        Returns:
            ChemblGenericResponseParser instance for parsing API responses.

        Note:
            This property uses lazy initialization and does not require
            bootstrap() to be called first.
        """
        if self._response_parser is None:
            self._response_parser = ChemblGenericResponseParser()
        return self._response_parser

    @property
    def schema_contract_provider(self) -> SchemaContractProviderABC:
        """Get schema contract provider.

        Returns:
            Configured SchemaContractProviderImpl instance.

        Raises:
            RuntimeError: If container has not been bootstrapped.
        """
        if self._schema_contract_provider is None:
            raise RuntimeError("Container not bootstrapped")
        return self._schema_contract_provider

    @property
    def schema_bootstrap(self) -> SchemaBootstrapService:
        """Get schema bootstrap service.

        Returns:
            Configured SchemaBootstrapService instance.

        Raises:
            RuntimeError: If container has not been bootstrapped.
        """
        if self._schema_bootstrap is None:
            raise RuntimeError("Container not bootstrapped")
        return self._schema_bootstrap

    def reset(self) -> None:
        """Reset the container state (primarily for testing).

        Clears all cached instances and resets bootstrap state.
        """
        from bioetl.infrastructure.config.loader import _clear_provider_internal

        _clear_provider_internal()

        self._schema_bootstrap = None
        self._schema_contract_provider = None
        self._record_mapper = None
        self._response_parser = None
        self._bootstrapped = False


__all__ = ["SimplePipelineContainer"]
