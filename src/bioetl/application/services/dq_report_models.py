"""Shared models and error tuple for DQ report orchestration."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from bioetl.domain.exceptions import BioETLError, DataQualityError, StorageError
from bioetl.domain.types import GoldBusinessRuleSpec, JsonDict, ScdConfig

_DQ_REPORT_ERRORS = (
    DataQualityError,
    StorageError,
    BioETLError,
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
)


@dataclass(frozen=True, slots=True)
class DQReportResult:
    """Result of DQ report generation for all layers."""

    bronze_report_path: Path | None = None
    silver_report_path: Path | None = None
    gold_report_path: Path | None = None
    bronze_enabled: bool = False
    silver_enabled: bool = False
    gold_enabled: bool = False

    @property
    def any_generated(self) -> bool:
        """Check if any report was generated."""
        return any(
            [
                self.bronze_report_path is not None,
                self.silver_report_path is not None,
                self.gold_report_path is not None,
            ]
        )

    @property
    def reports_count(self) -> int:
        """Count of generated reports."""
        return sum(
            [
                self.bronze_report_path is not None,
                self.silver_report_path is not None,
                self.gold_report_path is not None,
            ]
        )


@dataclass(frozen=True, slots=True)
class DQReportContext:
    """Context for DQ report generation."""

    run_id: str
    pipeline_name: str
    timestamp: datetime

    provider: str | None = None
    entity: str | None = None

    bronze_source_file: str | None = None
    bronze_batch_id: str | None = None
    bronze_records: list[bytes] | None = None
    bronze_output_path: str | None = None
    bronze_date_str: str | None = None

    silver_data: Any | None = None  # Any: pl.DataFrame (avoids polars import)
    silver_target_table: str | None = None
    silver_source_batch_ids: list[str] | None = None
    silver_primary_keys: list[str] | None = None
    silver_input_count: int | None = None
    silver_quarantined_count: int = 0
    silver_previous_schema: dict[str, str] | None = None
    silver_output_path: str | None = None
    silver_key_nullability_rules: (
        list[JsonDict]  # Any: DQ rule definitions have heterogeneous values
        | None
    ) = None

    gold_data: Any | None = None  # Any: pl.DataFrame (avoids polars import)
    gold_target_table: str | None = None
    gold_required_fields: list[str] | None = None
    gold_business_rules: list[GoldBusinessRuleSpec] | None = None
    gold_baseline_stats: JsonDict | None = None  # Any: heterogeneous DQ metrics
    gold_scd_config: ScdConfig | None = None
    gold_contract_version: str | None = None
    gold_output_path: str | None = None

    dq_soft_threshold: float = 0.05
    dq_hard_threshold: float = 0.20

    flat_structure: bool = False

    def __post_init__(self) -> None:
        """Coerce legacy mapping payloads into typed Gold report contracts."""
        if self.gold_business_rules is not None:
            object.__setattr__(
                self,
                "gold_business_rules",
                [
                    rule
                    if isinstance(rule, GoldBusinessRuleSpec)
                    else GoldBusinessRuleSpec.from_mapping(
                        rule,
                        default_contract_version=self.gold_contract_version,
                    )
                    for rule in self.gold_business_rules
                ],
            )
        if isinstance(self.gold_scd_config, Mapping):
            object.__setattr__(
                self,
                "gold_scd_config",
                ScdConfig.from_mapping(self.gold_scd_config),
            )


__all__ = [
    "_DQ_REPORT_ERRORS",
    "DQReportContext",
    "DQReportResult",
]
