# /run-document-chembl

## Goal

Запустить пайплайн извлечения документов из ChEMBL API и опционального обогащения метаданными из PubMed, Crossref, OpenAlex и Semantic Scholar в зависимости от режима выполнения.

## Inputs

- `--output-dir PATH` (обязательно): Директория для сохранения артефактов пайплайна
- `--config PATH` (опционально): Путь к конфигурационному файлу (по умолчанию: `configs/pipelines/document/document_chembl.yaml`)
- `--mode NAME` (опционально): Выбрать предопределенный режим выполнения (например, `chembl` для только ChEMBL или `all` для полного обогащения)
- `--dry-run` (опционально): Загрузить и валидировать конфигурацию без выполнения пайплайна
- `--verbose` (опционально): Включить подробное логирование (DEBUG уровень)
- `--limit N` (опционально): Обработать максимум N строк (для smoke-тестов)
- `--sample N` (опционально): Случайная выборка N строк с детерминированным seed
- `--extended` (опционально): Включить расширенные QC артефакты и метрики
- `--set KEY=VALUE` (опционально): Переопределить отдельные ключи конфигурации (повторяемый)
- `--input-file PATH` (опционально): Путь к входному файлу (CSV/Parquet) с ID для batch-извлечения
- `--golden PATH` (опционально): Путь к golden dataset для проверки битовой детерминированности

## Steps

1) Проверить наличие конфигурационного файла `configs/pipelines/document/document_chembl.yaml`
2) Создать выходную директорию, если она не существует
3) Запустить команду CLI: `python -m bioetl.cli.app document_chembl --config configs/pipelines/document/document_chembl.yaml --output-dir data/output/document --limit 10 [OPTIONS]`
4) Дождаться завершения пайплайна и проверить код возврата
5) Проверить наличие выходных файлов и `meta.yaml` в выходной директории

## Constraints

- Обязательные параметры: `--config` и `--output-dir`
- Пайплайн должен соответствовать детерминизму: стабильная сортировка по `year` и `document_id`, канонические значения, SHA256 хеши
- Все выходные данные валидируются через Pandera схемы перед записью
- Логирование только через UnifiedLogger (структурированный JSON)
- Enrichment адаптеры должны использовать UnifiedAPIClient с retry/backoff, rate limiting и circuit breaker
- Настройки адаптеров обеспечивают канонический порядок источников при сохранении детерминизма

## Outputs

- Таблица документов в формате Parquet/CSV в `data/output/document/`
- Файл `meta.yaml` с метаданными пайплайна (версия, git commit, checksums, row_count)
- QC отчеты: `quality_report_table.csv`, `correlation_report_table.csv`
- Логи в `data/logs/` (структурированный JSON)

## References

- Конфигурация: `configs/pipelines/document/document_chembl.yaml`
- Документация: `docs/pipelines/document-chembl/`, `docs/pipelines/document-pubmed/`, `docs/pipelines/document-crossref/`, `docs/pipelines/document-openalex/`, `docs/pipelines/document-semantic-scholar/`
- CLI справка: `docs/cli/01-cli-commands.md`

