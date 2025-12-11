"""Factories composing loaders for pipeline artifacts.

Naming convention:
- create_*() - creates a new instance each time
- get_*() - returns singleton/cached instance
- build_*() - uses builder pattern
"""

from typing import Any
import warnings

from bioetl.domain.clients.base.output.contracts import (
    OutputFrameConverterABC,
    QualityReportABC,
)
from bioetl.domain.configs import DeterminismConfig, QcConfig
from bioetl.domain.observability import MetricsPortABC
from bioetl.infrastructure.output.impl.csv_writer import CsvWriter
from bioetl.infrastructure.output.impl.metadata_writer import MetadataWriter
from bioetl.infrastructure.output.impl.quality_report import QualityReportImpl
from bioetl.infrastructure.output.unified_loader_impl import (
    UnifiedLoaderImpl,
)


def create_writer() -> CsvWriter:
    """Create a new CSV writer instance."""

    return CsvWriter()


def create_metadata_writer() -> MetadataWriter:
    """Create a new metadata writer instance."""

    return MetadataWriter()


def create_quality_reporter() -> QualityReportABC:
    """Create a new quality report writer instance."""

    return QualityReportImpl()


def create_loader(
    *,
    config: DeterminismConfig,
    qc_config: QcConfig | None = None,
    writer: Any | None = None,
    metadata_writer: Any | None = None,
    quality_reporter: QualityReportABC | None = None,
    metrics_port: MetricsPortABC | None = None,
    converter: OutputFrameConverterABC | None = None,
) -> UnifiedLoaderImpl:
    """Create a new unified loader with optional overrides."""

    return UnifiedLoaderImpl(
        writer=writer or create_writer(),
        metadata_writer=metadata_writer or create_metadata_writer(),
        quality_reporter=quality_reporter or create_quality_reporter(),
        config=config,
        qc_config=qc_config,
        metrics=metrics_port,
        converter=converter,
    )


# ---------------------------------------------------------------------------
# Deprecated aliases for backward compatibility
# ---------------------------------------------------------------------------


def default_writer() -> CsvWriter:
    """DEPRECATED: Use create_writer() instead."""
    warnings.warn(
        "default_writer is deprecated, use create_writer instead. "
        "Will be removed in v3.0.",
        DeprecationWarning,
        stacklevel=2,
    )
    return create_writer()


def default_metadata_writer() -> MetadataWriter:
    """DEPRECATED: Use create_metadata_writer() instead."""
    warnings.warn(
        "default_metadata_writer is deprecated, use create_metadata_writer instead. "
        "Will be removed in v3.0.",
        DeprecationWarning,
        stacklevel=2,
    )
    return create_metadata_writer()


def default_quality_reporter() -> QualityReportABC:
    """DEPRECATED: Use create_quality_reporter() instead."""
    warnings.warn(
        "default_quality_reporter is deprecated, use create_quality_reporter instead. "
        "Will be removed in v3.0.",
        DeprecationWarning,
        stacklevel=2,
    )
    return create_quality_reporter()


def default_loader(
    *,
    config: DeterminismConfig,
    qc_config: QcConfig | None = None,
    writer: Any | None = None,
    metadata_writer: Any | None = None,
    quality_reporter: QualityReportABC | None = None,
    metrics_port: MetricsPortABC | None = None,
    converter: OutputFrameConverterABC | None = None,
) -> UnifiedLoaderImpl:
    """DEPRECATED: Use create_loader() instead."""
    warnings.warn(
        "default_loader is deprecated, use create_loader instead. "
        "Will be removed in v3.0.",
        DeprecationWarning,
        stacklevel=2,
    )
    return create_loader(
        config=config,
        qc_config=qc_config,
        writer=writer,
        metadata_writer=metadata_writer,
        quality_reporter=quality_reporter,
        metrics_port=metrics_port,
        converter=converter,
    )
