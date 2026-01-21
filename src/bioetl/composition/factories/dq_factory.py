"""Factory for DQ report components.

Creates DQ analyzers and report writers following the DI pattern.
All components are created in the composition layer and injected
into pipeline services.

Usage:
    >>> from bioetl.composition.factories.dq_factory import DQServicesFactory
    >>> analyzer = DQServicesFactory.create_bronze_analyzer()
    >>> writer = DQServicesFactory.create_report_writer(base_path, logger)
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.application.services.dq import (
    BronzeDQAnalyzer,
    GoldDQAnalyzer,
    SilverDQAnalyzer,
)
from bioetl.infrastructure.export.dq_report_writer import DQReportWriter

if TYPE_CHECKING:
    from bioetl.domain.ports import (
        BronzeDQAnalyzerPort,
        DQReportWriterPort,
        GoldDQAnalyzerPort,
        LoggerPort,
        SilverDQAnalyzerPort,
    )


class DQServicesFactory:
    """Factory for creating DQ analysis and reporting services.

    All methods are static factory methods following the composition pattern.
    Services are created lazily only when DQ reporting is enabled.

    Example:
        >>> factory = DQServicesFactory()
        >>> bronze_analyzer = DQServicesFactory.create_bronze_analyzer()
        >>> silver_analyzer = DQServicesFactory.create_silver_analyzer()
        >>> gold_analyzer = DQServicesFactory.create_gold_analyzer()
        >>> writer = DQServicesFactory.create_report_writer(Path("/data"), logger)
    """

    @staticmethod
    def create_bronze_analyzer() -> BronzeDQAnalyzerPort:
        """Create Bronze layer DQ analyzer.

        Returns:
            BronzeDQAnalyzerPort implementation for analyzing raw Bronze data.
        """
        return BronzeDQAnalyzer()

    @staticmethod
    def create_silver_analyzer() -> SilverDQAnalyzerPort:
        """Create Silver layer DQ analyzer.

        Returns:
            SilverDQAnalyzerPort implementation for analyzing normalized Silver data.
        """
        return SilverDQAnalyzer()

    @staticmethod
    def create_gold_analyzer() -> GoldDQAnalyzerPort:
        """Create Gold layer DQ analyzer.

        Returns:
            GoldDQAnalyzerPort implementation for analyzing Gold data marts.
        """
        return GoldDQAnalyzer()

    @staticmethod
    def create_report_writer(
        base_path: str | Path,
        logger: LoggerPort,
        flat_structure: bool = False,
    ) -> DQReportWriterPort:
        """Create DQ report writer.

        Args:
            base_path: Base path for report storage.
            logger: Structured logger for observability.
            flat_structure: If True, write reports directly to base_path
                          with {layer}_{provider}_{entity}_dq_report{ext} naming.

        Returns:
            DQReportWriterPort implementation for writing reports to filesystem.
        """
        return DQReportWriter(
            base_path=base_path,
            logger=logger,
            flat_structure=flat_structure,
        )


__all__ = ["DQServicesFactory"]
