# 02 Etl Layers

## Orchestration
Ответственность: управление жизненным циклом запуска (prepare_run/finalize_run), выбор профилей конфигураций, планирование пайплайнов.
Ключевые ABC: PipelineHookABC, ErrorPolicyABC.
Взаимодействие: вызывает Client/Transform/Validation/Output стадии, передаёт run_id и контекст.
Примеры: базовые хуки для dry-run, сбор метрик, переопределяемые политики ошибок.

## Monitoring
Ответственность: логирование, метрики, прогресс и трассировка.
Ключевые ABC: UnifiedLogger, LoggerAdapterABC, ProgressReporterABC, TracerABC.
Взаимодействие: интегрируется в PipelineBase и клиенты, записывает события и метрики стадий.
Примеры: структурированное логирование с контекстом pipeline_name/run_id, прогресс выгрузки страниц из API.

## Client
Ответственность: получение данных из внешних API через унифицированные контракты.
Ключевые ABC: UnifiedAPIClient, BaseClient, RequestBuilder/Parser/Paginator ABC из infrastructure/clients.
Взаимодействие: Orchestration передает конфиг, Client возвращает поток записей для Transform.
Примеры: ChemblClient с ChemblRequestBuilder, ChemblResponseParser, TokenBucketRateLimiter.

## Transform
Ответственность: нормализация и подготовка данных к валидации (очистка, маппинг, вычисление хешей).
Ключевые ABC: TransformerABC, NormalizerABC, DescriptorFactory.
Взаимодействие: получает сырые записи от Client, выдаёт таблицу с детерминированным порядком колонок.
Примеры: ActivityTransformer, ChemblDescriptorFactory, TestitemNormalizer.

## Validation
Ответственность: проверка данных по Pandera-схемам и политикам ошибок.
Ключевые ABC: ValidationService, ValidatorABC, SchemaRegistry, ErrorPolicyABC.
Взаимодействие: получает таблицу из Transform, применяет схемы, формирует ValidationResult.
Примеры: валидация колонок по SchemaRegistry, сбор QC-отчётов, fallback-политика пропуска строк.

## Output
Ответственность: атомарная запись таблиц, метаданных и QC-отчётов.
Ключевые ABC: UnifiedOutputWriter, WriterABC, MetadataWriterABC.
Взаимодействие: принимает валидированные таблицы и контекст запуска, пишет в `tables/`, `qc/`, `meta.yaml`, `checksums/`.
Примеры: запись CSV/Parquet с фиксированным порядком колонок, генерация checksum-файлов.

## Физическая структура
См. [05 Physical Layout](05-physical-layout.md) для маппинга этих слоев на директории проекта.