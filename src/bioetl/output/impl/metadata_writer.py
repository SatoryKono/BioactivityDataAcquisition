import hashlib
from pathlib import Path
import pandas as pd
import yaml

from bioetl.output.contracts import MetadataWriterABC


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
        checksums = {}
        for path in paths:
            if not path.exists():
                continue
            sha256 = hashlib.sha256()
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    sha256.update(chunk)
            checksums[path.name] = sha256.hexdigest()
        return checksums

