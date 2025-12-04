"""Dependency Injection Container for the application."""
from pathlib import Path
from typing import Any

import bioetl.infrastructure.clients.chembl.provider  # noqa: F401 - ensure registration
from bioetl.application.pipelines.hooks import ErrorPolicyABC, PipelineHookABC
from bioetl.application.pipelines.hooks_impl import (
    LoggingPipelineHook,
    StopOnErrorPolicyImpl,
)
from bioetl.clients.csv_record_source import CsvRecordSource, IdListRecordSource
from bioetl.application.pipelines.hooks import ErrorPolicyABC, PipelineHookABC
from bioetl.application.pipelines.hooks_impl import (
    FailFastErrorPolicyImpl,
    LoggingPipelineHookImpl,
)
from bioetl.core.provider_registry import get_provider
from bioetl.core.providers import ProviderDefinition, ProviderId
from bioetl.domain.normalization_service import ChemblNormalizationService, NormalizationService
from bioetl.domain.record_source import ApiRecordSource, RecordSource
from bioetl.domain.schemas import register_schemas
from bioetl.domain.schemas.registry import SchemaRegistry
from bioetl.domain.transform.hash_service import HashService
from bioetl.domain.validation.service import ValidationService
from bioetl.infrastructure.clients.chembl.provider import register_chembl_provider
from bioetl.infrastructure.config.models import PipelineConfig
from bioetl.infrastructure.logging.contracts import LoggerAdapterABC
from bioetl.infrastructure.logging.factories import default_logger
from bioetl.infrastructure.output.factories import (
    default_metadata_writer,
    default_writer,
)
from bioetl.infrastructure.output.unified_writer import UnifiedOutputWriter


class PipelineContainer:
    """
    DI Container for pipeline dependencies.
    """

    def __init__(self, config: PipelineConfig) -> None:
        self.config = config
        self._provider_id = ProviderId(self.config.provider)
        self._schema_registry = SchemaRegistry()
        register_schemas(self._schema_registry)
        self._register_providers()
        self._logger: LoggerAdapterABC | None = None
        self._hooks: list[PipelineHookABC] | None = None
        self._error_policy: ErrorPolicyABC | None = None

    def get_logger(self) -> LoggerAdapterABC:
        """Get the configured logger."""
        if self._logger is None:
            self._logger = default_logger()
        return self._logger

    def get_hooks(self) -> list[PipelineHookABC]:
        """Возвращает список хуков пайплайна."""
        return [LoggingPipelineHookImpl(self.get_logger())]

    def get_error_policy(self) -> ErrorPolicyABC:
        """Возвращает политику обработки ошибок пайплайна."""
        return FailFastErrorPolicyImpl()

    def get_validation_service(self) -> ValidationService:
        """Get the validation service with registered schemas."""
        return ValidationService(schema_provider=self._schema_registry)

    def get_output_writer(self) -> UnifiedOutputWriter:
        """Get the unified output writer."""
        return UnifiedOutputWriter(
            writer=default_writer(),
            metadata_writer=default_metadata_writer(),
            config=self.config.determinism,
        )

    def get_normalization_service(self) -> NormalizationService:
        """Create normalization service for the configured provider."""
        if self._provider_id == ProviderId.CHEMBL:
            return ChemblNormalizationService(self.config)
        raise ValueError(
            f"Unsupported provider for normalization: {self._provider_id.value}"
        )

    def get_record_source(
        self,
        extraction_service: Any,
        *,
        limit: int | None = None,
        logger: LoggerAdapterABC | None = None,
    ) -> RecordSource:
        """Create record source based on pipeline input configuration."""
        mode = self.config.input_mode
        path = self.config.input_path

        if mode == "auto_detect" and path:
            mode = "csv"

        effective_logger = logger or self.get_logger()

        if mode == "csv":
            if path is None:
                raise ValueError("input_path is required for CSV mode")
            return CsvRecordSource(
                input_path=Path(path),
                csv_options=self.config.csv_options,
                limit=limit,
                logger=effective_logger,
            )

        if mode == "id_only":
            if path is None:
                raise ValueError("input_path is required for ID-only mode")
            definition = self._get_provider_definition()
            source_config = self._resolve_provider_config(definition)
            id_column = self._resolve_primary_key()
            filter_key = f"{id_column}__in"
            return IdListRecordSource(
                input_path=Path(path),
                id_column=id_column,
                csv_options=self.config.csv_options,
                limit=limit,
                extraction_service=extraction_service,
                source_config=source_config,
                entity=self.config.entity_name,
                filter_key=filter_key,
                logger=effective_logger,
            )

        filters = self.config.pipeline.copy()
        if limit is not None:
            filters["limit"] = limit

        return ApiRecordSource(
            extraction_service=extraction_service,
            entity=self.config.entity_name,
            filters=filters,
        )

    def get_extraction_service(self) -> Any:
        """Get the extraction service based on provider configuration."""
        definition = self._get_provider_definition()
        source_config = self._resolve_provider_config(definition)

        client = definition.components.create_client(source_config)
        return definition.components.create_extraction_service(client, source_config)

    def get_hash_service(self) -> HashService:
        """Get the hash service."""
        return HashService()

    def get_hooks(self) -> list[PipelineHookABC]:
        """Возвращает список хуков выполнения пайплайна."""
        if self._hooks is None:
            self._hooks = [LoggingPipelineHook(self.get_logger())]
        return list(self._hooks)

    def get_error_policy(self) -> ErrorPolicyABC:
        """Возвращает политику обработки ошибок пайплайна."""
        if self._error_policy is None:
            self._error_policy = StopOnErrorPolicyImpl()
        return self._error_policy

    def _resolve_primary_key(self) -> str:
        pk = self.config.primary_key
        if not pk and self.config.pipeline and "primary_key" in self.config.pipeline:
            pk = self.config.pipeline["primary_key"]
        if not pk:
            pk = f"{self.config.entity_name}_id"
        if not pk:
            raise ValueError(
                f"Could not resolve primary key for entity '{self.config.entity_name}'"
            )
        return pk

    def _register_providers(self) -> None:
        register_chembl_provider()

    def _get_provider_definition(self) -> ProviderDefinition:
        return get_provider(self._provider_id)

    def _resolve_provider_config(self, definition: ProviderDefinition) -> Any:
        source_config = self.config.get_source_config(self._provider_id.value)
        if not isinstance(source_config, definition.config_type):
            raise TypeError(
                f"Expected config type {definition.config_type.__name__} for "
                f"provider '{self._provider_id.value}'"
            )
        return source_config


def build_pipeline_dependencies(config: PipelineConfig) -> PipelineContainer:
    """Factory for the container."""
    return PipelineContainer(config)
