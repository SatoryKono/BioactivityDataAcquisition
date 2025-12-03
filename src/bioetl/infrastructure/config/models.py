from pathlib import Path
from typing import Annotated, Any, Literal, Optional

from pydantic import BaseModel, Field, PositiveInt, field_validator, model_validator


class PaginationConfig(BaseModel):
    limit: int = 1000
    offset: int = 0
    max_pages: Optional[int] = None


class ClientConfig(BaseModel):
    timeout: float = 30.0
    max_retries: int = 3
    rate_limit: float = 10.0
    backoff_factor: float = 2.0
    circuit_breaker_threshold: int = 5


class StorageConfig(BaseModel):
    output_path: str = "./data/output"
    cache_path: str = "./data/cache"
    temp_path: str = "./data/temp"


class LoggingConfig(BaseModel):
    level: str = "INFO"
    structured: bool = True
    redact_secrets: bool = True


class DeterminismConfig(BaseModel):
    stable_sort: bool = True
    utc_timestamps: bool = True
    canonical_json: bool = True
    atomic_writes: bool = True


class QcConfig(BaseModel):
    enable_quality_report: bool = True
    enable_correlation_report: bool = True
    min_coverage: float = 0.85


class HashingConfig(BaseModel):
    business_key_fields: list[str] = Field(default_factory=list)


class NormalizationConfig(BaseModel):
    """
    Конфигурация нормализации данных.
    """
    case_sensitive_fields: list[str] = Field(default_factory=list)
    id_fields: list[str] = Field(default_factory=list)
    custom_normalizers: dict[str, str] = Field(default_factory=dict)


# =============================================================================
# Source Configurations (Provider-specific)
# =============================================================================


class SourceConfigBase(BaseModel):
    """
    Базовая конфигурация источника данных.
    Все провайдер-специфичные конфиги наследуют от неё.
    """
    batch_size: Optional[PositiveInt] = None

    def resolve_effective_batch_size(
        self, limit: int | None = None, hard_cap: int | None = 25
    ) -> int:
        """
        Вычисляет эффективный размер батча.

        Приоритет:
        1. limit (если задан и меньше hard_cap)
        2. hard_cap (если задан и limit > hard_cap)
        3. self.batch_size (если задан)
        4. hard_cap (как дефолт)
        """
        effective_batch = self.batch_size or hard_cap or 25

        if hard_cap is not None:
            effective_batch = min(effective_batch, hard_cap)

        if limit is not None:
            effective_batch = min(effective_batch, limit)

        return effective_batch


class ChemblSourceConfig(SourceConfigBase):
    """
    Конфигурация источника ChEMBL.
    Все параметры подключения на верхнем уровне (без вложенного 'parameters').
    """
    provider: Literal["chembl"] = "chembl"
    base_url: str = "https://www.ebi.ac.uk/chembl/api/data"
    max_url_length: PositiveInt = 2000

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Ensure base_url doesn't have trailing slash."""
        return v.rstrip("/")


# Union type for discriminated source configs
# Add more providers here: ChemblSourceConfig | PubChemSourceConfig
SourceConfig = Annotated[
    ChemblSourceConfig,
    Field(discriminator="provider")
]


class CsvInputOptions(BaseModel):
    """Опции CSV-ввода."""

    delimiter: str = ","
    header: bool = True

    @field_validator("delimiter")
    @classmethod
    def validate_delimiter(cls, value: str) -> str:
        if not value:
            raise ValueError("CSV delimiter must be a non-empty string")
        return value


class PipelineConfig(BaseModel):
    """
    Полная конфигурация пайплайна.
    """
    provider: str
    entity_name: str
    primary_key: Optional[str] = None  # Added to support custom PKs like assay_chembl_id
    input_mode: Literal["csv", "id_only", "auto_detect"] = "auto_detect"
    input_path: str | None = None
    csv_options: CsvInputOptions = Field(default_factory=CsvInputOptions)

    # Sections
    pagination: PaginationConfig = Field(default_factory=PaginationConfig)
    client: ClientConfig = Field(default_factory=ClientConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    determinism: DeterminismConfig = Field(default_factory=DeterminismConfig)
    qc: QcConfig = Field(default_factory=QcConfig)
    hashing: HashingConfig = Field(default_factory=HashingConfig)
    normalization: NormalizationConfig = Field(
        default_factory=NormalizationConfig
    )

    # Sources configuration - keyed by provider name
    sources: dict[str, ChemblSourceConfig | dict[str, Any]] = Field(
        default_factory=dict
    )

    def get_source_config(self, provider: str) -> SourceConfigBase:
        """
        Get typed source config for provider.
        Handles both dict and typed config objects.
        """
        raw = self.sources.get(provider, {})
        if isinstance(raw, SourceConfigBase):
            return raw

        # Parse dict into typed config
        if provider == "chembl":
            return ChemblSourceConfig(**raw)

        raise ValueError(f"Unknown provider: {provider}")

    # Additional pipeline specific fields
    pipeline: dict[str, Any] = Field(default_factory=dict)
    fields: list[dict[str, Any]] = Field(default_factory=list)
    migration_messages: list[str] = Field(
        default_factory=list, repr=False, exclude=True
    )

    @model_validator(mode="before")
    @classmethod
    def migrate_cli_section(cls, values: dict[str, Any]) -> dict[str, Any]:
        cli_config = values.pop("cli", None) or {}
        if not cli_config:
            return values

        values.setdefault("input_path", cli_config.get("input_file"))

        if "input_mode" not in values:
            full_dataset_flag = cli_config.get("input_full_dataset")
            if full_dataset_flag is True:
                values["input_mode"] = "csv"
            elif full_dataset_flag is False:
                values["input_mode"] = "id_only"

        migration_hint = (
            "Deprecated 'cli' section detected. "
            "Use top-level input_mode/input_path/csv_options instead."
        )
        notes = values.setdefault("migration_messages", [])
        if migration_hint not in notes:
            notes.append(migration_hint)

        return values

    @field_validator("input_path")
    @classmethod
    def validate_input_path(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        path = Path(value)
        if not path.exists():
            raise ValueError(f"Input path does not exist: {value}")
        return str(path)

    @model_validator(mode="after")
    def validate_input_mode(self) -> "PipelineConfig":
        if self.input_mode in {"csv", "id_only"} and not self.input_path:
            raise ValueError(
                "input_path must be provided when input_mode is 'csv' or 'id_only'"
            )

        if self.input_mode == "csv" and not self.csv_options.header:
            raise ValueError(
                "csv_options.header must be true when input_mode is 'csv'"
            )

        if (
            self.input_mode == "auto_detect"
            and self.input_path
            and not self.csv_options.header
        ):
            raise ValueError(
                "csv_options.header must be true when input_mode is 'auto_detect' and input_path is set"
            )

        return self
