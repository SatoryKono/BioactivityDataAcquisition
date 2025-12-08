"""Base pipeline implementation for ChEMBL data extraction."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from bioetl.application.pipelines.base import (
    PipelineBase,
    _create_default_metadata_builder,
)
from bioetl.application.pipelines.chembl.extractor import ChemblExtractorImpl
from bioetl.application.pipelines.chembl.transformer import ChemblTransformerImpl
from bioetl.application.transform.pandas_batch_adapter import PandasBatchAdapter
from bioetl.domain.clients.base.output.contracts import (
    OutputWriterABC,
    WriteResult,
    RunMetadataBuilderProtocol,
)
from bioetl.domain.configs import PipelineConfig
from bioetl.domain.models import RunContext
from bioetl.domain.observability import LoggingPortABC
from bioetl.domain.pipelines.contracts import ErrorPolicyABC, PipelineHookABC
from bioetl.domain.ports.extraction import ExtractionServiceABC
from bioetl.domain.record_source import RecordSource
from bioetl.domain.schemas.pipeline_contracts import get_pipeline_contract
from bioetl.domain.transform.contracts import HashServiceABC, NormalizationServiceABC
from bioetl.domain.transform.transformers import TransformerABC
from bioetl.domain.validation.service import ValidationService


class ChemblPipelineBase(PipelineBase):
    """Базовый класс для ChEMBL-пайплайнов."""

    def __init__(
        self,
        config: PipelineConfig,
        logger: LoggingPortABC,
        validation_service: ValidationService,
        output_writer: OutputWriterABC,
        extraction_service: ExtractionServiceABC,
        hash_service: HashServiceABC,
        metadata_builder: RunMetadataBuilderProtocol | None = None,
        record_source: RecordSource | None = None,
        normalization_service: NormalizationServiceABC | None = None,
        hooks: list[PipelineHookABC] | None = None,
        error_policy: ErrorPolicyABC | None = None,
        post_transformer: TransformerABC | None = None,
    ) -> None:
        self._extraction_service = extraction_service
        self._chembl_release: str | None = None

        self.ID_COLUMN, self.API_FILTER_KEY = self._resolve_primary_key(config)

        if normalization_service is None:
            raise ValueError(
                "Normalization service is required. "
                "Inject NormalizationServiceABC from container."
            )
        norm_service = normalization_service

        extractor = ChemblExtractorImpl(
            config=config,
            extraction_service=extraction_service,
            normalization_service=norm_service,
            logger=logger,
            batch_adapter=PandasBatchAdapter(),
            record_source=record_source,
        )

        # Create Transformer
        # Need schema contract
        contract = get_pipeline_contract(config.id, default_entity=config.entity_name)
        transformer = ChemblTransformerImpl(
            validation_service=validation_service,
            schema_contract=contract,
            normalization_service=norm_service,
            logger=logger,
        )

        super().__init__(
            config=config,
            logger=logger,
            validation_service=validation_service,
            output_writer=output_writer,
            hash_service=hash_service,
            metadata_builder=metadata_builder or _create_default_metadata_builder(),
            extractor=extractor,
            hooks=hooks,
            error_policy=error_policy,
            transformer=transformer,
            post_transformer=post_transformer,
        )

    @staticmethod
    def _resolve_primary_key(config: PipelineConfig) -> tuple[str, str]:
        """Resolve entity primary key and API filter key based on config."""

        pk = config.primary_key

        if not pk and config.pipeline and "primary_key" in config.pipeline:
            pk = config.pipeline["primary_key"]

        if not pk:
            pk = f"{config.entity_name}_id"

        if not pk:
            raise ValueError(
                (
                    "Could not resolve ID_COLUMN for entity "
                    f"'{config.entity_name}'. Please set 'primary_key' "
                    "in config or pipeline options."
                )
            )

        return pk, f"{pk}__in"

    def get_version(self) -> str:
        """Возвращает версию релиза ChEMBL (например, 'chembl_34')."""
        if self._chembl_release is not None:
            return self._chembl_release

        if self._should_skip_release_lookup():
            self._chembl_release = "unknown"
            return self._chembl_release

        try:
            self._chembl_release = self._extraction_service.get_release_version()
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

    def _should_skip_release_lookup(self) -> bool:
        """True, если версию ChEMBL нужно пропустить (офлайн/CSV режим)."""
        input_mode = getattr(self._config, "input_mode", None)
        pipeline_cfg = getattr(self._config, "pipeline", {}) or {}
        if input_mode == "csv":
            return True
        return bool(pipeline_cfg.get("skip_release_lookup"))

    def extract(self, **kwargs: Any) -> Iterable[pd.DataFrame] | pd.DataFrame:  # type: ignore[override]
        return self._extractor.extract(**kwargs)

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:  # type: ignore[override]
        return self._transformer.apply(df)

    def write(
        self, df: pd.DataFrame, output_path: Path, context: RunContext
    ) -> WriteResult:  # type: ignore[override]
        return self._write_output(df, output_path, context)
