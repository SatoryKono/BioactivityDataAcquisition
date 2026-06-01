"""Unit tests for DQ services factory.

Tests the DQServicesFactory for creating DQ analyzers and report writers.
"""

from __future__ import annotations

import pytest

from pathlib import Path
from unittest.mock import MagicMock


from bioetl.composition.factories.dq.factory import DQServicesFactory
from bioetl.domain.ports import (
    BronzeDQAnalyzerPort,
    DQReportWriterPort,
    GoldDQAnalyzerPort,
    SilverDQAnalyzerPort,
)


pytestmark = pytest.mark.unit

class TestDQServicesFactory:
    """Tests for DQServicesFactory."""

    def test_create_bronze_analyzer_returns_port(self) -> None:
        """create_bronze_analyzer should return BronzeDQAnalyzerPort."""
        analyzer = DQServicesFactory.create_bronze_analyzer()

        assert isinstance(analyzer, BronzeDQAnalyzerPort)
        assert hasattr(analyzer, "analyze")

    def test_create_silver_analyzer_returns_port(self) -> None:
        """create_silver_analyzer should return SilverDQAnalyzerPort."""
        analyzer = DQServicesFactory.create_silver_analyzer()

        assert isinstance(analyzer, SilverDQAnalyzerPort)
        assert hasattr(analyzer, "analyze")

    def test_create_gold_analyzer_returns_port(self) -> None:
        """create_gold_analyzer should return GoldDQAnalyzerPort."""
        analyzer = DQServicesFactory.create_gold_analyzer()

        assert isinstance(analyzer, GoldDQAnalyzerPort)
        assert hasattr(analyzer, "analyze")

    def test_create_report_writer_returns_port(self, tmp_path: Path) -> None:
        """create_report_writer should return DQReportWriterPort."""
        logger = MagicMock()

        writer = DQServicesFactory.create_report_writer(
            base_path=tmp_path,
            logger=logger,
        )

        assert isinstance(writer, DQReportWriterPort)
        assert hasattr(writer, "write_bronze_report")
        assert hasattr(writer, "write_silver_report")
        assert hasattr(writer, "write_gold_report")

    def test_create_report_writer_accepts_string_path(self, tmp_path: Path) -> None:
        """create_report_writer should accept string path."""
        logger = MagicMock()

        writer = DQServicesFactory.create_report_writer(
            base_path=str(tmp_path),
            logger=logger,
        )

        assert isinstance(writer, DQReportWriterPort)

    def test_analyzers_are_independent_instances(self) -> None:
        """Each factory method should return a new instance."""
        bronze1 = DQServicesFactory.create_bronze_analyzer()
        bronze2 = DQServicesFactory.create_bronze_analyzer()

        assert bronze1 is not bronze2

    def test_all_analyzers_have_analyze_method(self) -> None:
        """All analyzers should have the analyze method."""
        bronze = DQServicesFactory.create_bronze_analyzer()
        silver = DQServicesFactory.create_silver_analyzer()
        gold = DQServicesFactory.create_gold_analyzer()

        assert callable(getattr(bronze, "analyze", None))
        assert callable(getattr(silver, "analyze", None))
        assert callable(getattr(gold, "analyze", None))
