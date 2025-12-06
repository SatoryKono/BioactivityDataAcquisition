from pathlib import Path
import pandas as pd
import yaml

from bioetl.infrastructure.output.contracts import MetadataWriterABC
from bioetl.infrastructure.files.checksum import compute_files_sha256


class MetadataWriterImpl(MetadataWriterABC):
    """
    Запись метаданных и QC отчетов.
    """

    def write_meta(self, meta: dict, path: Path) -> None:
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(meta, f, sort_keys=True)

    def write_qc_report(self, df: pd.DataFrame, path: Path) -> None:
        # Simple QC report: count nulls, unique values
        report = pd.DataFrame({
            "column": df.columns,
            "null_count": df.isnull().sum().values,
            "unique_count": df.nunique().values,
            "dtype": df.dtypes.values.astype(str)
        })
        report.to_csv(path, index=False)

    def generate_checksums(self, paths: list[Path]) -> dict[str, str]:
        return compute_files_sha256(paths)

