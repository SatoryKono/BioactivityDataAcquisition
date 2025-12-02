# activity.pdf

```text
1

ChemblActivityPipelineChemblCommonPipeline , 
ChemblPipelineContractbioetl/pipelines/chembl/
activity/run.pyКонкретный ETL-пайплайн для
ChEMBL активности. Реализует
контракт activity_chembl ,
оркестрируя этапы извлечения
данных из API ChEMBL, их
трансформацию, валидацию и
сохранение результатов .__init__(self, config: 
Mapping[str, Any] \| 
PipelineConfig, run_id: str, *, 
client_factory: Callable[[Any], 
BaseClient] \| None = None) -> 
None (настраивает pipeline, клиент,
валидатор и стадии)
<br> build_descriptor(self) -> 
ChemblExtractionDescriptor  (создаёт
дескриптор извлечения на основе
конфигурации)
<br> resolve_chembl_release(self, 
config: Any) -> str \| None
(определяет номер релиза ChEMBL для
запуска) <br> prepare_run(self, 
options: StageExecutionOptions) -> 
None (предварительно настраивает
запуск: дескриптор, детерминизм
сортировки, флаги валидации)
<br> extract(self, descriptor: 
ChemblExtractionDescriptor \| 
None, options: 
StageExecutionOptions) -> 
pd.DataFrame  (вызывает этап
извлечения с данным дескриптором;
накладывает ограничение limit  при
необходимости)
<br> transform(self, df: 
pd.DataFrame, options: 
StageExecutionOptions) -> 
pd.DataFrame  (применяет стадию
трансформации к извлечённым данным)
<br> validate(self, df: 
pd.DataFrame, options: 
StageExecutionOptions) -> 
pd.DataFrame  (выполняет валидацию
данных; в данном пайплайне просто
возвращает входные данные без
изменений) <br> run(self, 
output_dir: Path, *, run_tag: str 
\| None = None, mode: str \| None 
= None, extended: bool = False, 
dry_run: bool \| None = None, 
sample: int \| None = None, limit: 
int \| None = None, 
include_qc_metrics: bool = False, 
fail_on_schema_drift: bool = True) 
-> RunResult  (запускает полный
пайплайн: подготавливает запуск,
выполняет extract/transform/validate,_get_config_metadata(self, config: 
Mapping[str, Any] \| None = None) -> 
ChemblPipelineMetadata  (безопасно извлекает блок
metadata  из конфигурации)
<br> _extract_with_dataclass_descriptor(self, 
descriptor: ChemblExtractionDescriptor, 
options: StageExecutionOptions) -> 
pd.DataFrame  (выполняет извлечение, разбивая на
батчи, возвращает объединённый DataFrame)
<br> run_descriptor_extraction(self, 
descriptor: ChemblExtractionDescriptor, *, 
batch_size: int \| None = None) -> 
tuple[pd.DataFrame, dict]  (вызывает 
extractor.extract , сохраняя релиз и возвращая
данные с метаданными)
<br> _build_schema_registry(self) -> 
SchemaRegistry  (создаёт реестр схем, регистрируя 
ChEMBLActivitySchema  с порядком колонок и
ключевыми полями для детерминизма)123
4
5
6
78
9
1016
1718
1920
2122
2

Класс Предок Модуль Назначение Публичные методы Приватные методы
планирует артефакты, сохраняет
результаты и генерирует QC-отчёты)
<br> save_results(self, df: 
pd.DataFrame, artifacts: 
WriteArtifacts, options: 
StageExecutionOptions) -> 
WriteResult  (сохраняет DataFrame
через унифицированный вывод; при
ошибке — через запасной сервис
записи)
<br> build_pipeline_metadata(self, 
context: StageContextProtocol \| 
None = None) -> Mapping[str, Any]
(формирует метаданные по результатам
выполнения — например, release и
статистику извлечения)
ChemblClient ConfiguredHttpClientbioetl/clients/chembl/
client.pyВысокоуровневый REST-клиент для
ChEMBL API. Наследует
унифицированный HTTP-клиент и
инкапсулирует логику обращения к
ChEMBL (параметры API, сборка
запросов и т.д.) . В частности,
содержит именованный источник 
"chembl"  и генератор запросов 
ChemblRequestBuilder .__init__(self, backend: 
HttpBackend, *, config: 
SourceConfig \| None = None) -> 
None (инициализирует клиент с
конфигурацией источника и HTTP-
бэкендом)
<br> request_activity(self, *, ids: 
Sequence[str] \| None = None, 
filters: Mapping[str, object] \| 
None = None, pagination: 
PaginationParams \| None = None, 
context: RequestContext \| None = 
None) -> ClientRequest
(конструирует ClientRequest  для
маршрута "activity"  с заданными
идентификаторами/фильтрами)(нет дополнительных приватных методов)11
12
1314
15
23
232425
26
3

Класс Предок Модуль Назначение Публичные методы Приватные методы
RequestsBackend HttpBackend  (протокол)bioetl/clients/chembl/
factories.pyРеализация HTTP-бэкенда на базе
библиотеки requests .
Обеспечивает HTTP-вызовы к REST
API ChEMBL, включая получение
одиночного объекта или итерацию
по записям и страницам, а также
закрытие HTTP-сессии .fetch_one(self, *, source: 
SourceConfig, resource: 
ResourceConfig, request: 
ClientRequest, context: 
RequestContext \| None = None) -> 
Record \| None  (выполняет
единичный HTTP-запрос GET на
сформированный URL и возвращает
JSON как запись)
<br> iter_records(self, *, source: 
SourceConfig, resource: 
ResourceConfig, request: 
ClientRequest, context: 
RequestContext \| None = None) -> 
Iterator[Record]  (итерирует по
записям: для ChEMBL реализовано как
один запрос с параметром limit,
возвращающий список результатов)
<br> iter_pages(self, *, source: 
SourceConfig, resource: 
ResourceConfig, request: 
ClientRequest, context: 
RequestContext \| None = None) -> 
Iterator[Page]  (итерирует
постранично – для простоты возвращает
одну пустую страницу, так как пагинация
ChEMBL обрабатывается иначе)
<br> metadata(self, *, source: 
SourceConfig) -> dict[str, 
object]  (возвращает метаданные о
бэкенде, например тип)
<br> close(self) -> None  (закрывает
сессию requests.Session )(нет дополнительных приватных методов)
ChemblRequestBuilder (нет; dataclass )bioetl/clients/chembl/
client.pyКонструктор запросов ChEMBL.
Инкапсулирует объект
конфигурации источника
(SourceConfig ) и на его основе
строит стандартные объекты
запроса ClientRequest  для
различных маршрутов API ChEMBL
.build(self, *, route: str, ids: 
Sequence[str] \| None = None, 
filters: Mapping[str, object] \| 
None = None, pagination: 
PaginationParams \| None = None, 
context: RequestContext \| None = 
None) -> ClientRequest  (формирует
экземпляр ClientRequest  с указанным
маршрутом и параметрами)(нет приватных методов)272829
30
28
31
32
33
3435
35
4

Класс Предок Модуль Назначение Публичные методы Приватные методы
ActivityExtractor (нет; dataclass )bioetl/pipelines/chembl/
activity/stages.pyКласс этапа Extract  для пайплайна
ChEMBL Activity. Отвечает за
извлечение записей активности
через ChemblClient : разбивает
запрос на батчи, вызывает
итерацию по API и формирует
результирующий DataFrame. Также
собирает метаданные (номер
релиза ChEMBL, число API-вызовов,
частичные сбои) .extract(self, descriptor: 
ChemblExtractionDescriptor, 
config: PipelineConfig, 
batch_size: int \| None = None) -> 
tuple[pd.DataFrame, dict[str, 
Any]] (выполняет извлечение данных
активности: определяет размер батча,
получает клиент через _build_client ,
итеративно запрашивает записи из API
ChEMBL и парсит их в DataFrame;
возвращает DataFrame и словарь
метаданных по вызовам)_build_client(self, config: PipelineConfig) -
> BaseClient  (создаёт экземпляр клиента данных
через фабрику client_factory  или бросает
исключение, если фабрика не задана)
<br> _fallback_rows(self, ids: list[str], exc: 
Exception) -> pd.DataFrame  (генерирует
DataFrame-заглушку для указанных ids в случае
критического сбоя извлечения; помечает их как
ошибки с деталями)
ActivityTransformer (нет; dataclass )bioetl/pipelines/chembl/
activity/stages.pyКласс этапа Transform  для ChEMBL
Activity. Выполняет пост-обработку:
нормализует и обогащает данные
активности, например, добавляя
поле релиза ChEMBL и приводя
колонки к нужным типам и
названиям с помощью доменного
нормализатора .transform(self, df: pd.DataFrame) 
-> pd.DataFrame  (трансформирует
извлечённый DataFrame: вызывает
приватный обогащающий метод 
_domain_enrich  для добавления
релиза, затем применяет 
self.normalizer.normalize(...)
для приведения типов/значений
колонок к стандарту)_domain_enrich(self, df: pd.DataFrame) -> 
pd.DataFrame  (добавляет колонку chembl_release
ко всем записям, если релиз известен и ещё не
добавлен)
ActivityWriter (нет; dataclass )bioetl/pipelines/chembl/
activity/stages.pyКласс этапа Load/Write  для ChEMBL
Activity. Отвечает за сохранение
результирующего набора данных
на диск и генерацию артефактов
контроля качества (QC). Использует
унифицированный механизм
записи, записывая основной CSV/
Parquet файл и метаданные
(manifest, отчёт качества и пр.) в
заданную директорию вывода
.write(self, df: pd.DataFrame, 
artifacts: WriteArtifacts, *, 
run_stem: str, output_dir: Path) -
> WriteResult  (реализует стадию
записи: инициализирует 
UnifiedOutputWriter  с реестром схем
и конфигом, оборачивает пути вывода в 
RunArtifacts , атомарно записывает
DataFrame на диск и вызывает
генерацию QC-отчёта; возвращает
результат записи с информацией о
файлах)(нет приватных методов)
ActivityParser (нет)bioetl/pipelines/chembl/
activity/parsers.pyУтилита разбора (parser) ответа
ChEMBL API для активности.
Преобразует сырые данные (JSON
от ChEMBL /activity  endpoint) в
нормализованный pandas
DataFrame с требуемыми
колонками, сопоставляя поля API с
именами колонок доменной схемы
.parse(self, raw_json: Any) -> 
pd.DataFrame  (парсит сырой JSON
payload: извлекает список записей с
помощью 
build_records_from_payload  и
списка маппингов 
_ACTIVITY_MAPPINGS , затем
формирует DataFrame с нужными
колонками)(нет приватных методов)3637
383940
4142
4344
454644
47
48
4950
5152 5352
5

Класс Предок Модуль Назначение Публичные методы Приватные методы
ActivityNormalizer (нет)bioetl/pipelines/chembl/
activity/normalizers.pyУтилита нормализации данных
активности. Оборачивает общий
нормализатор ChEMBL
(BaseChemblNormalizer ) с
настроенными спецификациями
колонок для активности, применяя
его к DataFrame результатов.
Обеспечивает приведение типов,
заполнение значений по
умолчанию и генерацию бизнес-
ключей согласно схеме .normalize(self, df_raw: 
pd.DataFrame) -> pd.DataFrame
(применяет к сырому DataFrame
предварительно созданный 
_ACTIVITY_NORMALIZER , который
выполняет все заявленные
преобразования колонок; возвращает
очищенный и выровненный со схемой
DataFrame)(нет приватных методов)
BaseChemblNormalizer(нет явно; базовый класс для
нормализации ChEMBL)bioetl/clients/chembl
(модуль нормализации
данных)Базовый механизм нормализации
для наборов данных ChEMBL.
Принимает на вход описание
схемы (бизнес-ключ, Pandera-схема,
полный список колонок) и список
спецификаций колонок
(ColumnNormalizationSpec ). На
основе этого способен пройти по
DataFrame и привести каждую
колонку к требуемому типу, задать
значения по умолчанию для
отсутствующих данных, а также
вычислить хэши строк/бизнес-
ключей, если нужно .normalize(self, df: pd.DataFrame) 
-> pd.DataFrame  (выполняет
нормализацию DataFrame согласно
заданным спецификациям колонок:
применяет преобразование типов,
выставляет значения по умолчанию и
возвращает обновлённый DataFrame;
используется конкретными
нормализаторами вроде
ActivityNormalizer) 【отражено косвенно
в использовании】(нет явных приватных методов)
ColumnNormalizationSpec (нет; dataclass )bioetl/clients/chembl
(спецификации колонок)Спецификация нормализации для
одной колонки. Описывает
атрибуты столбца: целевой тип
данных ( dtype), значение по
умолчанию ( default ), а также
опциональную трансформацию
(функцию для преобразования
значений) . Эти объекты
используются 
BaseChemblNormalizer  для
последовательной обработки
каждой колонки.(нет публичных методов – только поля
данных: имя колонки, тип, дефолт,
трансформер)(нет приватных методов)54555655
555756
5758
6

Класс Предок Модуль Назначение Публичные методы Приватные методы
ColumnMapping (нет; dataclass )bioetl/clients/chembl
(утилиты разбора JSON)Структура сопоставления колонок
для парсера. Определяет
соответствие между именем
результирующей колонки и одним
или несколькими путями/ключами
в исходном JSON от ChEMBL.
Например, 
ColumnMapping("activity_id", 
("activity_id", 
"activity_chembl_id"))
означает, что значение для
колонки activity_id  берётся из
поля activity_id  (или
альтернативно 
activity_chembl_id ) в ответе
API . Используется в 
ActivityParser  для построения
записей.(нет публичных методов – только поля:
название колонки и tuple возможных
исходных ключей)(нет приватных методов)
ChemblExtractionDescriptor (нет; dataclass )bioetl/pipelines/chembl/
common/descriptor.pyОписание задачи извлечения
данных из ChEMBL. Хранит
параметры, определяющие, что
извлекать: список
идентификаторов ids (ChEMBL
IDs интересующих объектов) либо
параметры фильтрации, настройки
пагинации ( limit/offset ),
режим выгрузки и т.д. Кроме того,
содержит вложенный BatchPlan
для управления размером батча и
числом чанков при извлечении
. Используется пайплайном для
разбиения работы на части и
логирования целей выгрузки.(нет отдельных публичных методов –
доступ по атрибутам dataclass)__post_init__(self) -> None  (проверяет
корректность поля mode – разрешены только
значения "chembl"  или "all", иначе бросает 
ConfigValidationError )
BatchPlan (нет; dataclass )bioetl/clients/chembl/
descriptor_factory.pyПростая структура для параметров
пакетирования запросов. Содержит
размер батча ( batch_size ) –
число идентификаторов в одном
запросе к API – и размер чанка
(chunk_size ) – количество
батчей, объединяемых в одну
запись результатов. Эти параметры
влияют на стратегию извлечения
данных из API (ограничение в 25 ID
на запрос у ChEMBL) .(нет методов, только поля batch_size
и chunk_size )(нет приватных методов)52
59
6061
6263
7

Класс Предок Модуль Назначение Публичные методы Приватные методы
ChEMBLActivitySchema pandera.pandas.DataFrameSchemabioetl/schemas/
chembl_activity_schema.pyВалидирующая схема Pandera для
данных активности ChEMBL.
Описывает все ожидаемые колонки
итогового DataFrame и их типы
(строка, число, булево и т.д.), а
также отмечает обязательные
поля. Используется для проверки
соответствия выходных данных
ожидаемой структуре и для
настройки детерминизма
сортировки и хэширования ключей
при сохранении .(публичные методы у объекта
DataFrameSchema – например, 
validate(df)  – предоставляются
Pandera; конкретных перегрузок нет)(нет приватных методов)
ActivityArtifactPlanner ArtifactPlannerbioetl/pipelines/chembl/
activity/run.pyСпециализированный
планировщик артефактов для
данного пайплайна. Определяет,
как будут именоваться и
размещаться файлы вывода. В
реализации для активности
формирует поддиректорию с
именем, основанным на run_tag
и mode, и внутри неё задаёт имя
файла данных формата 
activity_<run_stem>.csv  для
основного датасета . Таким
образом обеспечивается
детерминированная структура
каталогов для каждой выгрузки.plan(self, output_dir: Path, 
pipeline_code: str, run_tag: str 
\| None, mode: str \| None) -> 
tuple[Path, WriteArtifacts]
(переопределяет абстрактный метод:
создаёт целевую директорию 
<output_dir>/<run_stem>  и
возвращает путь до неё и объект 
WriteArtifacts  с путём для будущего
CSV-файла)(нет дополнительных приватных методов)
ActivityWriteService WriteServicebioetl/pipelines/chembl/
activity/run.pyСпециализированный сервис
записи результатов для пайплайна
активности. Инкапсулирует 
ActivityWriter  и предоставляет
метод save(), соответствующий
интерфейсу WriteService . В
контексте данного пайплайна
используется для сохранения
данных через ActivityWriter  с
учётом особенностей именования
выходных файлов (префикс 
activity_  и т.д.) .save(self, df: pd.DataFrame, 
artifacts: WriteArtifacts, 
options: StageExecutionOptions, *, 
context: StageContextProtocol, 
runtime: StageRuntimeContext) -> 
WriteResult  (переопределяет метод
базового класса: определяет директорию
вывода, при необходимости формирует
имя файла по шаблону 
activity_<run_stem>.csv , и
вызывает self.writer.write(...)
для непосредственной записи;
возвращает результат записи)(нет дополнительных приватных методов)6465
6667
6869
7071
7273
8

Класс Предок Модуль Назначение Публичные методы Приватные методы
UnifiedOutputWriter (нет) bioetl/core/io/output.pyУнифицированный писатель
вывода данных. Отвечает за
атомарную запись DataFrame на
диск вместе с сопутствующими
файлами метаданных. В частности,
выполняет валидацию DataFrame
по зарегистрированной схеме,
сортирует данные
детерминированно, сохраняет
основный файл ( .csv или
.parquet ) через временный
файл, вычисляет хэш содержимого,
генерирует YAML-файл метаданных
(meta.yaml  с информацией о
выгрузке) и JSON манифест
(run_manifest.json  с хэшами и
размерами), а также инициирует
создание отчёта качества данных
.write_dataset_atomic(self, df: 
pd.DataFrame, artifacts: 
RunArtifacts, *, format: 
Literal["csv", "parquet"] = "csv", 
output_format: Literal["csv", 
"parquet"] \| None = None, 
encoding: str = "utf-8", index: 
bool = False) -> WriteResult
(записывает датасет атомарно:
регистрирует пути для data_path , 
meta_path  и manifest_path  в 
WriteArtifacts , создает директорию,
пишет DataFrame в временный файл и
перемещает как 
<run_stem>.csv /.parquet ,
вычисляет хэш, формирует структуру
метаданных через build_meta_yaml  и 
write_yaml_atomic , рассчитывает
бизнес-ключи/хэш строк, создаёт JSON
манифест с этой информацией,
сохраняет его; возвращает объект 
WriteResult  с числом записей и
путями артефактов)(нет приватных методов; используются внутренние
функции и контекстные менеджеры для атомарной
записи)
DefaultValidationService(нет явно; реализация сервиса
валидации)bioetl/core/pipeline/
servicesСервис валидации данных
пайплайна по схеме. Обёртка
вокруг Pandera-схемы,
используемая для проверки
соответствия DataFrame
ожидаемому формату и для выдачи
пустого DataFrame при
необходимости. В данном
пайплайне применяется,
например, для возвращения
пустого результата, если стратегия
извлечения ничего не вернула,
либо для предупреждения о
дрейфе схемы (может подавлять
исключения схемы) .empty_frame(self) -> pd.DataFrame
(возвращает пустой DataFrame согласно
схеме – со всеми требуемыми
колонками, но без строк; используется
стратегиями извлечения как запасной
результат в случае отсутствия данных)
<br> validate(df: pd.DataFrame) -> 
pd.DataFrame  (валидирует DataFrame с
помощью встроенной Pandera-схемы,
бросает ошибку при несовпадении, либо
предупреждает и возвращает исходный
df, если дрейф схемы разрешён) 
【используется внутри
UnifiedOutputWriter (validate_with_schema)】(нет дополнительных приватных методов)7475
7476
777877
9

Класс Предок Модуль Назначение Публичные методы Приватные методы
SchemaRegistry (нет)bioetl/core/io/
artifacts.pyIn-memory реестр схем данных для
ETL. Хранит набор
зарегистрированных схем (типа
Pandera DataFrameSchema) для
различных кодов пайплайнов,
вместе с сопутствующей
информацией: версией схемы,
эталонным порядком колонок,
настройками детерминизма (поля
сортировки) и ключевыми полями
(business key, row hash). Пайплайн
регистрирует свою итоговую схему
(ChEMBLActivitySchema ) в
реестре, и UnifiedOutputWriter
затем использует эту запись для
валидации и сортировки колонок
перед сохранением .register(self, entry: 
SchemaRegistryEntry) -> None
(регистрирует новую схему в реестре;
если схема с таким идентификатором
уже есть или если column_order
содержит колонки, отсутствующие в
самой схеме, генерирует ошибку)
<br> get(self, identifier: str) -> 
SchemaRegistryEntry  (возвращает
зарегистрированную схему по коду
пайплайна; бросает KeyError , если не
найдена)(нет приватных методов)
run.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
pipelines/chembl/activity/run.py
client.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
clients/chembl/client.py
factories.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
clients/chembl/factories.py
stages.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
pipelines/chembl/activity/stages.py
parsers.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
pipelines/chembl/activity/parsers.py
normalizers.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
pipelines/chembl/activity/normalizers.py
descriptor .py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
pipelines/chembl/common/descriptor .py
chembl_activity_schema.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
schemas/chembl_activity_schema.py79 8081 82
83
1 2 3 4 5 6 7 8 910 11 12 13 14 15 16 17 18 19 20 21 22 66 67 68 69 70 71 72
73
23 24 25 26 34 35
27 28 29 30 31 32 33
36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 62
51 52 53
54 55 56 57 58
59 60 61 63
64 65
10

output.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
core/io/output.py
strategies.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
pipelines/chembl/common/strategies.py
artifacts.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
core/io/artifacts.py74 75 76
77 78
79 80 81 82 83
11
```
