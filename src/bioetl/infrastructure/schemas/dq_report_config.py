# mypy: disable-error-code="misc"
"""Schema validation for DQ report configuration.

Pydantic models for parsing DQ report configuration from YAML files.
Each model has a `to_domain()` method for converting to domain value objects.

Implements the DQ report strategy for Medallion Architecture layers.
"""

from __future__ import annotations

import contextlib
from typing import Literal

from pydantic import BaseModel, Field

from bioetl.domain.value_objects.dq_report import (
    BronzeDQCheckType,
    DQReportFormat,
    GoldDQCheckType,
    SilverDQCheckType,
)

_DQ_REPORT_ENABLED_DESCRIPTION = "Enable DQ report generation (default: disabled)"
_DQ_REPORT_OUTPUT_PATH_DESCRIPTION = (
    "Output path for report. None = alongside data files."
)
_DQ_REPORT_OUTPUT_FORMAT_DESCRIPTION = "Report output format"
_DQ_REPORT_CHECKS_DESCRIPTION = "List of DQ checks to perform"


class BronzeDQReportConfig(BaseModel):
    """Configuration for Bronze layer DQ report generation.

    Bronze DQ reports focus on minimal validation: record counts,
    file integrity, and schema snapshots for lineage tracking.

    Attributes:
        enabled: Whether to generate DQ report (default: False).
        output_path: Path for report output. None = alongside data.
        format: Output format (json, yaml, html).
        checks: List of checks to perform.
    """

    enabled: bool = Field(
        default=False,
        description=_DQ_REPORT_ENABLED_DESCRIPTION,
    )
    output_path: str | None = Field(
        default=None,
        description=_DQ_REPORT_OUTPUT_PATH_DESCRIPTION,
    )
    format: Literal["json", "yaml", "html"] = Field(
        default="json",
        description=_DQ_REPORT_OUTPUT_FORMAT_DESCRIPTION,
    )
    checks: list[str] = Field(
        default_factory=lambda: [
            BronzeDQCheckType.RECORD_COUNT.value,
            BronzeDQCheckType.FILE_INTEGRITY.value,
            BronzeDQCheckType.SCHEMA_SNAPSHOT.value,
        ],
        description=_DQ_REPORT_CHECKS_DESCRIPTION,
    )

    def get_format_enum(self) -> DQReportFormat:
        """Get format as enum.

        Returns:
            Format enum.
        """
        return DQReportFormat(self.format)

    def get_checks_enums(self) -> list[BronzeDQCheckType]:
        """Get checks as enums, filtering invalid values.

        Returns:
            Checks enums.
        """
        result = []
        for check in self.checks:
            with contextlib.suppress(ValueError):
                result.append(BronzeDQCheckType(check))
        return result


class SilverDQReportConfig(BaseModel):
    """Configuration for Silver layer DQ report generation.

    Silver DQ reports focus on data quality monitoring: null rates,
    uniqueness, type conformance, schema drift, and deduplication stats.

    Attributes:
        enabled: Whether to generate DQ report (default: False).
        output_path: Path for report output. None = alongside data.
        format: Output format (json, yaml, html).
        checks: List of checks to perform.
    """

    enabled: bool = Field(
        default=False,
        description=_DQ_REPORT_ENABLED_DESCRIPTION,
    )
    output_path: str | None = Field(
        default=None,
        description=_DQ_REPORT_OUTPUT_PATH_DESCRIPTION,
    )
    format: Literal["json", "yaml", "html"] = Field(
        default="json",
        description=_DQ_REPORT_OUTPUT_FORMAT_DESCRIPTION,
    )
    checks: list[str] = Field(
        default_factory=lambda: [
            SilverDQCheckType.RECORD_COUNT.value,
            SilverDQCheckType.NULL_RATE.value,
            SilverDQCheckType.UNIQUENESS.value,
            SilverDQCheckType.TYPE_CONFORMANCE.value,
            SilverDQCheckType.VALUE_DISTRIBUTION.value,
            SilverDQCheckType.SCHEMA_DRIFT.value,
            SilverDQCheckType.DEDUPLICATION_STATS.value,
            SilverDQCheckType.KEY_NULLABILITY.value,
        ],
        description=_DQ_REPORT_CHECKS_DESCRIPTION,
    )

    def get_format_enum(self) -> DQReportFormat:
        """Get format as enum.

        Returns:
            Format enum.
        """
        return DQReportFormat(self.format)

    def get_checks_enums(self) -> list[SilverDQCheckType]:
        """Get checks as enums, filtering invalid values.

        Returns:
            Checks enums.
        """
        result = []
        for check in self.checks:
            with contextlib.suppress(ValueError):
                result.append(SilverDQCheckType(check))
        return result


class GoldDQReportConfig(BaseModel):
    """Configuration for Gold layer DQ report generation.

    Gold DQ reports focus on strict validation: completeness,
    business rules, referential integrity, and anomaly detection.

    Attributes:
        enabled: Whether to generate DQ report (default: False).
        output_path: Path for report output. None = alongside data.
        format: Output format (json, yaml, html).
        checks: List of checks to perform.
    """

    enabled: bool = Field(
        default=False,
        description=_DQ_REPORT_ENABLED_DESCRIPTION,
    )
    output_path: str | None = Field(
        default=None,
        description=_DQ_REPORT_OUTPUT_PATH_DESCRIPTION,
    )
    format: Literal["json", "yaml", "html"] = Field(
        default="json",
        description=_DQ_REPORT_OUTPUT_FORMAT_DESCRIPTION,
    )
    checks: list[str] = Field(
        default_factory=lambda: [
            GoldDQCheckType.RECORD_COUNT.value,
            GoldDQCheckType.COMPLETENESS.value,
            GoldDQCheckType.BUSINESS_RULES.value,
            GoldDQCheckType.REFERENTIAL_INTEGRITY.value,
            GoldDQCheckType.STATISTICAL_PROFILE.value,
            GoldDQCheckType.ANOMALY_DETECTION.value,
        ],
        description=_DQ_REPORT_CHECKS_DESCRIPTION,
    )

    def get_format_enum(self) -> DQReportFormat:
        """Get format as enum.

        Returns:
            Format enum.
        """
        return DQReportFormat(self.format)

    def get_checks_enums(self) -> list[GoldDQCheckType]:
        """Get checks as enums, filtering invalid values.

        Returns:
            Checks enums.
        """
        result = []
        for check in self.checks:
            with contextlib.suppress(ValueError):
                result.append(GoldDQCheckType(check))
        return result


class BronzeSinkConfig(BaseModel):
    """Bronze sink configuration with optional DQ report.

    Extends base bronze sink config with DQ report generation.
    """

    path: str = Field(description="Base path for Bronze data")
    format: Literal["jsonl"] = Field(default="jsonl")
    compression: Literal["zstd", "gzip", "none"] = Field(default="zstd")
    dq_report: BronzeDQReportConfig = Field(default_factory=BronzeDQReportConfig)


class SilverSinkConfig(BaseModel):
    """Silver sink configuration with optional DQ report.

    Unified schema for Silver layer sink configuration.
    Includes both metadata and DQ report settings.
    """

    path: str = Field(description="Base path for Silver data")
    format: Literal["delta"] = Field(default="delta")
    mode: Literal["merge", "append", "overwrite"] = Field(default="merge")
    primary_key: list[str] = Field(default_factory=list)
    partition_by: list[str] = Field(default_factory=list)
    # Metadata sidecar support
    save_metadata: bool = Field(
        default=False,
        description="Save _metadata.yaml sidecar file with lineage and QC info",
    )
    # DQ report config
    dq_report: SilverDQReportConfig = Field(default_factory=SilverDQReportConfig)
    # Schema drift handling
    on_schema_mismatch: Literal["error", "evolve", "ignore"] = Field(
        default="error",
        description="How to handle schema drift",
    )


class GoldSinkConfig(BaseModel):
    """Gold sink configuration with optional DQ report.

    Extends base gold sink config with DQ report generation.
    """

    path: str = Field(description="Base path for Gold data")
    format: Literal["delta"] = Field(default="delta")
    mode: Literal["append", "overwrite", "scd2"] = Field(default="overwrite")
    dq_report: GoldDQReportConfig = Field(default_factory=GoldDQReportConfig)


__all__ = [
    "BronzeDQReportConfig",
    "BronzeSinkConfig",
    "GoldDQReportConfig",
    "GoldSinkConfig",
    "SilverDQReportConfig",
    "SilverSinkConfig",
]
