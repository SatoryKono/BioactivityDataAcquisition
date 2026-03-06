"""Summary and layer-specific DQ report objects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from bioetl.domain.medallion import Layer as MedallionLayer
from bioetl.domain.types import JsonDict
from bioetl.domain.value_objects.dq_report_enums import DQCheckStatus, DQReportStatus
from bioetl.domain.value_objects.dq_report_results import DataFreshnessResult


@dataclass(frozen=True, slots=True)
class DQReportSummary:
    """Summary of DQ report results."""

    total_checks: int
    passed: int
    failed: int
    warnings: int
    overall_status: DQReportStatus


@dataclass(frozen=True, slots=True)
class DQThresholds:
    """DQ threshold configuration used in report."""

    soft_fail_threshold: float
    hard_fail_threshold: float
    current_error_rate: float
    threshold_status: DQCheckStatus


# =============================================================================
# Main Report Value Objects
# =============================================================================


@dataclass(frozen=True, slots=True)
class BronzeDQReport:
    """DQ report for Bronze layer.

    Attributes:
        layer: Always MedallionLayer.BRONZE.
        timestamp: Report generation timestamp (UTC).
        run_id: Pipeline run identifier.
        pipeline: Pipeline name.
        batch_id: Batch identifier.
        source_file: Path to the Bronze file.
        checks: Dictionary of check type to result.
        summary: Report summary.
    """

    layer: MedallionLayer
    timestamp: datetime
    run_id: str
    pipeline: str
    batch_id: str
    source_file: str
    checks: JsonDict
    summary: DQReportSummary

    def __post_init__(self) -> None:
        """Validate layer is BRONZE."""
        if self.layer != MedallionLayer.BRONZE:
            raise ValueError(f"BronzeDQReport layer must be BRONZE, got {self.layer}")


@dataclass(frozen=True, slots=True)
class SilverDQReport:
    """DQ report for Silver layer.

    Attributes:
        layer: Always MedallionLayer.SILVER.
        timestamp: Report generation timestamp (UTC).
        run_id: Pipeline run identifier.
        pipeline: Pipeline name.
        source_batch_ids: List of Bronze batch IDs processed.
        target_table: Silver table path.
        checks: Dictionary of check type to result.
        thresholds: DQ threshold configuration.
        summary: Report summary.
        metadata_path: Path to corresponding _metadata.yaml file (if generated).
    """

    layer: MedallionLayer
    timestamp: datetime
    run_id: str
    pipeline: str
    source_batch_ids: tuple[str, ...]
    target_table: str
    checks: JsonDict
    thresholds: DQThresholds
    summary: DQReportSummary
    # Cross-reference to metadata
    metadata_path: str | None = None

    def __post_init__(self) -> None:
        """Validate layer and convert lists."""
        if self.layer != MedallionLayer.SILVER:
            raise ValueError(f"SilverDQReport layer must be SILVER, got {self.layer}")
        if isinstance(self.source_batch_ids, list):
            object.__setattr__(self, "source_batch_ids", tuple(self.source_batch_ids))


@dataclass(frozen=True, slots=True)
class GoldDQReport:
    """DQ report for Gold layer.

    Attributes:
        layer: Always MedallionLayer.GOLD.
        timestamp: Report generation timestamp (UTC).
        run_id: Pipeline run identifier.
        pipeline: Pipeline name.
        target_table: Gold table path.
        checks: Dictionary of check type to result.
        data_freshness: Data freshness information.
        summary: Report summary.
    """

    layer: MedallionLayer
    timestamp: datetime
    run_id: str
    pipeline: str
    target_table: str
    checks: JsonDict
    data_freshness: DataFreshnessResult | None
    summary: DQReportSummary

    def __post_init__(self) -> None:
        """Validate layer is GOLD."""
        if self.layer != MedallionLayer.GOLD:
            raise ValueError(f"GoldDQReport layer must be GOLD, got {self.layer}")


__all__ = [
    "BronzeDQReport",
    "DQReportSummary",
    "DQThresholds",
    "GoldDQReport",
    "MedallionLayer",
    "SilverDQReport",
]
