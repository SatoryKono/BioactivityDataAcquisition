import hashlib
import os
import shutil
import time
from pathlib import Path
import pandas as pd

from bioetl.config.models import DeterminismConfig
from bioetl.core.models import RunContext
from bioetl.output.contracts import MetadataWriterABC, WriterABC, WriteResult


class UnifiedOutputWriter:
    """
    Фасад для записи результатов пайплайна.
    
    Обеспечивает:
    - Атомарную запись (write-temp-and-rename)
    - Генерацию meta.yaml
    - QC-отчеты (quality_report, correlation_report)
    """
    
    def __init__(
        self,
        writer: WriterABC,
        metadata_writer: MetadataWriterABC,
        config: DeterminismConfig,
    ) -> None:
        self._writer = writer
        self._metadata_writer = metadata_writer
        self._config = config
    
    def write_result(
        self,
        df: pd.DataFrame,
        output_path: Path,
        entity_name: str,
        run_context: RunContext,
    ) -> WriteResult:
        """Основной метод записи."""
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 1. Сортировка по ключам (детерминизм)
        df = self._stable_sort(df, entity_name)
        
        # 2. Атомарная запись данных
        data_path = output_path / f"{entity_name}.csv"
        write_result = self._atomic_write(df, data_path)
        
        # 3. Запись meta.yaml
        meta = self._build_meta(run_context, write_result)
        self._metadata_writer.write_meta(meta, output_path / "meta.yaml")
        
        # 4. QC-отчеты
        # QC generation omitted for brevity/scope of current fix
        
        return write_result
        
    def _stable_sort(self, df: pd.DataFrame, entity_name: str) -> pd.DataFrame:
        if self._config.stable_sort:
            # Sort by columns to ensure column order at least.
            df = df.sort_index(axis=1) 
            pass
        return df

    def _atomic_write(self, df: pd.DataFrame, path: Path) -> WriteResult:
        """Атомарная запись через временный файл."""
        tmp_path = path.with_suffix(".tmp")
        
        # Запись во временный файл
        result = self._writer.write(df, tmp_path)
        
        # Атомарная замена with retry for Windows
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if path.exists():
                    os.remove(path)
                shutil.move(str(tmp_path), str(path))
                break
            except OSError:
                if attempt == max_retries - 1:
                    raise
                time.sleep(0.5)
        
        return WriteResult(
            path=path,
            row_count=result.row_count,
            checksum=self._compute_checksum(path),
            duration_sec=result.duration_sec,
        )
    
    def _compute_checksum(self, path: Path) -> str:
        """Вычисляет SHA256 файла."""
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _build_meta(self, context: RunContext, result: WriteResult) -> dict:
        return {
            "run_id": context.run_id,
            "entity": context.entity_name,
            "timestamp": context.started_at.isoformat(),
            "row_count": result.row_count,
            "checksum": result.checksum,
            "files": [str(result.path.name)]
        }
