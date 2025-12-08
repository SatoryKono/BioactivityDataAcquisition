# ETL Layers

## Orchestration
Ответственность: управление жизненным циклом запуска (`run` метод в `PipelineBase`), инициализация контейнера зависимостей (`build_pipeline_dependencies`), выбор профилей конфигураций.
Ключевые компоненты: `PipelineBase`, `ConfigResolver`.
Взаимодействие: Связывает сервисы (Extraction, Validation, Output) в единый поток выполнения.

## Monitoring
Ответственность: логирование, метрики, прогресс.
Ключевые компоненты: `UnifiedLogger`, доменный порт `LoggingPortABC`, порт метрик
`PipelineMetricsPortABC`, а также конфигурация наблюдаемости
(`LoggingConfig`, `MetricsConfig`, `ObservabilityConfig`) внутри `PipelineConfig`.
Взаимодействие: Пронизывает все слои; контекстный логгер и метрики передаются в
каждый сервис при инициализации. Домен описывает **что** нужно логировать и
какие параметры мониторинга заданы в конфигурации пайплайна, а конкретные
реализации логгера и экспорта метрик находятся в инфраструктурном слое и
выбираются через DI/wiring.

## Client (Infrastructure)
Ответственность: получение данных из внешних API.
Реализует трёхслойный паттерн:
1. **Contracts**: Протоколы и ABC (`src/bioetl/infrastructure/clients/<domain>/contracts.py`).
2. **Factories**: Фабричные функции для создания клиентов (`default_<domain>_client`).
3. **Implementation**: Конкретные реализации (`impl/http_client.py`), скрывающие детали HTTP (retry, rate limit, pagination).
Примеры: `ChemblClient`, `ChemblPaginator`.

## Extraction (Application)
Ответственность: Прикладная логика извлечения данных.
Ключевые компоненты: `ExtractionService` (например, `ChemblExtractionService`).
Взаимодействие: Использует инфраструктурный Client для выполнения запросов, управляет стратегиями выборки (все записи, по фильтру, по списку ID).

## Transform (Domain/Application)
Ответственность: нормализация и подготовка данных к валидации.
Ключевые компоненты: 
- Методы `transform` / `_do_transform` в пайплайнах.
- `NormalizerMixin`: стандартизация типов (str, int, float), очистка (trim, null handling).
- `HashService`: вычисление детерминированных хешей (`hash_row`, `hash_business_key`).

## Validation (Domain)
Ответственность: проверка данных по Pandera-схемам.
Ключевые компоненты: `ValidationService`, `SchemaRegistry`, Pandera Models
(например, `ActivityTableSchema`, `AssayTableSchema`, `MoleculeTableSchema`,
`TargetTableSchema`, `DocumentTableSchema` в `bioetl.domain.schemas.chembl.*`).
Взаимодействие: Получает DataFrame после трансформации, возвращает валидированный
DataFrame и `ValidationResult`. Блокирует запись некорректных данных.

## Bounded Contexts (ChEMBL)

ChEMBL-данные разделены на несколько предметных контекстов, каждый из которых
имеет собственные таблицы, схемы и правила валидации:

- Activity: `ActivityTableSchema` в `bioetl.domain.schemas.chembl.activity`.
- Assay: `AssayTableSchema` в `bioetl.domain.schemas.chembl.assay`.
- Molecule: `MoleculeTableSchema` в `bioetl.domain.schemas.chembl.molecule`.
- Target: `TargetTableSchema` в `bioetl.domain.schemas.chembl.target`.
- Document: `DocumentTableSchema` в `bioetl.domain.schemas.chembl.document`.

Каждый bounded context может эволюционировать независимо (добавление полей,
ограничений, специфической логики), при этом общий каркас валидации (`ValidationService`,
`SchemaRegistry`) остаётся общим для всего доменного слоя.

## Output (Infrastructure)
Ответственность: атомарная запись таблиц, метаданных и QC-отчётов.
Ключевые компоненты: `UnifiedOutputWriter`.
Взаимодействие: Принимает валидированные данные, пишет файлы с учетом настроек детерминизма (сортировка колонок/строк), создает `meta.yaml` и checksums.

## Физическая структура
См. [05 Physical Layout](05-physical-layout.md) для маппинга этих слоев на директории проекта.
