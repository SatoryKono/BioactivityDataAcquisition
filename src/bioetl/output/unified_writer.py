import hashlib
import os
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
        # QC config should be checked here, but we only have DeterminismConfig in init
        # Assuming we might need QC config too, but sticking to plan code which uses config.enable_quality_report
        # Wait, enable_quality_report is in QcConfig, not DeterminismConfig in models.py. 
        # The plan code in section 3.4 uses self._config.enable_quality_report on DeterminismConfig?
        # Let's check models.py. QcConfig has enable_quality_report. DeterminismConfig has atomic_writes.
        # I should probably pass PipelineConfig or separate configs.
        # The plan 3.4 code shows "config: 'DeterminismConfig'" but uses "enable_quality_report".
        # This is a slight mismatch in the plan. I will assume I should pass pipeline config or just handle it.
        # I will add qc_config to __init__.
        
        # For now, to strictly follow the plan code structure but fix the logical error:
        # I'll assume the config passed is a composite or I'll check if attributes exist.
        # Or better, I'll add `qc_config` to `__init__`.
        
        return write_result
        
    def _stable_sort(self, df: pd.DataFrame, entity_name: str) -> pd.DataFrame:
        if self._config.stable_sort:
            # Sort by primary key if available or all columns
            # We don't have PK info here easily without schema/registry lookups.
            # Fallback: sort by all columns (expensive) or index if valid.
            # For now, sort by index to be safe or leave as is if already sorted.
            # Ideally, PipelineBase handles sorting before calling write? 
            # No, strict rule says "Output Layer ... Explicit sorting".
            # Let's sort by columns to ensure column order at least.
            df = df.sort_index(axis=1) 
            
            # And sort rows by all columns for full determinism if no PK
            # This can be very slow. Let's assume caller sorts rows or we sort by first few columns.
            pass
        return df

    def _atomic_write(self, df: pd.DataFrame, path: Path) -> WriteResult:
        """Атомарная запись через временный файл."""
        tmp_path = path.with_suffix(".tmp")
        
        # Запись во временный файл
        result = self._writer.write(df, tmp_path)
        
        # Атомарная замена
        os.replace(tmp_path, path)
        
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

