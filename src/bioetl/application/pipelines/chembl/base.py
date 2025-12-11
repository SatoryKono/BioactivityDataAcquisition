"""Base pipeline implementation for ChEMBL data extraction."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from bioetl.application.files.csv_record_source import (
    CsvRecordSourceImpl,
    IdListRecordSourceImpl,
)
from bioetl.application.helpers import resolve_primary_key_with_filter
from bioetl.application.mappers.chembl import ChemblRecordMapper
from bioetl.application.pipelines.base import PipelineBase
from bioetl.application.pipelines.chembl.transformer import ChemblTransformerImpl
from bioetl.application.pipelines.stages.extract import ExtractStage
from bioetl.domain.clients.base.output.contracts import (
    RunMetadataBuilderProtocol,
    WriteResult,
)
from bioetl.domain.configs import ChemblSourceConfig, PipelineConfig
from bioetl.domain.models import RunContext
from bioetl.domain.observability import LoggingPortABC
from bioetl.domain.pipelines.contracts import ErrorPolicyABC, LoaderABC, PipelineHookABC
from bioetl.domain.ports.entity_models import EntityModelRegistryABC
from bioetl.domain.ports.extraction import (
    ExtractionServiceABC,
)
from bioetl.domain.record_source import RecordSourceABC
from bioetl.domain.schemas.pipeline_contracts import (
    PipelineSchemaModel,
    get_pipeline_contract,
)
from bioetl.domain.services.version_formatter import format_chembl_version
from bioetl.domain.transform.contracts import (
    HashServiceABC,
    IndexGeneratorABC,
    NormalizationServiceABC,
    TimestampProviderABC,
)
from bioetl.domain.transform.transformers import TransformerABC
from bioetl.domain.validation.service import ValidationService


class ChemblPipelineBase(PipelineBase):
    """Base class for ChEMBL pipelines."""

    def __init__(
        self,
        config: PipelineConfig,
        logger: LoggingPortABC,
        validation_service: ValidationService,
        extraction_service: ExtractionServiceABC,
        hash_service: HashServiceABC,
        index_generator: IndexGeneratorABC,
        timestamp_provider: TimestampProviderABC,
        entity_model_registry: EntityModelRegistryABC,
        schema_contract: PipelineSchemaModel | None = None,
        loader: LoaderABC | None = None,
        metadata_builder: RunMetadataBuilderProtocol | None = None,
        normalization_service: NormalizationServiceABC | None = None,
        hooks: list[PipelineHookABC] | None = None,
        error_policy: ErrorPolicyABC | None = None,
        post_transformer: TransformerABC | None = None,
        record_source: RecordSourceABC | None = None,
    ) -> None:
        self._extraction_service: ExtractionServiceABC = extraction_service
        self._entity_model_registry: EntityModelRegistryABC = entity_model_registry
        self._chembl_release: str | None = None

        self.ID_COLUMN, self.API_FILTER_KEY = resolve_primary_key_with_filter(config)

        if normalization_service is None:
            raise ValueError(
                "Normalization service is required. "
                "Inject NormalizationServiceABC from container."
            )
        norm_service = normalization_service

        extractor = ExtractStage(
            extraction_service=extraction_service,
            record_mapper=ChemblRecordMapper(registry=entity_model_registry),
            entity=config.entity_name,
            record_source=record_source,
        )

        # Create Transformer with injected schema contract
        resolved_contract = schema_contract or get_pipeline_contract(
            config.id, default_entity=config.entity_name
        )

        transformer = ChemblTransformerImpl(
            validation_service=validation_service,
            schema_contract=resolved_contract,
            normalization_service=norm_service,
            logger=logger,
            serialization_mode=config.serialization_mode,
        )

        resolved_loader = loader
        if resolved_loader is None:
            raise ValueError("Loader must be provided.")

        super().__init__(
            config=config,
            logger=logger,
            validation_service=validation_service,
            loader=resolved_loader,
            hash_service=hash_service,
            index_generator=index_generator,
            timestamp_provider=timestamp_provider,
            schema_contract=resolved_contract,
            metadata_builder=metadata_builder,
            extractor=extractor,
            hooks=hooks,
            error_policy=error_policy,
            transformer=transformer,
            post_transformer=post_transformer,
        )

        self._loader = resolved_loader
        self._extractor = extractor
        self._transformer = transformer
        self._attach_record_source(extractor)

    def get_version(self) -> str:
        """Return ChEMBL release version (e.g., 'chembl_34').

        Extraction service returns raw version (e.g., '34').
        Formatting is done in application layer via domain service.
        """
        if self._chembl_release is not None:
            return self._chembl_release

        if self._should_skip_release_lookup():
            self._chembl_release = "unknown"
            return self._chembl_release

        try:
            raw_version = self._extraction_service.get_release_version()
            self._chembl_release = format_chembl_version(raw_version)
        except Exception as exc:  # pragma: no cover - defensive guard
            self._logger.warning(
                "Failed to fetch ChEMBL release; using 'unknown'",
                error=str(exc),
            )
            self._chembl_release = "unknown"

        return self._chembl_release

    def _enrich_context(self, context: RunContext) -> None:
        """Adds ChEMBL release version to metadata."""
        context.metadata["chembl_release"] = self.get_version()
        # Enrich with actual endpoint used if provided by extraction service
        try:
            getter = getattr(self._extraction_service, "get_last_endpoint_used", None)
            if callable(getter):
                endpoint_used = getter()
                if endpoint_used:
                    context.metadata["endpoint_used"] = endpoint_used
        except Exception:
            pass

    def _should_skip_release_lookup(self) -> bool:
        """True if ChEMBL version lookup should be skipped (offline/CSV mode)."""
        # Try new config structure first
        input_mode: str | None
        try:
            input_mode = self._config.source.input_mode
        except AttributeError:
            # Fallback for compatibility or mocks
            input_mode = getattr(self._config, "input_mode", None)

        pipeline_cfg = getattr(self._config, "pipeline", {}) or {}
        if input_mode == "csv":
            return True
        return bool(pipeline_cfg.get("skip_release_lookup"))

    def extract(self, **kwargs: Any) -> pd.DataFrame:
        """Return single DataFrame for unit tests and local checks.

        Main run process uses self._extractor directly, so
        chunk materialization in this wrapper doesn't affect production flow.
        """
        extractor = self._extractor
        if extractor is None:
            raise RuntimeError("Chembl extractor is not initialized.")

        extract_result = extractor.extract(**kwargs)
        if extract_result is None:
            return pd.DataFrame()

        if isinstance(extract_result, pd.DataFrame):
            return extract_result

        try:
            iterator = iter(extract_result)
        except TypeError as exc:  # pragma: no cover - defensive guard
            raise TypeError(
                "ExtractStage.extract() must return DataFrame or Iterable."
            ) from exc

        chunks: list[pd.DataFrame] = []
        for chunk in iterator:
            if chunk is None:
                continue
            if not isinstance(chunk, pd.DataFrame):
                raise TypeError("Extractor chunks must be pandas.DataFrame.")
            if chunk.empty:
                continue
            chunks.append(chunk)

        if not chunks:
            return pd.DataFrame()

        return pd.concat(chunks, ignore_index=True, copy=False)

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Runs Chembl-specific transformer pipeline on dataframe."""
        transformer = self._transformer
        if transformer is None:
            raise RuntimeError("Chembl transformer is not initialized.")
        return transformer.apply(df)

    def write(
        self,
        df: pd.DataFrame,
        output_path: Path,
        context: RunContext,
    ) -> WriteResult:
        """Persists transformed dataframe using the resolved loader."""
        return self._write_with_loader(df, output_path, context)

    # === Internal helpers ===

    def _attach_record_source(self, extractor: ExtractStage) -> None:
        """Attach file-based record source when configured to avoid network calls."""

        source_cfg = self._config.source
        mode = source_cfg.input_mode
        if mode == "auto_detect" and source_cfg.input_path:
            mode = "csv"

        record_source: RecordSourceABC | None = None
        if mode == "csv":
            input_path = source_cfg.input_path
            if input_path is None:
                raise ValueError("input_path is required when input_mode is 'csv'.")
            record_source = CsvRecordSourceImpl(
                input_path=Path(input_path),
                csv_options=source_cfg.csv,
                limit=None,
                logger=self._logger,
                chunk_size=source_cfg.batch_size,
            )
        elif mode == "id_only":
            input_path = source_cfg.input_path
            if input_path is None:
                raise ValueError("input_path is required when input_mode is 'id_only'.")
            provider_cfg = self._config.get_source_config(self._config.provider)

            if not isinstance(provider_cfg, ChemblSourceConfig):
                raise TypeError(
                    "ChemblSourceConfig is required for id_only input_mode."
                )
            record_source = IdListRecordSourceImpl(
                input_path=Path(input_path),
                id_column=self.ID_COLUMN,
                csv_options=source_cfg.csv,
                limit=None,
                extraction_service=self._extraction_service,
                source_config=provider_cfg,
                entity=self._config.entity_name,
                filter_key=self.API_FILTER_KEY,
                logger=self._logger,
                chunk_size=source_cfg.batch_size,
            )

        if record_source is not None:
            extractor.record_source = record_source
