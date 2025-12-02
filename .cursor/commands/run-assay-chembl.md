# /run-assay-chembl

**Goal:** Запустить пайплайн извлечения метаданных assay из ChEMBL API и нормализации данных по схеме проекта.

**Inputs**

- `--output-dir PATH` (обязательно): Директория для сохранения артефактов пайплайна
- `--config PATH` (опционально): Путь к конфигурационному файлу (по умолчанию: `configs/pipelines/assay/assay_chembl.yaml`)
- `--dry-run` (опционально): Загрузить и валидировать конфигурацию без выполнения пайплайна
- `--verbose` (опционально): Включить подробное логирование (DEBUG уровень)
- `--limit N` (опционально): Обработать максимум N строк (для smoke-тестов)
- `--sample N` (опционально): Случайная выборка N строк с детерминированным seed
- `--extended` (опционально): Включить расширенные QC артефакты и метрики
- `--set KEY=VALUE` (опционально): Переопределить отдельные ключи конфигурации (повторяемый)
- `--input-file PATH` (опционально): Путь к входному файлу (CSV/Parquet) с ID для batch-извлечения
- `--golden PATH` (опционально): Путь к golden dataset для проверки битовой детерминированности

**Steps**

1) Проверить наличие конфигурационного файла `configs/pipelines/assay/assay_chembl.yaml`
2) Создать выходную директорию, если она не существует
3) Запустить команду CLI: `python -m bioetl.cli.app assay_chembl --config configs/pipelines/assay/assay_chembl.yaml --output-dir <output-dir> [OPTIONS]`
4) Дождаться завершения пайплайна и проверить код возврата
5) Проверить наличие выходных файлов и `meta.yaml` в выходной директории

**Constraints**

- Обязательные параметры: `--config` и `--output-dir`
- Пайплайн должен соответствовать детерминизму: стабильная сортировка по `assay_id`, канонические значения, SHA256 хеши
- Все выходные данные валидируются через Pandera схемы перед записью
- Логирование только через UnifiedLogger (структурированный JSON)

**Outputs**

- Таблица assay в формате Parquet/CSV в `data/output/assay/`
- Файл `meta.yaml` с метаданными пайплайна (версия, git commit, checksums, row_count)
- QC отчеты: `quality_report_table.csv`, `correlation_report_table.csv`
- Логи в `data/logs/` (структурированный JSON)

**References**

- Конфигурация: `configs/pipelines/assay/assay_chembl.yaml`
- Документация: `docs/pipelines/assay-chembl/`
- CLI справка: `docs/cli/01-cli-commands.md`

