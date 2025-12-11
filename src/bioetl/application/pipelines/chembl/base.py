"""Base pipeline implementation for ChEMBL data extraction."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from bioetl.application.helpers import resolve_primary_key_with_filter
from bioetl.application.mappers.chembl import ChemblRecordMapper
from bioetl.application.pipelines.base import (
    PipelineBase,
    _create_default_metadata_builder,
)
from bioetl.application.pipelines.chembl.transformer import ChemblTransformerImpl
from bioetl.application.pipelines.stages.extract import ExtractStage
from bioetl.domain.clients.base.output.contracts import (
    RunMetadataBuilderProtocol,
    WriteResult,
)
from bioetl.domain.configs import PipelineConfig
from bioetl.domain.models import RunContext
from bioetl.domain.observability import LoggingPortABC
from bioetl.domain.pipelines.contracts import ErrorPolicyABC, LoaderABC, PipelineHookABC
from bioetl.domain.ports.extraction import (
    ExtractionServiceABC,
)
from bioetl.domain.schemas.pipeline_contracts import get_pipeline_contract
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
    """Базовый класс для ChEMBL-пайплайнов."""

    def __init__(
        self,
        config: PipelineConfig,
        logger: LoggingPortABC,
        validation_service: ValidationService,
        extraction_service: ExtractionServiceABC,
        hash_service: HashServiceABC,
        index_generator: IndexGeneratorABC,
        timestamp_provider: TimestampProviderABC,
        loader: LoaderABC | None = None,
        metadata_builder: RunMetadataBuilderProtocol | None = None,
        normalization_service: NormalizationServiceABC | None = None,
        hooks: list[PipelineHookABC] | None = None,
        error_policy: ErrorPolicyABC | None = None,
        post_transformer: TransformerABC | None = None,
    ) -> None:
        self._extraction_service: ExtractionServiceABC = extraction_service
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
            record_mapper=ChemblRecordMapper(),
            entity=config.entity_name,
        )

        # Create Transformer
        # Need schema contract
        contract = get_pipeline_contract(config.id, default_entity=config.entity_name)
        transformer = ChemblTransformerImpl(
            validation_service=validation_service,
            schema_contract=contract,
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
            metadata_builder=metadata_builder or _create_default_metadata_builder(),
            extractor=extractor,
            hooks=hooks,
            error_policy=error_policy,
            transformer=transformer,
            post_transformer=post_transformer,
        )

        self._loader = resolved_loader
        self._extractor = extractor
        self._transformer = transformer

    def get_version(self) -> str:
        """Возвращает версию релиза ChEMBL (например, 'chembl_34').

        Extraction service возвращает сырую версию (например, '34').
        Форматирование выполняется в application layer через domain service.
        """
        if self._chembl_release is not None:
            return self._chembl_release

        if self._should_skip_release_lookup():
            self._chembl_release = "unknown"
            return self._chembl_release

        try:
            raw_version = self._extraction_service.get_release_version()
            self._chembl_release = format_chembl_version(raw_version)
        except Exception as exc:  # pragma: no cover - защитный контур
            self._logger.warning(
                "Failed to fetch ChEMBL release; using 'unknown'",
                error=str(exc),
            )
            self._chembl_release = "unknown"

        return self._chembl_release

    def get_chembl_release(self) -> str:
        """Alias for get_version for backward compatibility."""
        return self.get_version()

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
        """True, если версию ChEMBL нужно пропустить (офлайн/CSV режим)."""
        input_mode = getattr(self._config, "input_mode", None)
        pipeline_cfg = getattr(self._config, "pipeline", {}) or {}
        if input_mode == "csv":
            return True
        return bool(pipeline_cfg.get("skip_release_lookup"))

    def extract(self, **kwargs: Any) -> pd.DataFrame:
        """
        Возвращает единый DataFrame для удобства unit-тестов и локальных проверок.

        Основной run-процесс использует self._extractor напрямую, поэтому
        материализация чанков в этой обёртке не влияет на боевой поток.
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
        except TypeError as exc:  # pragma: no cover - защитный контур
            raise TypeError(
                "ExtractStage.extract() должен возвращать DataFrame или Iterable."
            ) from exc

        chunks: list[pd.DataFrame] = []
        for chunk in iterator:
            if chunk is None:
                continue
            if not isinstance(chunk, pd.DataFrame):
                raise TypeError("Extractor chunks должны быть pandas.DataFrame.")
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
