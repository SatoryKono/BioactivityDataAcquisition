from typing import Any, Optional, Union
from pydantic import BaseModel, Field, PositiveInt


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


class SourceConfig(BaseModel):
    """
    Базовая конфигурация источника данных.
    """
    batch_size: Optional[PositiveInt] = None
    parameters: dict[str, Any] = Field(default_factory=dict)

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


class PipelineConfig(BaseModel):
    """
    Полная конфигурация пайплайна.
    """
    provider: str
    entity_name: str
    
    # Sections
    pagination: PaginationConfig = Field(default_factory=PaginationConfig)
    client: ClientConfig = Field(default_factory=ClientConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    determinism: DeterminismConfig = Field(default_factory=DeterminismConfig)
    qc: QcConfig = Field(default_factory=QcConfig)
    hashing: HashingConfig = Field(default_factory=HashingConfig)
    normalization: NormalizationConfig = Field(default_factory=NormalizationConfig)
    
    # Sources configuration
    # Use ForwardRef or check resolver logic if circular imports occur.
    # Here we accept dict or specialized config.
    # The resolver or post-init logic should handle specific instantiation if needed,
    # or we use a Union if we can import subclasses without cycles.
    # Given constraints, we will allow generic access here and specialized validation in resolver.
    # However, to support Pydantic validation, we'd ideally include types here.
    # We will assume dynamic loading or generic dict structure at this base level
    # UNLESS we import source_chembl here. But source_chembl imports models.py (SourceConfig).
    # So we avoid importing ChemblSourceConfig here to prevent circular import.
    sources: dict[str, Any] = Field(default_factory=dict)
    
    # Additional pipeline specific fields
    pipeline: dict[str, Any] = Field(default_factory=dict)
    cli: dict[str, Any] = Field(default_factory=dict)
    fields: list[dict[str, Any]] = Field(default_factory=list)
    
    # Business key definition
    # DEPRECATED: Use hashing.business_key_fields instead.
    # This field is kept for backward compatibility but will be removed in future versions.
    business_key: list[str] = Field(default_factory=list, description="Deprecated: Use hashing.business_key_fields")
