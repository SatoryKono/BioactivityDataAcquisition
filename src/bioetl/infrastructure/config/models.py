from typing import Any, Optional
from pydantic import BaseModel, Field


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
    
    # Additional pipeline specific fields
    pipeline: dict[str, Any] = Field(default_factory=dict)
    cli: dict[str, Any] = Field(default_factory=dict)
    fields: list[dict[str, Any]] = Field(default_factory=list)
    
    # Business key definition
    business_key: list[str] = Field(default_factory=list)

