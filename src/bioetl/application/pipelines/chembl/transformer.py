"""
ChEMBL data transformer implementation.
"""

import pandas as pd

from bioetl.domain.models import RunContext
from bioetl.domain.normalization_service import NormalizationService
from bioetl.domain.schemas.pipeline_contracts import PipelineSchemaContract
from bioetl.domain.transform.transformers import TransformerABC
from bioetl.domain.validation.service import ValidationService
from bioetl.infrastructure.logging.contracts import LoggerAdapterABC


class ChemblTransformerImpl(TransformerABC):
    """
    Transformer for ChEMBL data.

    Chain:
    pre_transform -> do_transform -> normalize -> enforce_schema -> drop nulls
    """

    def __init__(
        self,
        validation_service: ValidationService,
        schema_contract: PipelineSchemaContract,
        normalization_service: NormalizationService,
        logger: LoggerAdapterABC,
    ) -> None:
        self.validation_service = validation_service
        self.schema_contract = schema_contract
        self.normalization_service = normalization_service
        self.logger = logger

    def apply(
        self, df: pd.DataFrame, context: RunContext | None = None
    ) -> pd.DataFrame:
        df = self.pre_transform(df)
        df = self.do_transform(df)
        df = self.normalization_service.normalize_dataframe(df)
        df = self._enforce_schema(df)
        df = self._drop_nulls_in_required_columns(df)
        return df

    def pre_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Hook for pre-transformation."""
        return df

    def do_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Main transformation logic."""
        return df

    def _enforce_schema(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Ensures DataFrame matches the output schema columns.
        """
        schema_name = self.schema_contract.schema_out
        schema_columns = self.validation_service.get_schema_columns(schema_name)

        for col in schema_columns:
            if col not in df.columns:
                df[col] = None

        return df[schema_columns]

    def _drop_nulls_in_required_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Drops rows with nulls in required columns.
        """
        schema_name = self.schema_contract.schema_out
        schema_cls = self.validation_service.get_schema(schema_name)
        schema = schema_cls.to_schema()

        ignored_cols = {
            "hash_row",
            "hash_business_key",
            "index",
            "database_version",
            "extracted_at",
        }

        required_cols = [
            name
            for name, col in schema.columns.items()
            if not col.nullable and name in df.columns and name not in ignored_cols
        ]

        if not required_cols:
            return df

        initial_count = len(df)
        df_clean = df.dropna(subset=required_cols)
        dropped_count = initial_count - len(df_clean)

        if dropped_count > 0:
            self.logger.warning(
                f"Dropped {dropped_count} rows with nulls in required columns: {required_cols}"
            )

        return df_clean
