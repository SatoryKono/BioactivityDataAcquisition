# /run-target-chembl

## Goal

Запустить пайплайн извлечения записей target из ChEMBL API, обогащения данными UniProt и IUPHAR, и нормализации по схеме проекта.

## Inputs

- `--output-dir PATH` (обязательно): Директория для сохранения артефактов пайплайна
- `--config PATH` (опционально): Путь к конфигурационному файлу (по умолчанию: `configs/pipelines/target/target_chembl.yaml`)
- `--dry-run` (опционально): Загрузить и валидировать конфигурацию без выполнения пайплайна
- `--verbose` (опционально): Включить подробное логирование (DEBUG уровень)
- `--limit N` (опционально): Обработать максимум N строк (для smoke-тестов)
- `--sample N` (опционально): Случайная выборка N строк с детерминированным seed
- `--extended` (опционально): Включить расширенные QC артефакты и метрики
- `--set KEY=VALUE` (опционально): Переопределить отдельные ключи конфигурации (повторяемый, например для включения/отключения enrichment сервисов)
- `--input-file PATH` (опционально): Путь к входному файлу (CSV/Parquet) с ID для batch-извлечения
- `--golden PATH` (опционально): Путь к golden dataset для проверки битовой детерминированности

## Steps

1) Проверить наличие конфигурационного файла `configs/pipelines/target/target_chembl.yaml`
2) Создать выходную директорию, если она не существует
3) Запустить команду CLI: `python -m bioetl.cli.app target --config configs/pipelines/target/target_chembl.yaml --output-dir data/output/target --limit 10`
4) Дождаться завершения пайплайна и проверить код возврата
5) Проверить наличие выходных файлов и `meta.yaml` в выходной директории

## Constraints

- Обязательные параметры: `--config` и `--output-dir`
- Пайплайн должен соответствовать детерминизму: стабильная сортировка по `target_id`, канонические значения, SHA256 хеши
- Все выходные данные валидируются через Pandera схемы перед записью
- Логирование только через UnifiedLogger (структурированный JSON)
- Enrichment адаптеры должны использовать UnifiedAPIClient с retry/backoff и rate limiting

## Outputs

- Таблица targets в формате Parquet/CSV в `data/output/target/`
- Файл `meta.yaml` с метаданными пайплайна (версия, git commit, checksums, row_count)
- QC отчеты: `quality_report_table.csv`, `correlation_report_table.csv`
- Логи в `data/logs/` (структурированный JSON)

## References

- Конфигурация: `configs/pipelines/target/target_chembl.yaml`
- Документация: `docs/pipelines/target-chembl/`, `docs/pipelines/target-uniprot/`, `docs/pipelines/target-iuphar/`
- CLI справка: `docs/cli/01-cli-commands.md`

