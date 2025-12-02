# document.pdf

```text
Класс Предок Модуль Назначение Публичные методы Приватные методы
ChemblDocumentPipeline ChemblCommonPipelinesrc/bioetl/pipelines/chembl/
document/run.pyСкелет пайплайна для ChEMBL
Document с обогащением внешними
источниками . Определяет
специальные шаги обогащения,
валидации и сохранения результатов
для данных документов.build_descriptor(self)  – построить
дескриптор извлечения (переопределяет
базовый) <br> domain_enrich(self, df: 
pd.DataFrame) -> pd.DataFrame  –
обогащение данных (вызывает цепочку
обогащения после базового преобразования)
<br> validate(self, df: pd.DataFrame, 
options: StageExecutionOptions) -> 
pd.DataFrame  – валидация данных с
дополнительной проверкой 
document_chembl_id
<br> save_results(self, df: pd.DataFrame, 
artifacts: WriteArtifacts, options: 
StageExecutionOptions) -> WriteResult  –
сохранение результатов с попыткой
использования внешнего сервиса вывода,
сFallback на базовый метод при ошибках ._resolve_mode(self, config: Mapping[str, Any]) -
> str – определяет режим работы пайплайна ( chembl
или all) <br> _resolve_fallback_policy(self, 
config: Mapping[str, Any]) -> str  – читает
политику fallback из конфига ( ordered , best_effort
или strict)
<br> _build_enrichment_chain(self) -> 
tuple[str, ...]  – формирует цепочку источников
обогащения (cache, Semantic Scholar , PubMed, Crossref) в
зависимости от режима
<br> _apply_enrichment_chain(self, df: 
pd.DataFrame) -> pd.DataFrame  – проставляет метки о
цепочке обогащения и политике fallback в DataFrame .12
3
4
56
7
8
9
1

Класс Предок Модуль Назначение Публичные методы Приватные методы
ChemblCommonPipeline ChemblPipelineBasesrc/bioetl/pipelines/chembl/
common/base.pyБазовый класс для ChEMBL-
пайплайнов без legacy-зависимостей
. Отвечает за общую логику:
проверку корректности конфигурации,
инициализацию сервиса записи
результатов и создание дескриптора
извлечения для сущности.extract(self, descriptor: 
ChemblExtractionServiceDescriptor \| 
ChemblExtractionDescriptor \| None, 
options: StageExecutionOptions) -> 
pd.DataFrame  – выполняет извлечение данных
через стратегию (service или dataclass) на основе
дескриптора
<br> transform(self, df: pd.DataFrame, 
options: StageExecutionOptions) -> 
pd.DataFrame  – базовое преобразование:
вызывает pre_transform , затем 
domain_enrich  (по умолчанию возвращает 
df) <br> validate(self, df: 
pd.DataFrame, options: 
StageExecutionOptions) -> pd.DataFrame  –
валидирует DataFrame через службу валидации,
если она настроена
<br> build_descriptor(self) -> 
ChemblExtractionServiceDescriptor \| 
ChemblExtractionDescriptor  – строит
дескриптор выборки с помощью фабрики (для
сервиса ChEMBL или dataclass) ._create_descriptor_factory(self) -> 
ChemblDescriptorFactory  – создаёт фабрику
дескрипторов ChEMBL для текущей сущности
(инициализируя при необходимости реестр клиентов)
<br> _validate_common_config(self) -> None  –
проверяет конфигурацию на корректность (параметры
batch_size, max_url_length, namespace кэша, сортировку и
т.д.) <br> _get_config_value(self, 
dotted_path: str) -> Any  – утилита для получения
вложенного значения из конфига или выброса 
ConfigValidationError , если ключ отсутствует
<br> _write_quality_report(self, df: pd.DataFrame, 
output_path: Path) -> None  – генерирует CSV-отчёт по
качеству данных (число строк, столбцов, пропусков)
<br> _fallback_rows(self, ids: Iterable[str], 
exc: Exception) -> list[dict[str, Any]]  –
формирует “записи-замены” с информацией об ошибках
для каждого идентификатора при неудаче извлечения
(для fallback)
<br> _build_generic_descriptor(self) -> 
ChemblExtractionServiceDescriptor  – строит
универсальный дескриптор извлечения по конфигурации
(используется, если явно не задан специфичный
дескриптор)
<br> _extract_with_dataclass_descriptor(self, 
descriptor: ChemblExtractionDescriptor, options: 
StageExecutionOptions) -> pd.DataFrame  –
выполняет извлечение данных, если используется
dataclass-дескриптор (вызывается стратегией для 
descriptor_type="dataclass" ) .101112
13
14
1516
17
1819
20
21
22
2324
2526
2728
2

Класс Предок Модуль Назначение Публичные методы Приватные методы
ChemblPipelineBase PipelineBasesrc/bioetl/core/pipeline/
unified.pyБазовый пайплайн для ChEMBL с
делегированием доменной логики
сервису . Интегрирует сервис
извлечения ChEMBL (automatically
определяет chembl_release ) и
задаёт стандартные хуки 
pre_transform  и domain_enrich
для переопределения в подклассах.chembl_release(self) -> str \| None  –
свойство, возвращающее текущую версию
релиза ChEMBL (если определено)
<br> resolve_chembl_release(self, 
chembl_client: Any) -> str  – вызывать
сервис извлечения для получения версии
релиза ChEMBL по данному клиенту
<br> get_release(self) -> str \| None  –
алиас для chembl_release  (вернуть версию
релиза) <br> build_descriptor(self) -> 
Any – абстрактный метод, должен создавать
дескриптор выборки для сущности (в этом
классе бросает NotImplementedError  и
реализуется в потомках)
<br> pre_transform(self, df: 
pd.DataFrame) -> pd.DataFrame  – хук
предварительного преобразования (умолчание
– вернуть df без изменений)
<br> domain_enrich(self, df: 
pd.DataFrame) -> pd.DataFrame  – хук
обогащения доменными данными (умолчание –
вернуть df, переопределяется при
необходимости)
<br> run_descriptor_extraction(self, 
descriptor: 
ChemblExtractionServiceDescriptor, ids: 
Sequence[str] \| None, *, summary_event: 
str, metadata_filters: Mapping[str, Any] 
\| None = None, fetch_mode: str = 
"default", **batch_kwargs) -> 
tuple[pd.DataFrame, 
BatchExtractionStats]  – запускает
извлечение данных по дескриптору через 
ChemblExtractionService  с логированием и
обработкой ошибок ._resolve_extraction_service(extraction_service: 
ChemblExtractionService \| None, 
extraction_service_factory: Callable[[], 
ChemblExtractionService] \| None) -> 
ChemblExtractionService  – статический метод,
определяющий какой сервис извлечения использовать:
напрямую переданный или создаёт стандартный, если
фабрика не задана .2930
31
32
33
34
35
36373839
3

Класс Предок Модуль Назначение Публичные методы Приватные методы
PipelineBase PipelineRuntimeBasesrc/bioetl/core/pipeline/
unified.pyАбстрактный базовый класс,
определяющий интерфейс стадий
пайплайна . Задаёт основные
этапы ETL (extract, transform, validate,
save_results) и их реализацию по
умолчанию – включая валидацию
Pandera-схемой и сохранение
результатов через подключаемый
сервис записи.extract(self, descriptor: Any, options: 
StageExecutionOptions) -> pd.DataFrame  –
абстрактный  метод извлечения данных
(реализуется в подклассах)
<br> transform(self, df: pd.DataFrame, 
options: StageExecutionOptions) -> 
pd.DataFrame  – абстрактный  метод
трансформации данных (реализуется в
подклассах) <br> validate(self, df: 
pd.DataFrame, options: 
StageExecutionOptions) -> pd.DataFrame  –
выполняет валидацию DataFrame, если
включена (вызывает Pandera-валидатор через
ValidationService)
<br> save_results(self, df: pd.DataFrame, 
artifacts: WriteArtifacts, options: 
StageExecutionOptions) -> WriteResult  –
сохраняет DataFrame, используя 
write_service  (если не настроен, бросает
исключение) <br> prepare_run(self, 
options: StageExecutionOptions) -> None
– опциональный хук, вызывается перед
началом стадии extract (умолчание – ничего не
делает) <br> finalize_run(self, 
run_result: RunResult) -> None  –
опциональный хук, вызывается после
завершения стадии записи (умолчание – ничего
не делает) <br> build_stage_plan(self, 
context: StageContext, options: 
StageExecutionOptions) -> 
tuple[StageDescriptor, ...]  – формирует
план выполнения стадий по умолчанию
(extract→transform→validate→save), учитывая
настройки (dry_run, наличие валидатора и пр.)
.(нет)
DocumentSchemapa.DataFrameSchema
(Pandera)src/bioetl/core/schemas/
document_schema.pyСхема данных документов ChEMBL для
валидации результирующего
DataFrame . Определяет
обязательные поля документа
(document_id , doi, title, 
journal , и др.) и их типы,
используясь для проверки выходного
набора данных пайплайна.(нет – объект схемы) (нет)4041
42
4344
4546
47
48
49
50
4

Класс Предок Модуль Назначение Публичные методы Приватные методы
ChemblExtractionService (нет)src/bioetl/pipelines/chembl/
common/
chembl_extraction_service.pyСервис, инкапсулирующий общие
шаги извлечения данных из ChEMBL
. Управляет определением
актуального релиза ChEMBL,
формированием контекста выборки,
побатчевой загрузкой записей через
клиент ChEMBL и финализацией
объединённого DataFrame
результатов.chembl_release(self) -> str \| None  –
свойство, возвращающее кешированную
версию релиза ChEMBL (определяется при
первом запросе)
<br> resolve_chembl_release(self, 
chembl_client: BaseClient) -> str  –
определяет версию релиза ChEMBL через вызов
метода status()  у клиента, кеширует и
возвращает её
<br> build_context(self, descriptor: Any, 
pipeline: Any, *, metadata_filters: 
Mapping[str, Any] \| None = None, 
fetch_mode: str = "default") -> 
dict[str, Any]  – создаёт контекст
выполнения для выборки: дополняет контекст
дескриптора параметрами (фильтры, режим
выборки, версия релиза)
<br> finalize_dataframe(self, dataframe: 
pd.DataFrame, finalizer: Any, stats: 
BatchExtractionStats) -> 
tuple[pd.DataFrame, 
BatchExtractionStats]  – применяет
функцию-финализатор к объединённому
DataFrame и обновляет статистику (кол-во строк,
длительность)
<br> run_descriptor_extraction(self, 
pipeline: Any, descriptor: Any, ids: 
Sequence[str] \| None, *, summary_event: 
str, metadata_filters: Mapping[str, Any] 
\| None = None, fetch_mode: str = 
"default", **batch_kwargs) -> 
tuple[pd.DataFrame, 
BatchExtractionStats]  – выполняет
извлечение данных по дескриптору: формирует
контекст, запускает итеративную выборку через
fetcher (с учётом paging и batch_size) и
возвращает объединённый DataFrame и
статистику ._normalize_ids(self, ids: Sequence[str] \| None, 
context: Mapping[str, Any]) -> list[str] \| None
– нормализует список идентификаторов (преобразует в
строки, удаляет пустые)
<br> _resolve_page_size(self, context: 
Mapping[str, Any], default: int = 1000) -> int  –
определяет размер страницы (page_size) для выборки из
контекста или берёт значение по умолчанию
<br> _resolve_client_settings(self, context: 
Mapping[str, Any]) -> Mapping[str, Any]  –
извлекает из контекста дополнительные настройки
клиента (фильтры запросов)
<br> _build_client_fetcher(self, chembl_client: 
BaseClient, *, page_size: int, client_settings: 
Mapping[str, Any] \| None = None) -> 
Callable[[Sequence[str] \| None], Any]  – создает
функцию-выборку (fetcher) для клиента ChEMBL, которая
по заданному списку ID выполняет запрос через 
iter_records  и возвращает результаты с метаданными
вызова <br> _resolve_fetcher(self, 
descriptor: Any, context: Mapping[str, Any], *, 
page_size: int, client_settings: Mapping[str, 
Any] \| None = None) -> Callable[[Sequence[str] 
\| None], Any]  – выбирает функцию-выборку: если
дескриптор предоставляет фабрику fetcher’ов –
использует её, иначе возвращает fetcher для клиента
ChEMBL .
ChemblExtractionServiceDescriptor (нет)src/bioetl/core/pipeline/
unified.pyОписание параметров извлечения
сущности ChEMBL (service-дескриптор)
. Содержит функции для
построения контекста
(build_context ), фабрики выборки
(fetcher_factory ) и финализатора
(finalizer_factory ), используемые
ChemblExtractionService  для
получения и обработки данных.(нет) (нет)515253
5455
5657
5859
606162
63
64
6566
6768
69
5

Класс Предок Модуль Назначение Публичные методы Приватные методы
ChemblDescriptorFactory (нет)src/bioetl/clients/chembl/
descriptor_factory.pyФабрика дескрипторов ChEMBL . На
основе фасада контекста ChEMBL
(ChemblContextFacade ) и стратегий
выборки ( FetcherStrategy ) создаёт
дескриптор извлечения для указанной
сущности – включая настройки
пагинации, клиент API и функции
выборки/финализации результатов.build(self, entity_name: str) -> 
ChemblExtractionServiceDescriptor  –
создать дескриптор извлечения для сущности с
именем entity_name  (использует
предварительно сконфигурированные
стратегии и контекст).(нет)
ExtractionStrategyFactory (нет)src/bioetl/pipelines/chembl/
common/strategies.pyФабрика стратегий извлечения
данных . Инкапсулирует две
реализации стратегии – через
dataclass-дескриптор и service-
дескриптор – и по запросу возвращает
подходящую стратегию в зависимости
от типа дескриптора, указанного в
конфигурации пайплайна.get(self, descriptor_type: str) -> 
ExtractionStrategy  – получить объект
стратегии, поддерживающий заданный тип
дескриптора ( "dataclass"  или "service" )
.(нет)
ServiceExtractionStrategy (нет)src/bioetl/pipelines/chembl/
common/strategies.pyСтратегия извлечения через сервис-
дескрипторы . Реализует логику
выборки данных для дескриптора
типа "service" : вызывает у
пайплайна построение дескриптора
(если не передан) и метод 
run_descriptor_extraction  для
получения данных из ChEMBL API;
возвращает объединённый DataFrame
результатов или пустой DataFrame,
если выборка не вернула данных.supports(self, descriptor_type: str) -> 
bool – возвращает True, если тип
дескриптора равен "service"
<br> run(self, pipeline: 
ChemblCommonPipeline, descriptor: 
ChemblExtractionServiceDescriptor \| 
ChemblExtractionDescriptor \| None, 
options: StageExecutionOptions) -> 
pd.DataFrame  – выполняет процесс
извлечения для сервисного дескриптора:
определяет ids из конфигурации, получает
(или строит) дескриптор, вызывает 
pipeline.run_descriptor_extraction(...)
для получения данных; в случае пустого
результата возвращает пустой DataFrame либо
пустую рамку от ValidationService .(нет)70
71
7273
747576
7778
6

Класс Предок Модуль Назначение Публичные методы Приватные методы
ChemblWriteService (нет)src/bioetl/pipelines/chembl/
common/base.pyДетерминированная запись для
ChEMBL-пайплайнов . Класс-
утилита для сохранения результатов:
сохраняет итоговый DataFrame в CSV-
файл с фиксированным шаблоном
имени (например, 
<entity>_chembl_all_<date>.csv ),
формирует отчёт по качеству данных
и YAML с метаданными запуска,
обеспечивая воспроизводимость и
единообразие вывода.save(self, df: pd.DataFrame, artifacts: 
WriteArtifacts, options: 
StageExecutionOptions, *, context: 
StageContextProtocol, runtime: 
StageRuntimeContext) -> WriteResult  –
сохраняет DataFrame в CSV (если не dry_run ),
записывает отчёт качества
(_write_quality_report ) и метаданные
(run_id, размеры и пр.), возвращает объект с
информацией об артефактах записи
<br> write_metadata(self, output_dir: 
Path, artifacts: WriteArtifacts, df: 
pd.DataFrame \| None, *, dry_run: bool) 
-> None  – метод совместимости (не выполняет
действий, метаданные уже сохраняются в 
save()) .(нет)
DefaultValidationService (нет)src/bioetl/core/pipeline/
services/defaults.pyСтандартный сервис валидации
DataFrame с использованием Pandera-
схемы . Выполняет проверку
DataFrame на соответствие заданной
схеме (если схема установлена) и
сортирует строки/столбцы в
результатах для детерминизма.empty_frame(self) -> pd.DataFrame  –
формирует пустой DataFrame согласно схеме
(создаёт столбцы нужных типов, но без строк)
<br> validate(self, df: pd.DataFrame, 
*, pipeline: PipelineBaseProtocol, 
options: StageExecutionOptions) -> 
pd.DataFrame  – валидирует df с помощью
внутренней Pandera-схемы и возвращает
отсортированный по столбцам DataFrame
(игнорируя pipeline и options) .(нет)
PipelineOutputService (нет)src/bioetl/core/io/
output_service.pyСервис для вывода результатов
пайплайна (Pipeline Output) .
Пытается найти в конфигурации и
использовать унифицированный
writer (реализующий протокол записи
данных) для сохранения датасета
(например, в внешний хранилище или
БД); если writer не настроен,
генерирует исключение, сигнализируя
об отсутствии конфигурации вывода
(что заставляет пайплайн
использовать стандартный механизм
записи).resolve_writer(self, output_dir: Path) -
> UnifiedOutputWriter \| None  – извлекает
из конфигурации объект writer для записи
данных и настраивает его выходную
директорию (если задан)
<br> save(self, df: pd.DataFrame, 
artifacts: WriteArtifacts, output_dir: 
Path, format: str = "csv") -> 
WriteResult  – сохраняет DataFrame, используя
настроенный writer (если найден; может
использовать атомарную запись через 
write_dataset_atomic  или стандартную
через write), и инициирует генерацию QC-
артефактов; при ошибке логирует и
пробрасывает исключение .(нет)79
8081
8283
8485
8687
88
8990
9192
7

Класс Предок Модуль Назначение Публичные методы Приватные методы
ConfigValidationError ValueErrorsrc/bioetl/pipelines/chembl/
common/descriptor.pyИсключение, выбрасываемое при
некорректной пользовательской
конфигурации пайплайна .
Используется для сигнализации о
неверных параметрах в настройках
(например, неподдерживаемое
значение режима, отсутствие
обязательных полей сортировки и
т.д.), прерывая выполнение
пайплайна с сообщением об ошибке.(нет) (нет)
run.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
pipelines/chembl/document/run.py
base.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
pipelines/chembl/common/base.py
strategies.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
pipelines/chembl/common/strategies.py
unified.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
core/pipeline/unified.py
document_schema.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
core/schemas/document_schema.py
chembl_extraction_service.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
pipelines/chembl/common/chembl_extraction_service.py
descriptor_factory.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
clients/chembl/descriptor_factory.py
defaults.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
core/pipeline/services/defaults.py
output_service.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
core/io/output_service.py
descriptor .py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
pipelines/chembl/common/descriptor .py93
1 2 3 4 5 6 7 8 9
10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 79 80 81 82 83
27 28 71 72 73 74 75 76 77 78
29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 69
50
51 52 53 54 55 56 57 58 59 60 61 62 63 64 65 66 67 68
70
84 85 86 87
88 89 90 91 92
93
8
```
