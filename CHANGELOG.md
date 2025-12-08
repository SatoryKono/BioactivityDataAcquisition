# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Changed

- Добавлены типизированные поля `input_mode`/`input_path`/`csv_options` для пайплайнов; `cli.input_file` автоматически мигрирует с предупреждением.
- ChEMBL pipeline теперь выбирает источник записей явно (API/CSV/id-only) без колонковой эвристики; CLI умеет переопределять режим и CSV-опции.
- `HashService` больше не содержит собственной реализации `Hasher`: доменный фасад требует инжектируемый `HasherABC`, а фабрика по умолчанию использует `HasherImpl`.
- Документация и диаграммы ChEMBL переименованы (`TestItem` → `Molecule`), добавлены stub-схемы `CellTableSchema`/`TissueTableSchema`.

### Removed

- Удалена заглушка `assay_enrichment` из `ChemblSourceConfig`.
- Помечены deprecated несуществующие клиенты (PubChem, PubMed, Crossref, UniProt, SemanticScholar) в документации.
- Удалены устаревшие интерфейсы (`default_provider_registry()`, `bioetl.application.services.chembl_extraction`) и middleware-шимы.
- Удалены `src/bioetl/infrastructure/transform/impl/hash_service_impl.py`, `src/bioetl/domain/clients/base/logging/`, `src/bioetl/domain/configs/base.py`, `src/bioetl/domain/contracts.py`.

### Breaking Changes

- Поле `assay_enrichment` удалено из конфигурации. Если использовалось в YAML-конфигах — удалить.
- Флаг `features.enable_provider_loader_port` больше не поддерживается: порт загрузчика провайдеров активен всегда, а CLI/REST/MQ требуют валидного `providers.yaml` или явного `ProviderRegistry`.
- `HashService` больше нельзя инстанцировать без `HasherABC`; проекты должны создавать сервис через `bioetl.infrastructure.transform.factories.default_hash_service()` или явно передавать `Hasher`.
- `ProgressReporterABC` теперь экспортируется из `bioetl.domain.observability` (shim `domain.clients.base.logging` удалён).
- `domain.configs.base` (re-export) и `domain.contracts` больше не доступны; импортируйте `PipelineConfig` и extraction-порты напрямую.
