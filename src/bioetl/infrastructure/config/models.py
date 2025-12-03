from typing import Annotated, Any, Literal, Optional
from pydantic import BaseModel, Field, PositiveInt, field_validator


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


class NestedLookupConfig(BaseModel):
    """
    Конфигурация для вложенных запросов.

    Используется для data_validity, assay_enrichment и подобных.
    """
    enabled: bool = True
    fields: list[str] = Field(default_factory=list)
    page_limit: PositiveInt = 10
    request_timeout: float = 10.0
    max_retries: int = 3
    retry_backoff: float = 1.0


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
    data_validity: Optional[NestedLookupConfig] = None
    assay_enrichment: Optional[NestedLookupConfig] = None

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


class PipelineConfig(BaseModel):
    """
    Полная конфигурация пайплайна.
    """
    provider: str
    entity_name: str
    primary_key: Optional[str] = None  # Added to support custom PKs like assay_chembl_id

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
    cli: dict[str, Any] = Field(default_factory=dict)
    fields: list[dict[str, Any]] = Field(default_factory=list)
