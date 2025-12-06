# Project Map

Навигатор по проекту: соответствие документации, кода и конфигураций.

## Основные разделы

| Раздел | Docs | Source | Configs |
| :--- | :--- | :--- | :--- |
| **Pipelines** | `docs/application/pipelines/` | `src/bioetl/application/pipelines/` | `configs/pipelines/` |
| **Architecture** | `docs/architecture/` | N/A (концепции) | N/A |
| **Domain Schemas** | `docs/domain/schemas/` | `src/bioetl/domain/schemas/` | N/A |
| **Clients** | `docs/infrastructure/clients/` | `src/bioetl/infrastructure/clients/` | `configs/profiles/` (частично) |
| **CLI** | `docs/interfaces/cli/` | `src/bioetl/interfaces/cli/` | N/A |

## Ключевые файлы

- **Entry Point**: `src/bioetl/__main__.py`
- **Pipeline Base**: `src/bioetl/application/pipelines/base.py`
- **Validation Service**: `src/bioetl/domain/validation/service.py`
- **Unified Logger**: `src/bioetl/infrastructure/logging/impl/unified_logger.py`

## Легенда

- `docs/`: Спецификации и руководства.
- `src/`: Реализация (Physical Architecture).
- `configs/`: Параметры выполнения.
