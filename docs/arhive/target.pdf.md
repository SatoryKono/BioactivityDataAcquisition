# target.pdf

```text
Класс Предок Модуль Назначение Публичные методы Приватные методы
ChemblTargetPipelineChemblCommonPipeline src/bioetl/pipelines/chembl/
target/run.pyОсновной класс пайплайна для
сущности target  из ChEMBL
(включая обогащение данными
UniProt/IUPHAR) . Наследует
общий Chembl-пайплайн и
определяет специфичные шаги
для target .• __init__(self, config: 
Mapping[str, Any], *, run_id: str | 
None = None)  – конструктор,
инициализирует родительский класс с
типом дескриптора service , устанавливает
схему валидации TargetSchema  и сервис
валидации .<br>• 
build_descriptor(self) -> Any  –
строит дескриптор вызовом реализации
из базового класса .<br>• 
validate(self, df: pd.DataFrame, 
options: StageExecutionOptions) -> 
pd.DataFrame  – выполняет валидацию
через базовый метод и дополнительно
проверяет наличие target_chembl_id
(обязательное поле) .<br>• 
save_results(self, df: 
pd.DataFrame, artifacts: 
WriteArtifacts, options: 
StageExecutionOptions) -> 
WriteResult  – сохраняет результат через
PipelineOutputService , при ошибках
откатывается к реализации родителя
.—112
3
45
6
7
1

Класс Предок Модуль Назначение Публичные методы Приватные методы
ChemblCommonPipeline ChemblPipelineBasesrc/bioetl/pipelines/chembl/
common/base.pyОбщий базовый класс для
современных ChEMBL-
пайплайнов без legacy-
зависимостей . Отвечает за
проверку конфигурации,
создание сервисов (клиентов,
записи и пр.) и реализацию
стандартных стадий ETL.• __init__(self, config: 
Mapping[str, Any], *, run_id: str | 
None = None, extraction_service: 
ChemblExtractionService | None = 
None, extraction_service_factory: 
Callable[[], 
ChemblExtractionService] | None = 
None, descriptor_factory: 
ChemblDescriptorFactory | None = 
None, client_registry: 
ClientFactoryRegistry | None = 
None, ... descriptor_type: str = 
"service", 
extraction_strategy_factory: 
ExtractionStrategyFactory | None = 
None) – конструктор, вызывает базовый
ChemblPipelineBase, валидирует конфиг и
настраивает службы (запись через
ChemblWriteService, стратегии извлечения
и др.) .<br>• extract(self, 
descriptor: 
ChemblExtractionServiceDescriptor | 
ChemblExtractionDescriptor | None, 
options: StageExecutionOptions) -> 
pd.DataFrame  – реализует стадию
извлечения: выбирает стратегию по типу
дескриптора и выполняет её
(strategy.run(...) ) .<br>• 
transform(self, df: pd.DataFrame, 
options: StageExecutionOptions) -> 
pd.DataFrame  – стадия трансформации:
вызывает хуки pre_transform  и 
domain_enrich  (можно переопределить
в наследниках) .<br>• 
validate(self, df: pd.DataFrame, 
options: StageExecutionOptions) -> 
pd.DataFrame  – выполняет валидацию
через validation_service  (если
настроен Pandera-валидатор) .<br>• 
build_descriptor(self) -> 
ChemblExtractionServiceDescriptor | 
ChemblExtractionDescriptor  – строит
дескриптор для извлечения: для типа 
service  вызывает фабрику дескрипторов
(_descriptor_factory.build(...) )
 (для dataclass  бросает исключение).• _create_descriptor_factory(self) -> 
ChemblDescriptorFactory  – создаёт фабрику
дескрипторов ChEMBL через 
build_pipeline_chembl_factory  и реестр клиентов
.<br>• _validate_common_config(self) -> 
None – проверяет корректность ключевых настроек
ChEMBL (batch_size, max_url_length, namespace, sort fields и
т.д.) .<br>• 
_get_config_value(self, path: str) -> Any  –
утилита для извлечения значения из config по dotted-пути
(с валидацией наличия) .<br>• 
_write_quality_report(self, df: pd.DataFrame, 
output_path: Path) -> None  – записывает CSV отчёт
по качеству (число строк, столбцов, пропущенных
значений) .<br>• _fallback_rows(self, ids: 
Iterable[str], exc: Exception) -> list[dict[str, 
Any]] – формирует записи-замены при ошибках
извлечения (с кодом ошибки и т.д.) .<br>• 
_build_generic_descriptor(self) -> 
ChemblExtractionServiceDescriptor  – строит
универсальный дескриптор с контекстом (использует
конфиг sources.chembl  для настроек клиента и fetcher)
.88910
1112
13
14
151617
1819
20
21
2223
24
2

Класс Предок Модуль Назначение Публичные методы Приватные методы
ChemblPipelineBase PipelineBasesrc/bioetl/core/pipeline/
unified.pyБазовый класс пайплайна
ChEMBL, делегирующий
выполнение доменной логики
специальному сервису
извлечения . Интегрирует 
ChemblExtractionService  для
выполнения batched-выборок
из API.• __init__(self, config: 
Mapping[str, Any], *, run_id: str | 
None = None, extraction_service: 
ChemblExtractionService | None = 
None, extraction_service_factory: 
Callable[[], 
ChemblExtractionService] | None = 
None, **kwargs)  – конструктор,
вызывает базовый PipelineBase и
инициализирует 
self.extraction_service  (либо
использует переданный, либо создаёт
стандартный) .<br>• 
chembl_release(self) -> str | None
– свойство, возвращающее текущий релиз
ChEMBL (берётся у внутреннего 
extraction_service ) .<br>• 
resolve_chembl_release(self, 
chembl_client) -> str  – получить
версию релиза ChEMBL, вызвав метод у
клиента Chembl (через extraction_service )
.<br>• 
get_release(self) -> str | None  –
алиас к chembl_release  для получения
версии релиза .<br>• 
build_descriptor(self) -> Any  –
абстрактный метод построения
дескриптора извлечения (реализуется в
наследниках, например, в
ChemblCommonPipeline) .<br>• 
pre_transform(self, df: 
pd.DataFrame) -> pd.DataFrame  – хук
предобработки данных перед
трансформацией (по умолчанию
возвращает df без изменений) .<br>• 
domain_enrich(self, df: 
pd.DataFrame) -> pd.DataFrame  – хук
доменного обогащения данных (по
умолчанию ничего не делает) .<br>• 
run_descriptor_extraction(self, 
descriptor: 
ChemblExtractionServiceDescriptor, 
ids: Sequence[str] | None, 
**kwargs) -> tuple[pd.DataFrame, 
BatchExtractionStats]  – выполняет
извлечение по дескриптору через
встроенный ChemblExtractionService  с
логированием статистики .• 
_resolve_extraction_service(extraction_service, 
extraction_service_factory) -> 
ChemblExtractionService  – статический метод,
выбирающий способ инициализации 
ChemblExtractionService  (либо напрямую, либо через
фабрику, с защитой от одновременной передачи двух)
.25252627
28
29
30
31
32
33
343536
37
3

Класс Предок Модуль Назначение Публичные методы Приватные методы
ChemblExtractionServiceDescriptorGeneric[ChemblPipelineT]
(типовой класс)src/bioetl/core/pipeline/
unified.pyДескриптор, описывающий
параметры извлечения
сущности ChEMBL при
использовании сервисного
подхода. Содержит функции
для формирования контекста
запроса, фабрики выборки
данных и финализатора
результатов .
Используется стратегией 
ServiceExtractionStrategy  для
определения, как извлекать
данные.• __init__(self, *, build_context: 
Callable[[ChemblPipelineT], 
Mapping[str, Any]], 
fetcher_factory: 
Callable[[Mapping[str, Any]], 
Callable[[Sequence[str] | None], 
Any]], finalizer_factory: 
Callable[[Mapping[str, Any]], 
Callable[[pd.DataFrame], 
pd.DataFrame]])  – конструктор,
сохраняет переданные фабричные
функции (контекста, выборки,
финализации) .—
ChemblExtractionDescriptor object (dataclass)src/bioetl/pipelines/chembl/
common/descriptor.pyОблегчённый описатель
извлечения данных из ChEMBL,
используемый в “dataclass”-
стратегии. Хранит список
идентификаторов ids,
параметры пагинации, режим
(mode, напр. "chembl" или
"all") и план разбиения на
батчи . Предназначен для
конвейеров, использующих
dataclass-дескрипторы
(например, активности).• __post_init__(self) -> None  – пост-
инициализация (dataclass), проверяет
корректность поля mode (должно быть
"chembl" или "all", иначе вызывает
исключение) .—
ServiceExtractionStrategy —src/bioetl/pipelines/chembl/
common/strategies.pyСтратегия выполнения стадии 
extract  с использованием
сервисных дескрипторов.
Поддерживает тип дескриптора
"service"  и при запуске
извлечения вызывает метод 
run_descriptor_extraction
у пайплайна для заданного
дескриптора .• supports(self, descriptor_type: 
str) -> bool  – возвращает True для
типа дескриптора "service"
.<br>• run(self, pipeline: 
ChemblCommonPipeline, descriptor: 
ChemblExtractionServiceDescriptor | 
ChemblExtractionDescriptor | None, 
options: StageExecutionOptions) -> 
pd.DataFrame  – выполняет извлечение:
строит дескриптор (если не задан) и
вызывает у пайплайна 
run_descriptor_extraction  с
необходимыми параметрами (IDs,
batch_size и пр.) .—38
3839
4041
42
4243
444544
46
4748
4

Класс Предок Модуль Назначение Публичные методы Приватные методы
DataclassExtractionStrategy —src/bioetl/pipelines/chembl/
common/strategies.pyСтратегия выполнения extract
через dataclass -дескриптор.
Поддерживает тип 
"dataclass"  и запускает
кастомную логику извлечения,
определённую в пайплайне для
dataclass-дескриптора
(например, для ActivityPipeline)
.• supports(self, descriptor_type: 
str) -> bool  – возвращает True для
типа дескриптора "dataclass"
.<br>• run(self, pipeline: 
ChemblCommonPipeline, descriptor: 
ChemblExtractionServiceDescriptor | 
ChemblExtractionDescriptor | None, 
options: StageExecutionOptions) -> 
pd.DataFrame  – выполняет извлечение:
если дескриптор не задан – строит через 
pipeline.build_descriptor() , затем
вызывает 
_extract_with_dataclass_descriptor
у пайплайна (если дескриптор типа
ChemblExtractionDescriptor) ; при
отсутствии дескриптора или в dry-run
возвращает пустой DataFrame.—
ExtractionStrategyFactory —src/bioetl/pipelines/chembl/
common/strategies.pyФабрика для выбора стратегии
извлечения. При
инициализации регистрирует
набор стратегий (по
умолчанию оба типа: Dataclass
и Service) , а методом get
возвращает стратегию,
поддерживающую указанный
тип дескриптора, без явных
условных операторов .• __init__(self, strategies: 
Iterable[ExtractionStrategy] | None 
= None)  – при создании фабрики
инициализирует список стратегий; если
не задано, регистрирует стратегии по
умолчанию (dataclass, service) .<br>•
get(self, descriptor_type: str) -> 
ExtractionStrategy  – возвращает
первую подходящую стратегию для
данного типа дескриптора или
выбрасывает ValueError , если тип не
поддерживается .—495049
51
5253
54
55565457
5859
5

Класс Предок Модуль Назначение Публичные методы Приватные методы
ChemblExtractionService —src/bioetl/pipelines/chembl/
common/
chembl_extraction_service.pyСервис, инкапсулирующий
общие шаги извлечения
данных ChEMBL: определение
контекста запроса,
нормализация списка ID,
выбор подходящего fetcher
(клиентского метода) и
финализация DataFrame
. Хранит версию релиза
ChEMBL и способен её
определять через клиент
ChEMBL. Выполняет батч-
извлечения через функцию 
execute_chembl_batches .• chembl_release(self) -> str | 
None – свойство, возвращающее
сохранённый номер релиза ChEMBL (если
уже определён) .<br>• 
resolve_chembl_release(self, 
chembl_client: BaseClient) -> str  –
обращается к методу status()  клиента
ChEMBL для получения текущей версии
релиза и сохраняет её .<br>• 
build_context(self, descriptor: 
Any, pipeline: Any, *, 
metadata_filters: Mapping[str, Any] 
| None = None, fetch_mode: str = 
"default") -> dict[str, Any]  –
формирует словарь контекста для
выборки: на основе 
descriptor.build_context(pipeline)
дополняет параметрами (фильтры
метаданных, режим выборки, версия
релиза и клиент) .<br>• 
finalize_dataframe(self, dataframe: 
pd.DataFrame, finalizer: Any, 
stats: BatchExtractionStats) -> 
tuple[pd.DataFrame, 
BatchExtractionStats]  – применяет
функцию finalizer  к итоговому DataFrame и
обновляет статистику (кол-во строк,
длительность и пр.) .<br>• 
run_descriptor_extraction(self, 
pipeline: Any, descriptor: Any, 
ids: Sequence[str] | None, *, 
summary_event: str, 
metadata_filters: Mapping[str, Any] 
| None = None, fetch_mode: str = 
"default", **batch_kwargs) -> 
tuple[pd.DataFrame, 
BatchExtractionStats]  – выполняет
полное извлечение по дескриптору:
строит контекст, нормализует IDs,
определяет fetcher  (через фабрику
дескриптора или стандартный клиент
ChEMBL) , выполняет батч-запросы 
execute_chembl_batches  и
финализирует результат через 
finalize_dataframe .• 
_normalize_ids(self, ids: Sequence[str] | None, 
context: Mapping[str, Any]) -> list[str] | None
– нормализует список идентификаторов (приводит к
строкам) либо извлекает их из контекста .<br>• 
_resolve_page_size(self, context: Mapping[str, 
Any], default: int = 1000) -> int  – определяет
размер страницы (лимит) для запросов из контекста или
берёт значение по умолчанию .<br>• 
_resolve_client_settings(self, context: 
Mapping[str, Any]) -> Mapping[str, Any]  –
получает доп. настройки клиента из контекста (если
заданы) .<br>• _build_client_fetcher(self, 
chembl_client: BaseClient, *, page_size: int, 
client_settings: Mapping[str, Any] | None = 
None) -> Callable[[Sequence[str] | None], Any]  –
возвращает функцию для выборки батча: формирует
объект ClientRequest  и использует 
chembl_client.iter_records  для получения
результатов .<br>• _resolve_fetcher(self, 
descriptor: Any, context: Mapping[str, Any], *, 
page_size: int, client_settings: Mapping[str, 
Any] | None = None) -> Callable[[Sequence[str] | 
None], Any]  – выбирает функцию выборки: если в
дескрипторе определена фабрика fetcher , использует её;
иначе строит fetcher через ChemblClient (вызывая 
_build_client_fetcher ) .60
6162
6364
6561
6667
686970
71
72
73
7475
6

Класс Предок Модуль Назначение Публичные методы Приватные методы
ChemblDescriptorFactory dataclasssrc/bioetl/clients/chembl/
descriptor_factory.pyФабрика для создания
дескрипторов ChEMBL.
Инкапсулирует 
ChemblContextFacade  (контекст
подключения: транспорт,
параметры пагинации,
фабрику клиента и пр.) и
словарь стратегий выборки
данных . Метод 
build(entity)  у фабрики
(реализован через внутренний
builder) возвращает
сконфигурированный
экземпляр дескриптора 
ChemblExtractionServiceDescriptor
или аналогичный для
указанной сущности.(явных публичных методов нет,
используются поля и фабричный метод 
build через встроенный builder)—
TargetSchemapa.DataFrameSchema
(Pandera)src/bioetl/core/schemas/
target_schema.pyPandera-схема DataFrame для
сущности target . Определяет
структуру выходного набора
данных target: список
обязательных столбцов
(target_id , pref_name , 
organism , target_type , 
business_key , 
business_key_hash , 
row_hash ) с их типами и
условиями (например, 
target_id  не nullable и т.д.)
. Используется для
проверки и валидирования
данных на стадии validate .• (набор методов унаследован от Pandera
DataFrameSchema, например 
validate(df)  для валидации;
дополнительных методов не добавлено)—
DefaultValidationService —src/bioetl/core/pipeline/
services/defaults.pyСервис валидации DataFrame
по схеме Pandera. Принимает
объект схемы ( validator ) и
обеспечивает проверку
DataFrame на соответствие
этой схеме с последующей
сортировкой данных для
детерминизма .
Используется в пайплайне как
реализация стадии validate .• 
empty_frame(self) -> pd.DataFrame
– возвращает пустой DataFrame согласно
схеме (создаёт колонки нужных типов, но
без строк) .<br>• 
validate(self, df: pd.DataFrame, *, 
pipeline: PipelineBaseProtocol, 
options: StageExecutionOptions) -> 
pd.DataFrame  – валидирует DataFrame с
помощью Pandera-схемы
(self.validator.validate(df) ) и
затем сортирует колонки и строки для
стабильности результата .—7677
78
7879
808182
8384
7

Класс Предок Модуль Назначение Публичные методы Приватные методы
ChemblWriteService —src/bioetl/pipelines/chembl/
common/base.pyСервис записи результатов для
ChEMBL-пайплайнов с
детерминированным
именованием файлов.
Формирует пути для выходного
CSV-файла (включая дату и
название сущности), отчёта по
качеству, YAML-файла
метаданных и JSON манифеста,
затем сохраняет DataFrame в
CSV и записывает
сопутствующие файлы .
В режиме extended  может
вызывать дополнительную
запись метаданных через хук
пайплайна.• save(self, df: pd.DataFrame, 
artifacts: WriteArtifacts, options: 
StageExecutionOptions, *, context: 
StageContextProtocol, runtime: 
StageRuntimeContext) -> 
WriteResult  – сохраняет DataFrame в
CSV по сформированному пути (если не 
dry_run ), вызывает 
_write_quality_report  для отчета
качества, записывает файл метаданных
(YAML) и манифест запуска (JSON), при
расширенном режиме вызывает
дополнительную запись метаданных, если
определена .<br>• 
write_metadata(self, output_dir: 
Path, artifacts: WriteArtifacts, 
df: pd.DataFrame | None, *, 
dry_run: bool) -> None  – метод для
совместимости с интерфейсом
WriteService, в данном классе не
выполняет действий (метаданные уже
записаны в save) .—
PipelineOutputService —src/bioetl/core/io/
output_service.pyСервис-утилита для сохранения
результатов пайплайна с
использованием
унифицированного writer из
конфигурации. При вызове
пытается получить
настроенный 
UnifiedOutputWriter  из
конфигурации
(resolve_writer ), и если он
задан – делегирует ему запись
DataFrame и генерацию
артефактов (QC метрик), либо
бросает ошибку при отсутствии
настроек writer . В
пайплайне
ChemblTargetPipeline
используется для попытки
атомарной записи результатов.• resolve_writer(self, output_dir: 
Path) -> UnifiedOutputWriter | 
None – по переданному каталогу
пытается получить объект writer из
конфигурации (например, заранее
сконфигурированный ArtifactWriter ),
устанавливает для него выходной каталог
.<br>• save(self, df: 
pd.DataFrame, artifacts: 
WriteArtifacts, output_dir: Path, 
format: str = "csv") -> 
WriteResult  – сохраняет DataFrame,
используя настроенный writer: либо через
метод write_dataset_atomic , либо 
write, в зависимости от доступности,
затем ловит исключения и логирует их
; после успешной записи пытается
сгенерировать QC-отчёт
(emit_qc_artifact ).—85868587
88
89908991
92
93
8

Класс Предок Модуль Назначение Публичные методы Приватные методы
WriteArtifacts dataclasssrc/bioetl/core/io/
artifacts.pyСтруктура данных для
хранения путей выходных
файлов пайплайна. Содержит
поля: dataset  (имя
основного набора данных), 
data_path  (путь к файлу
данных), meta_path  (путь к
YAML-файлу метаданных), 
manifest_path  (путь к JSON-
манифесту), 
quality_report_path  (путь к
CSV файлу с отчётом качества), 
qc_summary_path  (путь для
сводки QC) и словарь extra
для дополнительных
артефактов . Эти пути
заполняются в процессе
сохранения результатов
(например, ChemblWriteService
формирует их имена).— —
ChemblClient ConfiguredHttpClientsrc/bioetl/clients/chembl/
client.pyКлиент для REST API ChEMBL в
унифицированной клиентской
архитектуре. Наследует
базовый HTTP-клиент
(ConfiguredHttpClient ) и
обеспечивает выполнение
запросов к ChEMBL API
(например, к эндпоинту activity )
с поддержкой пагинации и
фильтров . При
инициализации загружает
конфигурацию источника
ChEMBL и использует 
HttpBackend  (например,
RequestsBackend) для
выполнения HTTP-запросов.• __init__(self, backend: 
HttpBackend, *, config: 
SourceConfig | None = None)  –
инициализирует клиент ChEMBL;
загружает конфиг источника (если не
предоставлен) и вызывает 
ConfiguredHttpClient.__init__ ,
привязывая backend .<br>• 
request_activity(self, *, ids: 
Sequence[str] | None = None, 
filters: Mapping[str, object] | 
None = None, pagination: 
PaginationParams | None = None, 
context: RequestContext | None = 
None) -> ClientRequest  – формирует
запрос для получения activity : возвращает
объект ClientRequest  с установленным
маршрутом "activity" , списком ID,
фильтрами и параметрами пагинации
 (фактическое выполнение запроса
происходит при вызове методов backend
через iter_records ).—94
95
95969697
98
99
9

Класс Предок Модуль Назначение Публичные методы Приватные методы
ChemblRequestBuilder —src/bioetl/clients/chembl/
client.pyВспомогательный класс для
формирования запросов к
ChEMBL API. Представлен как
dataclass, принимает
конфигурацию источника
(SourceConfig ) и на основе
маршрута и параметров строит
объект ClientRequest  для
выполнения HTTP-запроса
. Используется внутри 
ChemblClient  для создания
запросов к различным
ресурсам.• build(self, *, route: str, ids: 
Sequence[str] | None = None, 
filters: Mapping[str, object] | 
None = None, pagination: 
PaginationParams | None = None, 
context: RequestContext | None = 
None) -> ClientRequest  – создаёт и
возвращает объект ClientRequest  с
заданным маршрутом и параметрами
(списком идентификаторов, фильтрами,
информацией о пагинации и контексте)
.—
UniProtClient ConfiguredHttpClientsrc/bioetl/clients/uniprot/
client.pyКлиент для REST API UniProt,
реализованный в общей
архитектуре клиентов.
Наследует ConfiguredHttpClient
аналогично ChemblClient, при
создании загружает конфиг
источника UniProt и использует
HttpBackend  для запросов.
Предоставляет метод для
формирования запроса на
получение данных белков.• __init__(self, backend: 
HttpBackend, *, config: 
SourceConfig | None = None)  –
инициализация клиента UniProt;
загружает конфигурацию UniProt (если не
передана) и вызывает базовый
инициализатор с данным backend
.<br>• request_proteins(self, *, 
ids: Sequence[str] | None = None, 
filters: Mapping[str, object] | 
None = None, pagination: 
PaginationParams | None = None, 
context: RequestContext | None = 
None) -> ClientRequest  – формирует 
ClientRequest  для получения данных о
белках (маршрут "protein" , с
заданными идентификаторами,
фильтрами и пагинацией) .—100
101
102 103
104105
106 107
10

Класс Предок Модуль Назначение Публичные методы Приватные методы
RequestsBackend HttpBackendsrc/bioetl/clients/chembl/
factories.pyРеализация HTTP-бэкенда на
базе библиотеки requests .
Предоставляет
низкоуровневые методы для
выполнения запросов к REST
API ChEMBL и обработки
ответа. Используется по
умолчанию клиентами ChEMBL
(и аналогично другими) для
фактического выполнения
HTTP-запросов .
Реализует базовые методы
интерфейса HttpBackend:
единичный запрос, итерацию
по записям и страницам,
получение метаданных и
закрытие сессии.• fetch_one(self, *, source: 
SourceConfig, resource: 
ResourceConfig, request: 
ClientRequest, context: 
RequestContext | None = None) -> 
Record | None  – выполняет единичный
HTTP-запрос (GET/POST) для ресурса и
возвращает один результат (JSON)
.<br>• iter_records(self, *, 
source: SourceConfig, resource: 
ResourceConfig, request: 
ClientRequest, context: 
RequestContext | None = None) -> 
Iterator[Record]  – выполняет
запрос(ы) и итеративно возвращает
записи (для ChEMBL объединяет
результаты, напр. для списка activities )
 (в упрощенной реализации может
вернуть первую страницу).<br>• 
iter_pages(...) -> Iterator[Page]
– возвращает итератор по страницам
ответа (заглушка в простой реализации)
.<br>• metadata(self, *, 
source: SourceConfig) -> dict[str, 
object]  – возвращает метаданные
backend (например, тип "requests")
.<br>• close(self) -> None  –
закрывает сессию requests.Session
.—
ClientFactoryRegistry —src/bioetl/pipelines/
client_registry.pyРеестр фабрик клиентов,
используемый в пайплайнах.
Хранит словарь фабрик
(ClientFactory ) по именам
(namespace), например 
"chembl"  для фабрики
клиентов ChEMBL .
Пайплайн Chembl при
инициализации создаёт 
chembl_factory  и регистрирует
её в реестре, после чего может
получать фабрику через 
get("chembl")  и создавать
конкретные клиенты/
дескрипторы для сущностей.• get(self, name: str) -> 
ClientFactory[Any]  – возвращает
фабрику клиента по заданному имени или
выбрасывает исключение, если такая не
зарегистрирована .—108
109 110111
112
113
114
115 116
117
109 118
119 120
121 122
11

Класс Предок Модуль Назначение Публичные методы Приватные методы
TargetNormalizer —src/bioetl/pipelines/chembl/
target/normalizers.pyКласс-шуточная (заглушка) для
нормализации данных target  на
основе контролируемых
словарей (справочников) .
Предполагается для обработки
и стандартизации значений
(например, типов таргетов,
организмов и т.п.) после
извлечения и перед загрузкой,
однако текущая реализация не
заполнена (метод вызывает
NotImplementedError).• normalize(self, df)  – должен
выполнить нормализацию DataFrame
(например, привести типы к строкам,
заполнить пропуски, вычислить бизнес-
ключи, хэши и т.д.), но в текущей заглушке
просто бросает исключение
NotImplementedError .—
run.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
pipelines/chembl/target/run.py
base.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
pipelines/chembl/common/base.py
unified.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
core/pipeline/unified.py
descriptor .py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
pipelines/chembl/common/descriptor .py
strategies.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
pipelines/chembl/common/strategies.py
chembl_extraction_service.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
pipelines/chembl/common/chembl_extraction_service.py
descriptor_factory.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
clients/chembl/descriptor_factory.py
target_schema.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
core/schemas/target_schema.py
defaults.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
core/pipeline/services/defaults.py
output_service.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
core/io/output_service.py123
123 124
1 2 3 4 5 6 7
8 910 11 12 13 14 15 16 17 18 19 20 21 22 23 24 85 86 87 88
25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41
42 43
44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59
60 61 62 63 64 65 66 67 68 69 70 71 72 73 74 75
76 77
78 79
80 81 82 83 84
89 90 91 92 93
12

artifacts.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
core/io/artifacts.py
client.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
clients/chembl/client.py
client.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
clients/uniprot/client.py
factories.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
clients/chembl/factories.py
client_registry.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
pipelines/client_registry.py
normalizers.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
pipelines/chembl/target/normalizers.py94
95 96 97 98 99100 101 102 103
104 105 106 107
108 109 110 111 112 113 114 115 116 117 118
119 120 121 122
123 124
13
```
