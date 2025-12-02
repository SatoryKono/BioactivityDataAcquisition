# 05 Physical Layout

## Соответствие слоев и структуры кода

В этом документе описано отображение логических слоев архитектуры (см. [02 ETL Layers](02-etl-layers.md)) на физическую структуру директорий в `src/`.

### Таблица маппинга

| Логический слой (Docs) | Папка (Source) | Ответственность |
| :--- | :--- | :--- |
| **Domain** | `src/bioetl/domain/` | Ядро бизнес-логики: схемы Pandera, Enums, инварианты (хеширование). |
| **Orchestration** | `src/bioetl/application/` | Сборка пайплайнов, управление зависимостями и шагами выполнения. |
| **Client** | `src/bioetl/infrastructure/clients/` | Адаптеры к внешним API (ChEMBL), ретраи, пагинация. |
| **Monitoring** | `src/bioetl/infrastructure/logging/` | Логирование, метрики и трейсинг (UnifiedLogger). |
| **Configuration** | `src/bioetl/infrastructure/config/` | Загрузка и валидация YAML-конфигураций. |
| **Output** | `src/bioetl/infrastructure/output/` | Писатели файлов (CSV, Parquet) и метаданных. |
| **Interfaces** | `src/bioetl/interfaces/` | Точки входа: CLI команды, API хендлеры. |

### Детали структуры

#### Domain Layer (`src/bioetl/domain/`)

Здесь находятся определения данных, независимые от внешней инфраструктуры.

- `schemas/`: Pandera-схемы для валидации.
- `models/`: Pydantic-модели для внутреннего представления.
- `services/`: Чистые функции доменной логики (например, расчет `hash_business_key`).

#### Application Layer (`src/bioetl/application/`)

Слой сценариев использования (Use Cases).

- `pipelines/`: Конкретные реализации пайплайнов (например, `ChemblActivityPipeline`).
- `services/`: Сервисы приложения, оркестрирующие доменные и инфраструктурные компоненты (например, `ValidationService`).

#### Infrastructure Layer (`src/bioetl/infrastructure/`)

Реализация взаимодействия с внешним миром (Adapters).

- `clients/`: HTTP-клиенты.
- `output/`: Файловый ввод-вывод.
- `logging/`: Инфраструктура наблюдения.

#### Interfaces Layer (`src/bioetl/interfaces/`)

Порты для запуска приложения.

- `cli/`: Реализация командной строки на базе Typer.
