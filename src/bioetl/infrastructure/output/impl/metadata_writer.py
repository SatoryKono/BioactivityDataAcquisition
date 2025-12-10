"""Writers for pipeline metadata and QC artifacts."""

from pathlib import Path

import pandas as pd
import yaml

from bioetl.domain.clients.base.output.contracts import QualityReportABC
from bioetl.infrastructure.files.atomic import AtomicFileOperation
from bioetl.infrastructure.files.checksum import compute_files_sha256
from bioetl.infrastructure.output.impl.quality_report import QualityReportImpl


def build_quality_report_table(
    df: pd.DataFrame,
    *,
    min_coverage: float,
    quality_reporter: QualityReportABC | None = None,
) -> pd.DataFrame:
    """Build a QC summary table for the provided dataframe using Pandera reporter."""

    reporter = quality_reporter or QualityReportImpl()
    return reporter.build_quality_report(df, min_coverage=min_coverage)


class MetadataWriterImpl:
    """
    Запись метаданных и QC отчетов.
    """

    def __init__(
        self,
        quality_reporter: QualityReportABC | None = None,
        *,
        min_coverage: float = 0.85,
    ) -> None:
        self._quality_reporter = quality_reporter or QualityReportImpl()
        self._min_coverage = min_coverage
        self._atomic_op = AtomicFileOperation()

    def write_meta(self, meta: dict, path: Path) -> None:
        """Persist run metadata as YAML with stable key ordering."""

        def _write(temp_path: Path) -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(temp_path, "w", encoding="utf-8") as f:
                yaml.dump(meta, f, sort_keys=True)

        self._atomic_op.write_atomic(path, _write)

    def write_qc_report(
        self, df: pd.DataFrame, path: Path, *, min_coverage: float | None = None
    ) -> None:
        """Generate and store QC report CSV with optional coverage override."""
        path.parent.mkdir(parents=True, exist_ok=True)
        report = build_quality_report_table(
            df,
            min_coverage=(
                min_coverage if min_coverage is not None else self._min_coverage
            ),
            quality_reporter=self._quality_reporter,
        )
        report.to_csv(path, index=False)

    def build_checksums(self, paths: list[Path]) -> dict[str, str]:
        """Calculate SHA256 checksums for a list of artifact paths."""
        return compute_files_sha256(paths)
