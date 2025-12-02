# activity_v1.pdf

```text
Класс Предок Модуль Назначение Публичные методы Приватные методы
ChemblActivityPipeline PipelineBasesrc/bioetl/
pipelines/chembl/
activity/run.pyРеализация пайплайна
выгрузки активности из
ChEMBL . Использует
дескриптор для
извлечения данных и
реализует полный цикл
ETL для сущности
“activity”.def extract(self, descriptor: 
ChemblExtractionDescriptor \| 
None, options: 
StageExecutionOptions) -> 
pd.DataFrame <br> def 
transform(self, df: 
pd.DataFrame, options: 
StageExecutionOptions) -> 
pd.DataFrame <br> def 
validate(self, df: 
pd.DataFrame, options: 
StageExecutionOptions) -> 
pd.DataFrame <br> def run(self, 
output_dir: Path, *, run_tag: 
str \| None = None, mode: str 
\| None = None, extended: bool 
= False, dry_run: bool \| None 
= None, sample: int \| None = 
None, limit: int \| None = 
None, include_qc_metrics: bool 
= False, fail_on_schema_drift: 
bool = True) -> 
RunResult <br> def 
save_results(self, df: 
pd.DataFrame, artifacts: 
WriteArtifacts, options: 
StageExecutionOptions) -> 
WriteResult <br> def 
build_pipeline_metadata(self, 
context: StageContextProtocol 
\| None = None) -> 
Mapping[str, Any](нет)
ChemblAssayPipeline PipelineBasesrc/bioetl/
pipelines/chembl/
assay/run.pyКаркас пайплайна для
выгрузки данных об
биоактивности типа
“assay” . Наследует
общий функционал
ChEMBL-пайплайнов и
переопределяет точки
расширения для
специфики assay.def pre_transform(self, df: 
pd.DataFrame) -> 
pd.DataFrame <br> def 
validate(self, df: 
pd.DataFrame, options: 
StageExecutionOptions) -> 
pd.DataFrame <br> def 
save_results(self, df: 
pd.DataFrame, artifacts: 
WriteArtifacts, options: 
StageExecutionOptions) -> 
WriteResult(нет)1
2
1

Класс Предок Модуль Назначение Публичные методы Приватные методы
ChemblTargetPipeline PipelineBasesrc/bioetl/
pipelines/chembl/
target/run.pyКаркас пайплайна для
сущности “target” в
ChEMBL с обогащением
данными UniProt/IUPHAR
. Выполняет
стандартный ETL-процесс
для target, добавляя
проверку на
заполненность
идентификаторов.def validate(self, df: 
pd.DataFrame, options: 
StageExecutionOptions) -> 
pd.DataFrame <br> def 
save_results(self, df: 
pd.DataFrame, artifacts: 
WriteArtifacts, options: 
StageExecutionOptions) -> 
WriteResult(нет)
ChemblDocumentPipeline PipelineBasesrc/bioetl/
pipelines/chembl/
document/run.pyСкелет пайплайна для
сущности “document”
ChEMBL с
дополнительным
обогащением из
внешних источников .
Реализует стандартные
стадии ETL и дополняет
этап преобразования
внешними данными.def domain_enrich(self, df: 
pd.DataFrame) -> 
pd.DataFrame <br> def 
validate(self, df: 
pd.DataFrame, options: 
StageExecutionOptions) -> 
pd.DataFrame <br> def 
save_results(self, df: 
pd.DataFrame, artifacts: 
WriteArtifacts, options: 
StageExecutionOptions) -> 
WriteResult(нет)
TestItemChemblPipeline PipelineBasesrc/bioetl/
pipelines/chembl/
testitem/run.pyСкелет пайплайна
“testitem” для тестовых
веществ, включает
обогащение данными
PubChem . Реализует
ETL конвейер с
кастомной
трансформацией
(обогащение через
PubChem).def pre_transform(self, df: 
pd.DataFrame) -> 
pd.DataFrame <br> def 
transform(self, df: 
pd.DataFrame, options: 
StageExecutionOptions) -> 
pd.DataFrame <br> def 
validate(self, df: 
pd.DataFrame, options: 
StageExecutionOptions) -> 
pd.DataFrame <br> def 
save_results(self, df: 
pd.DataFrame, artifacts: 
WriteArtifacts, options: 
StageExecutionOptions) -> 
WriteResult(нет)
ActivityExtractor StageABCsrc/bioetl/
pipelines/chembl/
activity/stages.pyКласс этапа извлечения
данных активности из
API ChEMBL .
Вызывает клиент ChEMBL
батчами и формирует
результирующий
DataFrame с
метаданными.def extract(self, descriptor: 
ChemblExtractionDescriptor, 
config: PipelineConfig, 
batch_size: int \| None = 
None) -> tuple[pd.DataFrame, 
dict[str, Any]]_build_client(self, config: 
PipelineConfig) -> 
BaseClient <br> _fallback_rows(self, 
ids: list[str], exc: Exception) -> 
pd.DataFrame3
4
5
6
2

Класс Предок Модуль Назначение Публичные методы Приватные методы
ActivityTransformer StageABCsrc/bioetl/
pipelines/chembl/
activity/stages.pyКласс этапа
трансформации для
активности ChEMBL .
Нормализует и
обогащает извлечённые
данные (например,
добавляет номер релиза
ChEMBL).def transform(self, df: 
pd.DataFrame) -> pd.DataFrame_domain_enrich(self, df: 
pd.DataFrame) -> pd.DataFrame
ActivityWriter StageABCsrc/bioetl/
pipelines/chembl/
activity/stages.pyКласс этапа сохранения
результатов пайплайна
активности .
Записывает финальный
набор данных на диск и
генерирует артефакты
контроля качества (QC).def write(self, df: 
pd.DataFrame, artifacts: 
WriteArtifacts, *, run_stem: 
str, output_dir: Path) -> 
WriteResult(нет)
ActivityWriteService WriteServicesrc/bioetl/
pipelines/chembl/
activity/run.pyСервис вывода данных
для пайплайна
активности .
Оборачивает 
ActivityWriter  в
интерфейс 
WriteService  для
совместимости с
оркестрацией.def save(self, df: 
pd.DataFrame, artifacts: 
WriteArtifacts, options: 
StageExecutionOptions, *, 
context: StageContextProtocol, 
runtime: StageRuntimeContext) 
-> WriteResult(нет)
ChemblWriteService WriteServicesrc/bioetl/
pipelines/chembl/
common/base.pyСервис
детерминированной
записи для всех ChEMBL-
пайплайнов .
Выполняет сохранение
основного датасета,
метаданных и отчёта
качества с
единообразным
именованием.def save(self, df: 
pd.DataFrame, artifacts: 
WriteArtifacts, options: 
StageExecutionOptions, *, 
context: StageContextProtocol, 
runtime: StageRuntimeContext) 
-> WriteResult <br> def 
write_metadata(self, 
output_dir: Path, artifacts: 
WriteArtifacts, df: 
pd.DataFrame \| None, *, 
dry_run: bool) -> None(нет)7
8
9
10
3

Класс Предок Модуль Назначение Публичные методы Приватные методы
ConfiguredHttpClient BaseClientsrc/bioetl/
clients/factory.pyБазовая реализация
клиента данных,
настроенного
конфигурацией
источника и HTTP-
бэкендом . Делегирует
выполнение запросов
объекту HttpBackend .def fetch_one(self, request: 
ClientRequest) -> Record \| 
None<br> def 
iter_records(self, request: 
ClientRequest) -> 
Iterator[Record] <br> def 
iter_pages(self, request: 
ClientRequest) -> 
Iterator[Page] <br> def 
metadata(self) -> dict[str, 
object] <br> def close(self) -> 
None(нет)
ChemblClient BaseClientsrc/bioetl/
clients/chembl/
client.pyВысокоуровневый клиент
API ChEMBL,
использующий
унифицированный
контракт. Наследует всю
базовую
функциональность 
BaseClient  через 
ConfiguredHttpClient
, добавляя удобные
методы для запросов
ChEMBL.(нет – использует реализации 
BaseClient  по умолчанию)(нет)
PubMedClient BaseClientsrc/bioetl/
clients/pubmed/
client.pyКлиент для API PubMed
на базе
унифицированного
интерфейса. Наследует 
ConfiguredHttpClient
(то есть BaseClient ) и
предоставляет
фабричный метод
формирования запроса
для статей PubMed .(нет – использует реализации 
BaseClient  по умолчанию)(нет)
CrossrefClient BaseClientsrc/bioetl/
clients/crossref/
client.pyКлиент для API CrossRef,
реализующий общий
контракт клиентов
данных. Наследует
базовую реализацию и
предоставляет метод для
формирования запроса
по рабочим записям
(works) .(нет – использует реализации 
BaseClient  по умолчанию)(нет)11
12
13
14
4

Класс Предок Модуль Назначение Публичные методы Приватные методы
SemanticScholarClient BaseClientsrc/bioetl/
clients/
semantic_scholar/
client.pyКлиент для API Semantic
Scholar , реализованный
на базе BaseClient .
Наследует типовой HTTP-
клиент и определяет
источник ( source) как
“semantic_scholar” .(нет – использует реализации 
BaseClient  по умолчанию)(нет)
PubChemClient BaseClientsrc/bioetl/
clients/pubchem/
client.pyКлиент для PubChem,
предоставляющий доступ
к данным соединений.
Реализован через общий
ConfiguredHttpClient
для унификации работы с
REST API .(нет – использует реализации 
BaseClient  по умолчанию)(нет)
RequestsBackend HttpBackendsrc/bioetl/
clients/chembl/
factories.pyРеализация
транспортного HTTP-
бэкенда с
использованием
библиотеки requests
. Отвечает за
выполнение HTTP-
запросов для клиентов
данных.def fetch_one(self, *, source: 
SourceConfig, resource: 
ResourceConfig, request: 
ClientRequest, context: 
RequestContext \| None = None) 
-> Record \| None <br> def 
iter_records(self, *, source: 
SourceConfig, resource: 
ResourceConfig, request: 
ClientRequest, context: 
RequestContext \| None = None) 
-> Iterator[Record] <br> def 
iter_pages(self, *, source: 
SourceConfig, resource: 
ResourceConfig, request: 
ClientRequest, context: 
RequestContext \| None = None) 
-> Iterator[Page] <br> def 
metadata(self, *, source: 
SourceConfig) -> dict[str, 
object] <br> def close(self) -> 
None(нет)
UnifiedOutputWriterWriterABC
(UnifiedOutputWriter
Protocol)src/bioetl/core/
io/output.pyУнифицированный
писатель вывода данных
пайплайна. Сохраняет
результирующий
DataFrame в CSV или
Parquet, вычисляет хеши
и записывает
метаданные запуска
(манифест, мета-файл)
.def write_dataset_atomic(self, 
df: pd.DataFrame, artifacts: 
RunArtifacts, *, format: 
Literal["csv","parquet"] = 
"csv", output_format: 
Literal["csv","parquet"] \| 
None = None, encoding: str = 
"utf-8", index: bool = False) 
-> WriteResult(нет)15
16
17
1819
5

Класс Предок Модуль Назначение Публичные методы Приватные методы
InMemoryTTLCacheImpl CacheABC (CacheStrategy)src/bioetl/core/
http/cache.pyПотокобезопасный кэш
HTTP-ответов с
истечением (TTL) в
памяти (либо файле) .
Используется для
кэширования
результатов API вызовов
в течение заданного
времени.@staticmethod def 
make_key(method: str, url: 
str, params: Mapping[str, Any] 
\| None, headers: Mapping[str, 
str] \| None) -> str <br> def 
get(self, key: str) -> bytes 
\| 
None<br> def set(self, key: 
str, value: bytes) -> None(нет)
TokenBucketRateLimiterImpl RateLimiterABCsrc/bioetl/core/
http/
rate_limiter.pyРеализация лимитера
частоты запросов с
алгоритмом токен-бакета
. Ограничивает
скорость обращений к
внешним API,
поддерживает
блокирующее и
неблокирующее
получение токена.def try_acquire(self) -> 
bool<br> def acquire(self, *, 
timeout: Optional[float] = 
None) -> bool(нет)
ExponentialBackoffRetryImpl RetryPolicyABCsrc/bioetl/core/
http/retry.pyРеализация стратегии
повторных попыток с
экспоненциальной
задержкой. Вычисляет
интервал перед
следующей попыткой с
учётом случайного
джиттера и
максимального порога
задержки .def compute_backoff(self, 
attempt: int, retry_after: 
float \| None = None) -> 
float(нет)
CircuitBreakerImpl CircuitBreakerStrategyABCsrc/bioetl/core/
http/
circuit_breaker.pyРеализация шаблона
Circuit Breaker для
устойчивости HTTP-
запросов. Отслеживает
число ошибок, открывает
“предохранитель” при
достижении порога и
автоматически
сбрасывается по таймеру
.def before_call(self) -> 
None<br> def 
record_success(self) -> 
None<br> def 
record_failure(self) -> 
None<br> def call(self, func: 
Callable[[], Response]) -> 
Response(нет)20
21
22
2324
6

Класс Предок Модуль Назначение Публичные методы Приватные методы
DefaultPaginationStrategy PaginatorABCsrc/bioetl/core/
http/pagination.pyПростая стратегия
постраничной навигации
по API . Использует
параметр “page” и поле
ответа “next” для
последовательного
получения всех страниц
результатов.def iter_pages(self, 
initial_response: Mapping[str, 
Any] \| Sequence[Mapping[str, 
Any]], transport: 
ApiTransportProtocol, *, 
endpoint: str, params: 
Mapping[str, Any] \| None = 
None, logger: Any \| None = 
None, page_key: str \| None = 
None, next_key: str \| None = 
None, page_param: str \| None 
= None, normalize: Any \| None 
= None) -> 
Iterator[ResponsePayload](нет)
EnvSecretProvider SecretProviderABCsrc/bioetl/core/
config/
config_resolver.pyПровайдер секретов,
основанный на
переменных окружения и
файлах .env .
Обеспечивает доступ к
секретным настройкам
(пароли, ключи) и
переменным окружения
для конфигурации
пайплайна.def get_secret(self, name: 
str) -> str <br> def 
get_variable(self, name: str) 
-> str<br> def 
iter_variables(self) -> 
Mapping[str, str](нет)
FileConfigResolver ConfigResolverABCsrc/bioetl/core/
config/
config_resolver.pyРеализация резолвера
конфигурации
пайплайна из YAML-
файлов . Загружает
основной конфиг и
профильные слоя,
сливает их и применяет
переопределения
окружения и переменных
для получения
окончательного 
PipelineConfig .def resolve(self, profile: str 
\| Path \| None = None, 
overrides: Mapping[str, Any] 
\| None = None) -> 
PipelineConfig(нет)
run.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
pipelines/chembl/activity/run.py
run.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
pipelines/chembl/assay/run.py25
26
27
1 9
2
7

run.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
pipelines/chembl/target/run.py
run.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
pipelines/chembl/document/run.py
run.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
pipelines/chembl/testitem/run.py
stages.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
pipelines/chembl/activity/stages.py
base.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
pipelines/chembl/common/base.py
factory.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
clients/factory.py
client.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
clients/chembl/client.py
client.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
clients/pubmed/client.py
client.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
clients/crossref/client.py
client.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
clients/semantic_scholar/client.py
client.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
clients/pubchem/client.py
factories.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
clients/chembl/factories.py
output.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
core/io/output.py
cache.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
core/http/cache.py
rate_limiter .py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
core/http/rate_limiter .py3
4
5
6 7 8
10
11
12
13
14
15
16
17
18 19
20
21
8

retry.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
core/http/retry.py
circuit_breaker .py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
core/http/circuit_breaker .py
pagination.py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
core/http/pagination.py
config_resolver .py
https://github.com/SatoryKono/bioactivity_data_acquisition/blob/98f17f432532cddd56d0a07fd4796b37c54677ec/src/bioetl/
core/config/config_resolver .py22
23 24
25
26 27
9
```
