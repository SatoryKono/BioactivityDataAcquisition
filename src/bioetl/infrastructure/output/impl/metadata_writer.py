from pathlib import Path

import pandas as pd
import yaml

from bioetl.infrastructure.files.checksum import compute_files_sha256
from bioetl.domain.clients.base.output.contracts import (
    MetadataWriterABC,
    QualityReportABC,
)
from bioetl.infrastructure.output.impl.quality_report import QualityReportImpl


def build_quality_report_table(
    df: pd.DataFrame,
    *,
    min_coverage: float,
    quality_reporter: QualityReportABC | None = None,
) -> pd.DataFrame:
    reporter = quality_reporter or QualityReportImpl()
    return reporter.build_quality_report(df, min_coverage=min_coverage)


class MetadataWriterImpl(MetadataWriterABC):
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

    def write_meta(self, meta: dict, path: Path) -> None:
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(meta, f, sort_keys=True)

    def write_qc_report(
        self, df: pd.DataFrame, path: Path, *, min_coverage: float | None = None
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        report = build_quality_report_table(
            df,
            min_coverage=(
                min_coverage if min_coverage is not None else self._min_coverage
            ),
            quality_reporter=self._quality_reporter,
        )
        report.to_csv(path, index=False)

    def generate_checksums(self, paths: list[Path]) -> dict[str, str]:
        return compute_files_sha256(paths)
