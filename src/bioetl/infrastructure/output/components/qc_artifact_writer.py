"""QC artifact writer component implementation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from bioetl.infrastructure.files.atomic import AtomicFileOperation


class QcArtifactWriter:
    """Writer for QC artifacts (CSV reports).

    This component handles atomic CSV writing for QC reports
    without knowledge of QC report generation logic.
    """

    def __init__(
        self,
        atomic_op: AtomicFileOperation | None = None,
    ) -> None:
        """Initialize writer.

        Args:
            atomic_op: Atomic file operation handler.
        """
        self._atomic_op = atomic_op or AtomicFileOperation()

    def write_qc_csv(self, df: pd.DataFrame, path: Path) -> Path:
        """Write QC DataFrame to CSV atomically.

        Args:
            df: QC report DataFrame.
            path: Target file path.

        Returns:
            Path to written file.
        """

        def _write_wrapper(temp_path: Path) -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(temp_path, index=False)

        self._atomic_op.write_atomic(path, _write_wrapper)
        return path


__all__ = ["QcArtifactWriter"]
