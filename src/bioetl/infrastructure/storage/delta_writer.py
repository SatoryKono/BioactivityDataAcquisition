"""Deprecated alias for SilverWriter (backward compatibility).

.. deprecated:: 1.0.0
    Use :class:`~bioetl.infrastructure.storage.silver_writer.SilverWriter` instead.
    DeltaWriter was renamed to SilverWriter to follow the Medallion layer naming
    convention (BronzeWriter, SilverWriter, GoldWriter).
    This alias will be removed after a 14-day deprecation period (RULES.md §6.2).

Migration guide:
    Replace::

        from bioetl.infrastructure.storage.delta_writer import DeltaWriter
        writer = DeltaWriter(...)

    With::

        from bioetl.infrastructure.storage.silver_writer import SilverWriter
        writer = SilverWriter(...)

Note:
    SilverWriteMode is re-exported here for backward compatibility.
    Import it from silver_writer or domain.medallion instead.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

# Re-export SilverWriteMode for backward compatibility
from bioetl.domain.medallion import SilverWriteMode
from bioetl.infrastructure.storage.silver_writer import SilverWriter

if TYPE_CHECKING:
    from pathlib import Path

    from bioetl.domain.medallion import WriteModePolicy
    from bioetl.domain.ports import (
        AuditPort,
        LoggerPort,
        MetricsPort,
        SilverValidatorPort,
        TracingPort,
    )
    from bioetl.infrastructure.export.csv_exporter import CsvExporter


__all__ = ["DeltaWriter", "SilverWriteMode"]


class DeltaWriter(SilverWriter):
    """Deprecated: Use SilverWriter instead.

    This class is a deprecated alias for SilverWriter. It was renamed to follow
    the Medallion layer naming convention (BronzeWriter, SilverWriter, GoldWriter).

    .. deprecated:: 1.0.0
        DeltaWriter will be removed after a 14-day deprecation period.
        Use SilverWriter instead.
    """

    def __init__(
        self,
        base_path: str | Path,
        logger: LoggerPort,
        tracing: TracingPort | None = None,
        csv_exporter: CsvExporter | None = None,
        write_policy: WriteModePolicy | None = None,
        metrics: MetricsPort | None = None,
        audit: AuditPort | None = None,
        silver_validator: SilverValidatorPort | None = None,
    ) -> None:
        """Initialize DeltaWriter (deprecated, use SilverWriter instead).

        Args:
            base_path: Base path for Delta tables (local filesystem)
            logger: Structured logger for observability (MUST be injected)
            tracing: TracingPort for distributed tracing
            csv_exporter: Optional CsvExporter for CSV output
            write_policy: Optional WriteModePolicy for medallion layer validation
            metrics: Optional MetricsPort for recording policy violation metrics
            audit: Optional AuditPort for write operation traceability
            silver_validator: Optional SilverValidatorPort for Pandera validation

        .. deprecated:: 1.0.0
            Use SilverWriter instead.
        """
        warnings.warn(
            "DeltaWriter is deprecated, use SilverWriter instead. "
            "DeltaWriter will be removed after a 14-day deprecation period.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(
            base_path=base_path,
            logger=logger,
            tracing=tracing,
            csv_exporter=csv_exporter,
            write_policy=write_policy,
            metrics=metrics,
            audit=audit,
            silver_validator=silver_validator,
        )
