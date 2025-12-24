"""Configuration objects for application core components."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from bioetl.domain.config import DQConfig, TableConfig


@dataclass(frozen=True)
class RecordProcessorConfig:
    """Configuration for RecordProcessor."""

    pipeline_name: str
    provider: str
    entity_type: str
    silver_schema: Any
    gold_schema: Any | None = None
    dq_config: DQConfig | None = None
    table_config: TableConfig = field(default_factory=TableConfig)
