# UnifiedOutputWriter

**Модуль:** `src/bioetl/output/unified_writer.py`

Координирует процесс записи результатов пайплайна, обеспечивая целостность, атомарность и генерацию сопутствующих артефактов.

## Функциональность

### 1. Атомарная запись
Реализует паттерн `write-temp-and-rename`.
1. Данные пишутся во временный файл `.tmp`.
2. После успешной записи выполняется `os.replace()` на целевое имя.
Это гарантирует, что потребители данных никогда не увидят частично записанный файл.

### 2. Метаданные (meta.yaml)
Генерирует файл метаданных, содержащий:
- `pipeline_version`: Версия кода.
- `chembl_release`: Версия данных источника.
- `run_id`: Уникальный ID запуска.
- `timestamp_utc`: Время завершения.
- `row_count`: Количество строк.
- `checksums`: SHA256 хеши записанных файлов.

### 3. Отчеты качества (QC)
Если включено в конфиге, генерирует CSV-файлы:
- `quality_report_table.csv`: Статистика по колонкам (NULLs, unique, min/max).
- `correlation_report_table.csv`: Корреляционная матрица для числовых полей.

## Интерфейс

```python
class UnifiedOutputWriter:
    def write_result(
        self,
        df: pd.DataFrame,
        output_path: Path,
        entity_name: str,
        run_context: RunContext
    ) -> WriteResult:
        """
        Основной метод записи.
        """
```

## Конфигурация

```yaml
determinism:
  atomic_writes: true
  validate_checksums: true

qc:
  enable_quality_report: true
  enable_correlation_report: true
```

