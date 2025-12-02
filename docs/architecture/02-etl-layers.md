# 02 Etl Layers

## Orchestration
Ответственность: управление жизненным циклом запуска (`run` метод в `PipelineBase`), инициализация контейнера зависимостей (`build_pipeline_dependencies`), выбор профилей конфигураций.
Ключевые компоненты: `PipelineBase`, `ConfigResolver`.
Взаимодействие: Связывает сервисы (Extraction, Validation, Output) в единый поток выполнения.

## Monitoring
Ответственность: логирование, метрики, прогресс.
Ключевые компоненты: `UnifiedLogger`, `LoggerAdapterABC`.
Взаимодействие: Пронизывает все слои; контекстный логгер передается в каждый сервис при инициализации.

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
Ключевые компоненты: `ValidationService`, `SchemaRegistry`, Pandera Models (например, `ActivitySchema`).
Взаимодействие: Получает DataFrame после трансформации, возвращает валидированный DataFrame и `ValidationResult`. Блокирует запись некорректных данных.

## Output (Infrastructure)
Ответственность: атомарная запись таблиц, метаданных и QC-отчётов.
Ключевые компоненты: `UnifiedOutputWriter`.
Взаимодействие: Принимает валидированные данные, пишет файлы с учетом настроек детерминизма (сортировка колонок/строк), создает `meta.yaml` и checksums.

## Физическая структура
См. [05 Physical Layout](05-physical-layout.md) для маппинга этих слоев на директории проекта.
