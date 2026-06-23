"""DQ Config port interfaces (Protocols).

Defines interfaces for DQ report configuration following
the Ports & Adapters architecture (RULES.md §1.1).

These protocols enable domain services to depend on abstractions
rather than concrete infrastructure classes (Pydantic models).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from bioetl.domain.value_objects.dq_report import (
        BronzeDQCheckType,
        DQReportFormat,
        GoldDQCheckType,
        SilverDQCheckType,
    )


@runtime_checkable
class BronzeDQConfigPort(Protocol):
    """Protocol for Bronze layer DQ report configuration.

    Defines the interface that configuration objects must implement
    to be usable by BronzeDQAnalyzer and DQReportService.
    """

    @property
    def enabled(self) -> bool:
        """Whether DQ report generation is enabled."""
        ...

    @property
    def output_path(self) -> str | None:
        """Output path for report. None = alongside data files."""
        ...

    def get_checks_enums(self) -> list[BronzeDQCheckType]:
        """Get list of enabled check types.

        Returns:
            List of BronzeDQCheckType values for enabled checks.
        """
        ...

    def get_format_enum(self) -> DQReportFormat:
        """Get output format as enum.

        Returns:
            DQReportFormat for report output.
        """
        ...


@runtime_checkable
class SilverDQConfigPort(Protocol):
    """Protocol for Silver layer DQ report configuration.

    Defines the interface that configuration objects must implement
    to be usable by SilverDQAnalyzer and DQReportService.
    """

    @property
    def enabled(self) -> bool:
        """Whether DQ report generation is enabled."""
        ...

    @property
    def output_path(self) -> str | None:
        """Output path for report. None = alongside data files."""
        ...

    def get_checks_enums(self) -> list[SilverDQCheckType]:
        """Get list of enabled check types.

        Returns:
            List of SilverDQCheckType values for enabled checks.
        """
        ...

    def get_format_enum(self) -> DQReportFormat:
        """Get output format as enum.

        Returns:
            DQReportFormat for report output.
        """
        ...


@runtime_checkable
class GoldDQConfigPort(Protocol):
    """Protocol for Gold layer DQ report configuration.

    Defines the interface that configuration objects must implement
    to be usable by GoldDQAnalyzer and DQReportService.
    """

    @property
    def enabled(self) -> bool:
        """Whether DQ report generation is enabled."""
        ...

    @property
    def output_path(self) -> str | None:
        """Output path for report. None = alongside data files."""
        ...

    def get_checks_enums(self) -> list[GoldDQCheckType]:
        """Get list of enabled check types.

        Returns:
            List of GoldDQCheckType values for enabled checks.
        """
        ...

    def get_format_enum(self) -> DQReportFormat:
        """Get output format as enum.

        Returns:
            DQReportFormat for report output.
        """
        ...


__all__ = [
    "BronzeDQConfigPort",
    "GoldDQConfigPort",
    "SilverDQConfigPort",
]
