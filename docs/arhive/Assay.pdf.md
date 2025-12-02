# Assay.pdf

```text
Объекты ETL-пайплайна ChEMBL/Assay
Класс/Объект Предок Модуль Назначение Публичные методы Приватные методы
ChemblAssayPipeline ChemblCommonPipelinesrc/bioetl/pipelines/chembl/
assay/run.pyОсновной класс
пайплайна для выгрузки
данных об ассаях из
ChEMBL . Реализует
этапы ETL для сущности
assay (использует схему
валидации AssaySchema
и переопределяет stage-
хуки для трансформации,
валидации и сохранения
данных).init(config: Mapping[str , Any], *, run_id: str
| None = None)<br>build_descriptor(self) ->
Any<br>pre_transform(self, df:
pd.DataFrame) -> pd.DataFrame
<br>validate(self, df: pd.DataFrame, options:
StageExecutionOptions) ->
pd.DataFrame<br>save_results(self, df:
pd.DataFrame, artifacts: WriteArtifacts,
options: StageExecutionOptions) ->
WriteResult_normalize_nested_parameters(self, df:
pd.DataFrame) ->
pd.DataFrame<br>_ensure_assay_class_mapping(self,
df: pd.DataFrame) ->
pd.DataFrame<br>_ensure_target_integrity(self, df:
pd.DataFrame) -> pd.DataFrame
ChemblCommonPipeline ChemblPipelineBasesrc/bioetl/pipelines/chembl/
common/base.pyБазовый класс для
ChEMBL-пайплайнов
(обобщённая логика без
legacy-зависимостей) .
Определяет стандартные
стадии ETL: извлечение
через стратегию,
трансформацию (вызов
pre_transform и
domain_enrich),
валидацию через
Schema, и план записи
результатов.init(config: Mapping[str , Any], *, run_id: str
| None = None,<br>  extraction_service:
ChemblExtractionService | None = None,
extraction_service_factory: Callable[[],
ChemblExtractionService] | None = None,
descriptor_factory:
ChemblDescriptorFactory | None =
None,<br>  client_registry:
ClientFactoryRegistry | None = None,
artifact_runtime_service_factory:
Callable[[Any], Any] | None =
None,<br>  custom_artifact_planner_factory:
Callable[[], ArtifactPlanner] | None = None,
schema_registry_factory: Callable[[],
SchemaRegistry] | None =
None,<br>  descriptor_type: str = "service",
extraction_strategy_factory:
ExtractionStrategyFactory | None = None)
<br>extract(self, descriptor:
ChemblExtractionServiceDescriptor |
ChemblExtractionDescriptor | None,
options: StageExecutionOptions) ->
pd.DataFrame <br>transform(self, df:
pd.DataFrame, options:
StageExecutionOptions) -> pd.DataFrame
<br>validate(self, df: pd.DataFrame,
options: StageExecutionOptions) ->
pd.DataFrame <br>build_descriptor(self)
-> ChemblExtractionServiceDescriptor |
ChemblExtractionDescriptor_create_descriptor_factory(self) ->
ChemblDescriptorFactory
<br>_validate_common_config(self) -> None
<br>_get_config_value(self, dotted_path: str) -> Any
<br>_write_quality_report(self, df: pd.DataFrame,
output_path: Path) -> None
<br>_fallback_rows(self, ids: Iterable[str], exc:
Exception) -> list[dict[str , Any]]
<br>_build_generic_descriptor(self) ->
ChemblExtractionServiceDescriptor[Any]
<br>_extract_with_dataclass_descriptor(self,
descriptor: ChemblExtractionDescriptor , options:
StageExecutionOptions) -> pd.DataFrame (должен
быть переопределён в подклассах при
использовании dataclass-дескрипторов)12
3
45
6
7
8910
1112
13
14
1516
1718
1920
1

Класс/Объект Предок Модуль Назначение Публичные методы Приватные методы
ChemblPipelineBase PipelineBasesrc/bioetl/core/pipeline/
unified.pyАбстрактный базовый
класс пайплайна для
ChEMBL, делегирующий
доменную логику сервису
извлечения .
Содержит реализацию
общих хуков:
pre_transform и
domain_enrich (по
умолчанию возвращают
исходный DataFrame), а
также интеграцию с
ChemblExtractionService
для запуска извлечения.init(config: Mapping[str , Any], , run_id: str |
None = None, extraction_service:
ChemblExtractionService | None = None,
extraction_service_factory: Callable[[],
ChemblExtractionService] | None = None, 
kwargs)<br>chembl_release
(property)<br>resolve_chembl_release(self,
chembl_client: Any) -> str
<br>get_release(self) -> str | None
<br>build_descriptor(self) -> Any (abstract;
реализуется в
наследниках)<br>pre_transform(self, df:
pd.DataFrame) -> pd.DataFrame
<br>domain_enrich(self, df: pd.DataFrame) ->
pd.DataFrame
<br>run_descriptor_extraction(self, descriptor:
ChemblExtractionServiceDescriptor, ids:
Sequence[str] | None, , summary_event: str ,
metadata_filters: Mapping[str , Any] | None
= None, fetch_mode: str = "default",
**batch_kwargs) -> tuple[pd.DataFrame,
BatchExtractionStats】_resolve_extraction_service(extraction_service:
ChemblExtractionService | None,
extraction_service_factory: Callable[[],
ChemblExtractionService] | None) ->
ChemblExtractionService
ChemblExtractionService objectsrc/bioetl/pipelines/chembl/
common/
chembl_extraction_service.pyСервис для выполнения
общего процесса
извлечения данных
ChEMBL . Отвечает за
определение текущего
релиза ChEMBL,
построение контекста
запроса, формирование
функций выборки
(fetcher) и финализации
данных, а также за
пакетное выполнение
извлечения через API
ChEMBL.chembl_release (свойство) -> str |
None<br>resolve_chembl_release(self,
chembl_client: BaseClient | Any) -> str
<br>build_context(self, descriptor: Any,
pipeline: Any, , metadata_filters: Mapping[str,
Any] | None = None, fetch_mode: str =
"default") -> dict[str, Any]
<br>finalize_dataframe(self, dataframe:
pd.DataFrame, finalizer: Any, stats:
BatchExtractionStats) -> tuple[pd.DataFrame,
BatchExtractionStats]
<br>run_descriptor_extraction(self, pipeline:
Any, descriptor: Any, ids: Sequence[str] | None,
, summary_event: str , metadata_filters:
Mapping[str , Any] | None = None,
fetch_mode: str = "default",
**batch_kwargs) -> tuple[pd.DataFrame,
BatchExtractionStats】_normalize_ids(self, ids: Sequence[str] | None,
context: Mapping[str , Any]) -> list[str] | None
<br>_resolve_page_size(self, context: Mapping[str ,
Any], default: int = 1000) -> int
<br>_resolve_client_settings(self, context:
Mapping[str , Any]) -> Mapping[str , Any]
<br>_build_client_fetcher(self, chembl_client:
BaseClient, , page_size: int, client_settings: Mapping[str,
Any] | None = None) -> Callable[[Sequence[str] | None],
Any] <br>_resolve_fetcher(self, descriptor: Any,
context: Mapping[str, Any], , page_size: int,
client_settings: Mapping[str , Any] | None = None) ->
Callable[[Sequence[str] | None], Any]2122
23
24
242526
2728
2930
31
323334
35
36
3738
3940
2

Класс/Объект Предок Модуль Назначение Публичные методы Приватные методы
ChemblExtractionServiceDescriptor Generic[ChemblPipelineBase]src/bioetl/core/pipeline/
unified.pyОписание (дескриптор)
извлечения сущности
ChEMBL через сервисный
подход . Содержит три
фабричные функции:
build_context (строит
контекст для выборки),
fetcher_factory
(возвращает функцию
для получения данных по
батчу ID) и
finalizer_factory
(возвращает функцию
для финальной
обработки DataFrame).init(*, build_context:
Callable[[ChemblPipelineBase], Mapping[str ,
Any]], fetcher_factory: Callable[[Mapping[str ,
Any]], Callable[[Sequence[str] | None],
Any]], finalizer_factory:
Callable[[Mapping[str , Any]],
Callable[[pd.DataFrame], pd.DataFrame]])–
ChemblExtractionDescriptor –src/bioetl/pipelines/chembl/
common/descriptor.pyЛёгкий dataclass-
дескриптор запроса к
ChEMBL . Описывает,
какие данные извлекать:
список ID (или None для
полного извлечения),
параметры пагинации,
режим ( mode – “chembl”
или “all”), план батч-
разбиения и номер
релиза. В процессе
инициализации
валидирует режим
выборки.init(ids: list[str] | None, pagination: dict[str ,
Any] | None, mode: str = "chembl",
batch_plan: BatchPlan | None = None,
release: str | None =
None)<br> post_init (self) -> None (проверка
допустимости mode)–
BatchPlan –src/bioetl/clients/chembl/
descriptor_factory.pyDataclass, описывающий
план разбиения на батчи
при выборке .
Содержит размер батча
(batch_size ) и размер
чанка ( chunk_size ) для
постраничного
извлечения.init(batch_size: int | None = None,
chunk_size: int | None = None)–41
42
43
3

Класс/Объект Предок Модуль Назначение Публичные методы Приватные методы
ChemblDescriptorFactory –src/bioetl/clients/chembl/
descriptor_factory.pyФабрика дескрипторов
ChEMBL . Хранит
конфигурационный
фасад
(ChemblContextFacade),
набор стратегий
получения данных
(fetcher_strategies
по типам сущностей),
функцию для генерации
фолбэк-значений при
ошибках
(fallback_rows ), а
также поля сортировки
для детерминизма.
Используется
пайплайном для
построения дескриптора
через registry/фабрику.init(context_facade: ChemblContextFacade,
fetcher_strategies: dict[str , FetcherStrategy],
fallback_rows: Callable[[Any, Exception],
list[dict[str , Any]]] | None = None,
sort_fields: Mapping[str , Sequence[str]] |
None = None)–
ChemblContextFacade –src/bioetl/clients/chembl/
descriptor_factory.py“Фасад” контекста
ChEMBL . Структура
для передачи в
дескриптор фабрику
необходимых
компонентов: фабрики
транспорта, стратегии
пагинации и её имени,
набора фабрик
пагинации, номера
релиза, готового клиента
Chembl (если уже создан),
либо фабрики клиента.init(transport_factory: Any,
pagination_strategy: Any,
pagination_strategy_name: str | None,
pagination_factories: Any, chembl_release:
str | None, chembl_client: Any,
client_factory: Any)–
ChemblClient ConfiguredHttpClientsrc/bioetl/clients/chembl/
client.pyAPI-клиент ChEMBL
(новая архитектура) .
Наследует общий HTTP-
клиент и предоставляет
методы для
формирования запросов
к ChEMBL. При
инициализации
загружает конфигурацию
источника и использует 
ChemblRequestBuilder
для создания запросов.init(backend: HttpBackend, , config:
SourceConfig | None = None)
<br>request_activity(self, , ids: Sequence[str]
| None = None, filters: Mapping[str , object]
| None = None, pagination:
PaginationParams | None = None, context:
RequestContext | None = None) ->
ClientRequest–44
45
46
46
47
4

Класс/Объект Предок Модуль Назначение Публичные методы Приватные методы
ChemblRequestBuilder –src/bioetl/clients/chembl/
client.pyКласс-построитель
запросов для ChEMBL API
. Инкапсулирует
логику формирования
объекта ClientRequest
(маршрут, список ID,
фильтры, параметры
пагинации и пр.).
Используется
ChemblClient для
получения настроенных
запросов.build(self, *, route: str , ids: Sequence[str] |
None = None, filters: Mapping[str , object] |
None = None, pagination:
PaginationParams | None = None, context:
RequestContext | None = None) ->
ClientRequest–
RequestsBackend HttpBackend (Protocol)src/bioetl/clients/chembl/
factories.pyРеализация HTTP-
бэкенда для ChEMBL на
базе библиотеки 
requests . Отвечает
за выполнение HTTP-
запросов к REST API
ChEMBL: реализует
методы для получения
одной записи,
итерирования по
записям и страницам, а
также закрытия
соединения.init(self) <br>fetch_one(self, , source:
SourceConfig, resource: ResourceConfig,
request: ClientRequest, context:
RequestContext | None = None) -> Record |
None <br>iter_records(self, , source:
SourceConfig, resource: ResourceConfig,
request: ClientRequest, context:
RequestContext | None = None) ->
Iterator[Record]<br>iter_pages(self, , source:
SourceConfig, resource: ResourceConfig,
request: ClientRequest, context:
RequestContext | None = None) ->
Iterator[Page]<br>metadata(self, , source:
SourceConfig) -> dict[str ,
object]<br>close(self) -> None–
AssaySchema pa.DataFrameSchemasrc/bioetl/core/schemas/
assay_schema.pyСхема валидации данных
ассая (Pandera
DataFrameSchema) .
Определяет
обязательные колонки
(assay_id, business_key и
др.) и их типы,
используется для
проверки целостности и
приведения типов
данных после
трансформации.(наследует методы валидации Pandera,
например validate(df) -> 
DataFrame )–48
4950
51
52
5

Класс/Объект Предок Модуль Назначение Публичные методы Приватные методы
AssayNormalizer –src/bioetl/pipelines/chembl/
assay/normalizers.pyНормализатор данных
assay . Предназначен
для приведения и
очистки колонок ассая (в
т.ч. обработки
вложенных параметров),
чтобы привести
DataFrame к целевому
виду. (Пока содержит
заглушку метода.)normalize(self, df: pd.DataFrame) ->
pd.DataFrame–
AssayPayloadParser –src/bioetl/pipelines/chembl/
assay/parsers.pyПарсер payload’ов ассая
. Должен разбирать
сырой JSON-ответ
ChEMBL (например, поле
assay_parameters и
связанные сущности) в
структурированный вид
(DataFrame или dict). 
(Пока заглушка.)parse(self, payload: Any) -> Any –
ChemblWriteService WriteService (Protocol)src/bioetl/pipelines/chembl/
common/base.pyСпециализированный
сервис записи для
ChEMBL-пайплайнов .
Реализует
детерминированное
сохранение результата:
формирует имена
выходных файлов
(датасет, отчёт качества,
метаданные) с
суффиксами по дате,
сохраняет DataFrame в
CSV и генерирует YAML/
JSON мета-информацию о
запуске.init(self, pipeline: ChemblCommonPipeline)
<br>save(self, df: pd.DataFrame,
artifacts: WriteArtifacts, options:
StageExecutionOptions, , context:
StageContextProtocol, runtime:
StageRuntimeContext) -> WriteResult
<br>write_metadata(self, output_dir: Path,
artifacts: WriteArtifacts, df: pd.DataFrame |
None, , dry_run: bool) -> None–53
54
55
56
57
6

Класс/Объект Предок Модуль Назначение Публичные методы Приватные методы
PipelineOutputService –src/bioetl/core/io/
output_service.pyСервис верхнего уровня
для записи результатов
пайплайна . Получает
на вход DataFrame и
артефакты, находит
настроенный writer в
конфигурации и
вызывает его для
атомарной записи
датасета. После
успешной записи
генерирует QC-метрики
(при помощи 
emit_qc_artifact ).
Используется в
ChemblAssayPipeline для
сохранения с
использованием
унифицированного writer
или отката к
ChemblWriteService .init(self, config: Mapping[str , Any] | None =
None, logger: UnifiedLogger | None =
None) <br>resolve_writer(self,
output_dir: Path) -> UnifiedOutputWriter |
None <br>save(self, df: pd.DataFrame,
artifacts: WriteArtifacts, output_dir: Path,
format: str = "csv") -> WriteResult–
WriteArtifacts –src/bioetl/core/io/
artifacts.pyСтруктура для хранения
путей выходных файлов
пайплайна . Содержит
поля для названия
датасета и путей: 
data_path  (файл
данных), 
quality_report_path
(CSV с краткой сводкой
качества), meta_path
(YAML с метаданными
запуска), 
manifest_path  (JSON-
манифест) и пр.
Заполняется во время
исполнения пайплайна и
передаётся в методы
записи.– –
run.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
pipelines/chembl/assay/run.py
base.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
pipelines/chembl/common/base.py58
5958
60
61
62
1 259
3 4 5 6 7 8 910 11 12 13 14 15 16 17 18 19 20 55 56 57
7

unified.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
core/pipeline/unified.py
chembl_extraction_service.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
pipelines/chembl/common/chembl_extraction_service.py
descriptor .py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
pipelines/chembl/common/descriptor .py
descriptor_factory.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
clients/chembl/descriptor_factory.py
client.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
clients/chembl/client.py
factories.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
clients/chembl/factories.py
assay_schema.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
core/schemas/assay_schema.py
normalizers.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
pipelines/chembl/assay/normalizers.py
parsers.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
pipelines/chembl/assay/parsers.py
output_service.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
core/io/output_service.py
artifacts.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
core/io/artifacts.py21 22 23 24 25 26 41
27 28 29 30 31 32 33 34 35 36 37 38 39 40
42
43 44 45
46 47 48
49 50 51
52
53
54
58 60 61
62
8
```
