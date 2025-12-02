from typing import Optional

from pydantic import BaseModel, PositiveInt, Field
from bioetl.infrastructure.config.models import SourceConfig


class ChemblNestedLookupConfig(BaseModel):
    """
    Конфигурация для вложенных запросов (например, для data_validity).
    """
    enabled: bool = True
    fields: list[str] = Field(default_factory=list)
    page_limit: PositiveInt = 10
    request_timeout: float = 10.0
    max_retries: int = 3
    retry_backoff: float = 1.0


class ChemblSourceParameters(BaseModel):
    """
    Параметры подключения к ChEMBL.
    """
    base_url: str
    max_url_length: PositiveInt = 2000
    data_validity: Optional[ChemblNestedLookupConfig] = None
    assay_enrichment: Optional[ChemblNestedLookupConfig] = None


class ChemblSourceConfig(SourceConfig):
    """
    Специализированная конфигурация источника ChEMBL.
    """
    parameters: ChemblSourceParameters

