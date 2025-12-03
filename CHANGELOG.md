# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Changed
- Добавлены типизированные поля `input_mode`/`input_path`/`csv_options` для пайплайнов; `cli.input_file` автоматически мигрирует с предупреждением.
- ChEMBL pipeline теперь выбирает источник записей явно (API/CSV/id-only) без колонковой эвристики; CLI умеет переопределять режим и CSV-опции.

### Removed
- Удалена заглушка `assay_enrichment` из `ChemblSourceConfig`.
- Помечены deprecated несуществующие клиенты (PubChem, PubMed, Crossref, UniProt, SemanticScholar) в документации.

### Breaking Changes
- Поле `assay_enrichment` удалено из конфигурации. Если использовалось в YAML-конфигах — удалить.

