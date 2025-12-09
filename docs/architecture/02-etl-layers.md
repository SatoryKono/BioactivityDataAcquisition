# ETL Layers

## Orchestration
Ответственность: управление жизненным циклом запуска (`run` метод в `PipelineBase`), инициализация контейнера зависимостей (через `bioetl.interfaces.container_factory`), выбор профилей конфигураций.
Ключевые компоненты: `PipelineBase`, `ConfigResolver`, `PipelineContainer`.
Взаимодействие: Связывает сервисы (Extraction, Validation, Output) в единый поток выполнения.

## Monitoring
Ответственность: логирование, метрики, прогресс.
Ключевые компоненты: доменные порты `LoggingPortABC`, `PipelineMetricsPortABC`, `MetricsPortABC` (для клиентов),
адаптеры инфраструктурного логгера (например, `UnifiedLogger`) и экспорта
метрик (Prometheus), а также секция `observability` в `PipelineConfig`.
Взаимодействие: Пронизывает все слои; контекстный логгер и метрики передаются в
каждый сервис при инициализации. Домен описывает **что** и **где** нужно
логировать, но не знает форматов конфигурации, backends и протоколов экспорта —
это ответственность инфраструктуры и wiring/DI.

## Client (Infrastructure)
Ответственность: получение данных из внешних API.
Реализует трёхслойный паттерн:
1. **Contracts**: Протоколы и ABC (`src/bioetl/domain/clients/base/contracts.py`).
2. **Factories**: Фабричные функции для создания клиентов (`src/bioetl/infrastructure/clients/base/factories.py`).
3. **Implementation**: Конкретные реализации (`UnifiedAPIClientImpl`), скрывающие детали HTTP (retry, rate limit, metrics, logging).
Примеры: `ChemblHttpClientImpl` (использует UnifiedAPIClient).

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
`TargetTableSchema`, `PublicationTableSchema` в `bioetl.domain.schemas.chembl.*`).
Взаимодействие: Получает DataFrame после трансформации, возвращает валидированный
DataFrame и `ValidationResult`. Блокирует запись некорректных данных.

## Bounded Contexts (ChEMBL)

ChEMBL-данные разделены на несколько предметных контекстов, каждый из которых
имеет собственные таблицы, схемы и правила валидации:

- Activity: `ActivityTableSchema` в `bioetl.domain.schemas.chembl.activity`.
- Assay: `AssayTableSchema` в `bioetl.domain.schemas.chembl.assay`.
- Molecule: `MoleculeTableSchema` в `bioetl.domain.schemas.chembl.molecule`.
- Target: `TargetTableSchema` в `bioetl.domain.schemas.chembl.target`.
- Publication: `PublicationTableSchema` в `bioetl.domain.schemas.chembl.publication`.

Каждый bounded context может эволюционировать независимо (добавление полей,
ограничений, специфической логики), при этом общий каркас валидации (`ValidationService`,
`SchemaRegistry`) остаётся общим для всего доменного слоя.

## Output (Infrastructure)
Ответственность: атомарная запись таблиц, метаданных и QC-отчётов.
Ключевые компоненты: `UnifiedOutputWriter`.
Взаимодействие: Принимает валидированные данные, пишет файлы с учетом настроек детерминизма (сортировка колонок/строк), создает `meta.yaml` и checksums.

## Cross-cutting Concerns
Логирование, метрики и конфигурация HTTP-клиентов относятся к инфраструктурному
слою и считаются сквозными (cross-cutting) аспектами. Доменный слой зависит
только от портов (`LoggingPortABC`, `PipelineMetricsPortABC`, клиентские ABC) и
не знает:
- где и как хранятся настройки (YAML, ENV, CLI);
- какие конкретные реализации логгера/метрик используются;
- какие HTTP-библиотеки и параметры ретраев применяются.
Эти детали инкапсулированы в `bioetl.infrastructure.*` и настраиваются через
DI/wiring.

## Физическая структура
См. [05 Physical Layout](05-physical-layout.md) для маппинга этих слоев на директории проекта.
