# Каталог Диаграмм BioETL

*Версия: 1.0 | Дата: 2026-01-20*

Комплексный каталог из 500 диаграмм для документирования архитектуры, потоков данных, компонентов и взаимодействий проекта BioETL.

---

## Категория 1: Архитектурные Обзоры (50 диаграмм)

### 1.1 Общая Архитектура (10)
1. **Hexagonal Architecture Overview** - C4 Context - Общий взгляд на Ports & Adapters архитектуру
2. **Five Layer Architecture** - Component - Слои: Domain, Application, Composition, Infrastructure, Interfaces
3. **Layer Dependency Matrix** - Matrix - Матрица разрешённых импортов между слоями
4. **Medallion Architecture Overview** - Flowchart - Bronze → Silver → Gold уровни
5. **DDD Strategic Design** - Context Map - Bounded contexts и их отношения
6. **System Context Diagram** - C4 Context - BioETL в контексте внешних систем
7. **Container Diagram** - C4 Container - Основные контейнеры системы
8. **Deployment Architecture** - Deployment - Local-only deployment модель
9. **Technology Stack** - Component - Все используемые технологии
10. **Architecture Decision Records Map** - Mind Map - 27 ADR и их связи

### 1.2 Domain Layer (10)
11. **Domain Model Overview** - Class - Все entities, value objects, aggregates
12. **Ports Architecture** - Interface - 24 порта и их категории
13. **DDD Aggregates** - Class - PipelineRun, Batch, QuarantineEntry с границами
14. **Domain Services** - Component - DataNormalizationService, IdentityService и др.
15. **Value Objects Hierarchy** - Class - Все value objects и их отношения
16. **Entity Relationships** - ER - Связи между domain entities
17. **Configuration Objects** - Class - PipelineConfig, DQConfig, RuntimeConfig и др.
18. **Domain Events** - Sequence - Event sourcing для aggregates
19. **Invariants Enforcement** - Activity - Как aggregates поддерживают инварианты
20. **Domain Exceptions Hierarchy** - Class - BioETLError и подклассы

### 1.3 Application Layer (10)
21. **Pipeline Core Components** - Component - PipelineRunner, BatchExecutor, RecordProcessor
22. **Pipeline Lifecycle** - State - Состояния выполнения пайплайна
23. **Services Architecture** - Component - 14 application services
24. **Transformer Hierarchy** - Class - BaseTransformer и конкретные реализации
25. **Pipeline Services Bundle** - Component - PipelineServices и его компоненты
26. **Batch Processing Flow** - Activity - Полный цикл обработки батча
27. **Preflight Checklist** - Activity - PreflightService проверки
28. **Postrun Operations** - Activity - PostrunService cleanup
29. **Observability Integration** - Component - PipelineObserver интеграция
30. **Use Cases Overview** - Use Case - Основные use cases системы

### 1.4 Composition Layer (10)
31. **Composition Root** - Component - bootstrap_pipeline() orchestration
32. **Factory Pattern Usage** - Class - 8 фабрик и их ответственности
33. **Bootstrap Functions** - Flowchart - 10 bootstrap функций
34. **Dependency Injection Flow** - Sequence - Как собираются зависимости
35. **Pipeline Registry** - Component - Регистрация 30+ пайплайнов
36. **Provider Registration** - Component - 7 провайдеров
37. **Configuration Builders** - Class - FilterConfigBuilder и др.
38. **Entrypoints Mapping** - Flowchart - CLI → Composition → Application
39. **Services Factory** - Sequence - Создание PipelineServices bundle
40. **Storage Factory** - Sequence - Создание storage adapters

### 1.5 Infrastructure Layer (10)
41. **Infrastructure Components** - Component - Все adapters и implementations
42. **Storage Architecture** - Component - Bronze/Silver/Gold writers
43. **HTTP Infrastructure** - Component - UnifiedHTTPClient и компоненты
44. **Provider Adapters Overview** - Component - 7 провайдеров
45. **Base Adapter Classes** - Class - BaseHttpAdapter, BaseSyncAdapter
46. **Checkpoint & Quarantine** - Component - State persistence
47. **Serialization Layer** - Component - JSON encoding/decoding
48. **Config Loader** - Flowchart - YAML → PipelineConfig
49. **Health Check Infrastructure** - Component - Health monitoring
50. **Metrics Collection** - Component - Prometheus metrics infrastructure

---

## Категория 2: Потоки Данных (60 диаграмм)

### 2.1 End-to-End Data Flow (10)
51. **Complete Pipeline Flow** - Flowchart - От API до Gold layer
52. **Bronze Layer Flow** - Sequence - Fetch → JSONL → Compress → Store
53. **Silver Layer Flow** - Sequence - Transform → Validate → Delta Merge
54. **Gold Layer Flow** - Sequence - Filter → Validate → Delta Write
55. **Incremental Run Flow** - Activity - Checkpoint → Fetch → Process → Write
56. **Backfill Run Flow** - Activity - Clear → Full Fetch → Process
57. **Rebuild Run Flow** - Activity - Exclusive Lock → Clear All → Rebuild
58. **Data Lineage** - Flowchart - Data provenance через слои
59. **Content Hash Calculation** - Activity - SHA256 hashing алгоритм
60. **Medallion Transformation** - Flowchart - Bronze → Silver → Gold трансформации

### 2.2 Provider-Specific Flows (14)
61. **ChEMBL Activity Pipeline** - Sequence - Полный flow для activity
62. **ChEMBL Molecule Pipeline** - Sequence - Molecule fetch → transform → write
63. **ChEMBL Target Pipeline** - Sequence - Target data processing
64. **PubChem Compound Pipeline** - Sequence - PubChem API → Storage
65. **UniProt Protein Pipeline** - Sequence - UniProt fetch → parse → store
66. **CrossRef Publication Pipeline** - Sequence - CrossRef API flow
67. **OpenAlex Work Pipeline** - Sequence - OpenAlex processing
68. **PubMed Article Pipeline** - Sequence - NCBI E-utilities flow
69. **SemanticScholar Pipeline** - Sequence - Semantic Scholar API
70. **ChEMBL Assay Pipeline** - Sequence - Assay data flow
71. **ChEMBL Compound Record Pipeline** - Sequence - Compound records
72. **UniProt ID Mapping** - Sequence - ID mapping transformation
73. **ChEMBL Cell Line Pipeline** - Sequence - Cell line data
74. **ChEMBL Protein Class Pipeline** - Sequence - Protein classification

### 2.3 Transformation Flows (12)
75. **BaseTransformer Template Method** - Activity - Template Method pattern
76. **Entity Mapping** - Activity - DTO → Domain Entity
77. **Data Normalization** - Activity - Text/Value/ID normalization
78. **Unit Conversion** - Activity - Unit converter flow
79. **Activity Aggregation** - Activity - Aggregating multiple activities
80. **Value Validation** - Activity - Molecular weight, activity validation
81. **SMILES Validation** - Activity - Chemical structure validation
82. **Taxonomy ID Resolution** - Activity - NCBI taxonomy lookup
83. **Date Normalization** - Activity - ISO date formatting
84. **PII Hashing** - Activity - Email/identifier hashing
85. **JSON Flattening** - Activity - Nested JSON → Flat schema
86. **Gold Filtering** - Activity - JSON field exclusion

### 2.4 Storage Operations (12)
87. **Bronze Write Operation** - Sequence - JSONL append with metadata
88. **Silver Merge Operation** - Sequence - Delta merge by content_hash
89. **Gold SCD2 Write** - Sequence - Slowly Changing Dimension Type 2
90. **Delta VACUUM** - Activity - Retention и cleanup
91. **Checkpoint Save** - Sequence - State persistence
92. **Checkpoint Load** - Sequence - Resume from checkpoint
93. **Quarantine Write** - Sequence - Failed record isolation
94. **Metadata Write** - Sequence - _metadata.yaml creation
95. **Bronze Archive** - Activity - 90d → Archive flow
96. **Silver Upsert** - Sequence - Insert or Update logic
97. **Gold Overwrite** - Sequence - Full table replacement
98. **Delta Read** - Sequence - Query Delta table

### 2.5 Batch Processing (12)
99. **Batch Creation** - State - Batch lifecycle states
100. **Record Addition** - Activity - add_record() flow
101. **Batch Sealing** - Activity - seal() operation
102. **Batch Writing** - Sequence - Mark writing → Commit
103. **Batch Failure** - Activity - mark_failed() и rollback
104. **Batch Metrics Recording** - Activity - BatchMetricsRecorder
105. **Adaptive Batch Sizing** - Activity - Memory-based sizing
106. **Batch Transformation** - Sequence - BatchTransformer процесс
107. **Quarantine Handling** - Activity - Failed record flow
108. **Batch Validation** - Activity - Pre-write validation
109. **Batch Commit** - Activity - ACID commit операция
110. **Batch Rollback** - Activity - Failure recovery

---

## Категория 3: Паттерны и Механизмы (80 диаграмм)

### 3.1 Design Patterns (15)
111. **Ports & Adapters Pattern** - Component - Hexagonal architecture
112. **Repository Pattern** - Class - Data access abstraction
113. **Factory Pattern** - Class - Object creation
114. **Template Method Pattern** - Class - BaseTransformer
115. **Strategy Pattern** - Class - Write modes, clear policies
116. **Observer Pattern** - Sequence - PipelineObserver
117. **Null Object Pattern** - Class - NoOp implementations
118. **Dependency Injection** - Sequence - Constructor injection
119. **Aggregate Pattern** - Class - DDD aggregates
120. **Value Object Pattern** - Class - Immutable value objects
121. **Service Layer Pattern** - Component - Domain vs Application services
122. **Facade Pattern** - Class - Domain ports facade
123. **Builder Pattern** - Class - Configuration builders
124. **Adapter Pattern** - Class - Provider adapters
125. **Composite Pattern** - Class - Composite pipeline

### 3.2 Error Handling (15)
126. **Error Classification** - Flowchart - Critical/Recoverable/DQ
127. **Retry Mechanism** - Activity - Exponential backoff
128. **Circuit Breaker States** - State - Closed → Open → Half-Open
129. **Circuit Breaker Flow** - Sequence - Error detection → Trip
130. **Error Recovery** - Activity - Retry → Fallback → Fail
131. **Exception Hierarchy** - Class - BioETLError tree
132. **Error Propagation** - Sequence - Layer error handling
133. **DQ Error Handling** - Activity - Soft/Hard threshold
134. **Schema Violation Handling** - Activity - Gold strict validation
135. **Merge Conflict Resolution** - Activity - Silver merge conflicts
136. **Rate Limit Handling** - Sequence - 429 → Backoff → Retry
137. **Timeout Handling** - Activity - Request timeout recovery
138. **Auth Error Handling** - Activity - 401/403 critical errors
139. **Network Error Recovery** - Activity - Connection failures
140. **Graceful Degradation** - Flowchart - Fallback strategies

### 3.3 Observability (15)
141. **Tracing Architecture** - Component - OpenTelemetry integration
142. **Span Hierarchy** - Tree - Parent-child span relationships
143. **Metrics Collection** - Component - Prometheus metrics
144. **Logging Architecture** - Component - Structured logging
145. **DQ Monitoring** - Sequence - DQMonitorPort flow
146. **Health Checks** - Sequence - Component health probes
147. **Pipeline Observer Pattern** - Sequence - Cross-cutting concerns
148. **Metrics Emission** - Activity - Metric recording flow
149. **Log Correlation** - Flowchart - run_id correlation
150. **Trace Context Propagation** - Sequence - Distributed tracing
151. **Alerting Flow** - Flowchart - Metrics → Alerts
152. **Dashboard Data Flow** - Flowchart - Metrics → Dashboards
153. **Audit Trail** - Sequence - AuditPort recording
154. **Performance Monitoring** - Component - Latency tracking
155. **Error Rate Monitoring** - Component - Error metrics

### 3.4 Concurrency & Locking (15)
156. **Lock Acquisition Flow** - Sequence - acquire() → heartbeat → release()
157. **Lock States** - State - Unlocked → Locked → Released
158. **Heartbeat Mechanism** - Sequence - Periodic TTL refresh
159. **Lock Manager** - Component - LockManager orchestration
160. **MemoryLock Implementation** - Class - In-memory locking
161. **Exclusive Lock Flow** - Sequence - Rebuild/backfill locking
162. **Lock Validation** - Activity - Owner validation
163. **Lock TTL Expiration** - Sequence - Auto-release
164. **Concurrent Pipeline Runs** - Sequence - Multiple runs
165. **Lock Contention** - Activity - Wait timeout handling
166. **Graceful Shutdown** - Sequence - SIGTERM → Cleanup → Exit
167. **Shutdown Signal Handling** - Activity - Signal propagation
168. **In-Flight Batch Completion** - Activity - Current batch finish
169. **Checkpoint on Shutdown** - Sequence - Save state before exit
170. **Resource Cleanup** - Activity - aclose() calls

### 3.5 Resilience & Reliability (20)
171. **Rate Limiting** - Activity - Token bucket algorithm
172. **Rate Limiter States** - State - Tokens available/exhausted
173. **Circuit Breaker Logic** - Flowchart - Failure threshold detection
174. **Circuit Breaker Recovery** - Sequence - Half-open probing
175. **Retry Policy** - Flowchart - Max attempts, backoff
176. **Exponential Backoff** - Activity - 2^n backoff calculation
177. **Jitter Addition** - Activity - Random jitter 0.1-0.5s
178. **Health Monitoring** - Sequence - Periodic health checks
179. **Provider Health Check** - Activity - Specific provider probe
180. **Fallback Strategies** - Flowchart - Primary → Fallback
181. **Idempotency** - Activity - Content hash deduplication
182. **ACID Guarantees** - Activity - Delta Lake transactions
183. **Checkpoint Recovery** - Sequence - Resume from last checkpoint
184. **Quarantine Isolation** - Activity - Failed record quarantine
185. **Data Integrity** - Activity - Schema validation
186. **Forensic Retention** - Activity - 7d Delta history
187. **VACUUM Safety** - Activity - Retention period enforcement
188. **Lock Safety** - Activity - Lock-before-write validation
189. **Memory Safety** - Activity - Adaptive batch sizing
190. **Timeout Protection** - Activity - Request timeout enforcement

---

## Категория 4: Компонентные Диаграммы (100 диаграмм)

### 4.1 Domain Components (20)
191. **PipelineRun Aggregate** - Class - Полная структура
192. **Batch Aggregate** - Class - Полная структура
193. **QuarantineEntry Aggregate** - Class - Полная структура
194. **StageResult VO** - Class - Immutable result object
195. **BatchRecord VO** - Class - Record representation
196. **Activity VO** - Class - Activity measurement
197. **DQMetrics VO** - Class - Quality metrics
198. **RunContext VO** - Class - Execution context
199. **CompoundIds VO** - Class - Compound identifiers
200. **TaxonomyId VO** - Class - Taxonomy ID handling
201. **StoragePort Interface** - Interface - Storage contract
202. **DataSourcePort Interface** - Interface - Data fetch contract
203. **LockPort Interface** - Interface - Locking contract
204. **CheckpointPort Interface** - Interface - State persistence
205. **QuarantinePort Interface** - Interface - Quarantine contract
206. **TracingPort Interface** - Interface - Tracing contract
207. **MetricsPort Interface** - Interface - Metrics contract
208. **LoggerPort Interface** - Interface - Logging contract
209. **ValidationConfig** - Class - Validation rules
210. **DQConfig** - Class - DQ configuration

### 4.2 Application Components (20)
211. **PipelineRunner** - Class - Runner structure
212. **BatchExecutor** - Class - Execution loop
213. **RecordProcessor** - Class - Record processing
214. **BatchTransformer** - Class - Transformation logic
215. **BatchWriter** - Class - Write orchestration
216. **BatchMetricsRecorder** - Class - Metrics recording
217. **BaseTransformer** - Class - Abstract transformer
218. **BasePipeline** - Class - Abstract pipeline
219. **LockManager** - Class - Lock orchestration
220. **CheckpointManager** - Class - Checkpoint handling
221. **PipelineServices** - Class - Services bundle
222. **QuarantineManager** - Class - Quarantine management
223. **PreflightService** - Class - Pre-run checks
224. **PostrunService** - Class - Post-run operations
225. **MemoryMonitor** - Class - Memory tracking
226. **Heartbeat** - Class - Lock heartbeat
227. **Shutdown** - Class - Shutdown coordination
228. **MedallionLifecycleService** - Class - Layer lifecycle
229. **DQReportService** - Class - DQ reporting
230. **PipelineObserver** - Class - Observability wrapper

### 4.3 Composition Components (15)
231. **bootstrap_pipeline()** - Sequence - Composition root
232. **bootstrap_observability()** - Sequence - Observability setup
233. **bootstrap_storage()** - Sequence - Storage setup
234. **PipelineFactory** - Class - Pipeline creation
235. **RunnerFactory** - Class - Runner creation
236. **ServicesFactory** - Class - Services creation
237. **StorageFactory** - Class - Storage creation
238. **HTTPClientFactory** - Class - HTTP client creation
239. **DataSourceFactory** - Class - Data source creation
240. **TransformerFactory** - Class - Transformer creation
241. **DQFactory** - Class - DQ analyzer creation
242. **PipelineRegistry** - Class - Registry implementation
243. **FilterConfigBuilder** - Class - Filter building
244. **ConfigurationLoader** - Class - YAML loading
245. **ProviderRegistration** - Sequence - 7 providers

### 4.4 Infrastructure Components (25)
246. **BronzeWriter** - Class - JSONL writer
247. **SilverWriter** - Class - Delta merge writer
248. **GoldWriter** - Class - Validated Delta writer
249. **BaseDeltaWriter** - Class - Common Delta operations
250. **DeltaReader** - Class - Delta table reader
251. **MetadataWriter** - Class - Metadata YAML writer
252. **RetentionManager** - Class - VACUUM manager
253. **UnifiedHTTPClient** - Class - HTTP client
254. **RateLimiter** - Class - Rate limiting
255. **CircuitBreaker** - Class - Circuit breaker
256. **HealthMonitor** - Class - Health checking
257. **Pagination** - Class - Paginated requests
258. **ChemblAdapter** - Class - ChEMBL implementation
259. **PubChemAdapter** - Class - PubChem implementation
260. **UniProtAdapter** - Class - UniProt implementation
261. **CrossRefAdapter** - Class - CrossRef implementation
262. **OpenAlexAdapter** - Class - OpenAlex implementation
263. **PubMedAdapter** - Class - PubMed implementation
264. **SemanticScholarAdapter** - Class - SemanticScholar implementation
265. **BaseHttpAdapter** - Class - Base HTTP adapter
266. **BaseSyncAdapter** - Class - Sync-to-async wrapper
267. **CheckpointAdapter** - Class - Checkpoint storage
268. **QuarantineAdapter** - Class - Quarantine storage
269. **JsonEncoder** - Class - JSON serialization
270. **ConfigLoader** - Class - YAML configuration

### 4.5 Interface Components (20)
271. **CLI Main** - Component - Click CLI structure
272. **Run Command** - Sequence - Single pipeline execution
273. **RunAll Command** - Sequence - Multi-pipeline execution
274. **RunComposite Command** - Sequence - Composite execution
275. **Export Command** - Sequence - Data export
276. **Quarantine Command** - Sequence - Quarantine query
277. **Checkpoint Command** - Sequence - Checkpoint ops
278. **Lock Command** - Sequence - Lock management
279. **Health Command** - Sequence - Health checks
280. **Config Command** - Sequence - Config validation
281. **Maintenance Command** - Sequence - VACUUM/cleanup
282. **Formatters** - Class - Output formatting
283. **ExitCodes** - Class - Exit code definitions
284. **CLI Flow** - Flowchart - User input → execution
285. **Command Routing** - Flowchart - Command dispatch
286. **Error Display** - Activity - User-friendly errors
287. **Progress Display** - Activity - Progress bars
288. **Dry-Run Mode** - Activity - Preview operations
289. **Confirmation Prompts** - Activity - User confirmations
290. **Output Formatting** - Activity - Table/JSON output

---

## Категория 5: Взаимодействия (80 диаграмм)

### 5.1 Layer Interactions (15)
291. **Domain ↔ Application** - Sequence - Port usage
292. **Application ↔ Composition** - Sequence - Factory creation
293. **Composition ↔ Infrastructure** - Sequence - Adapter wiring
294. **Infrastructure ↔ External** - Sequence - API calls
295. **Interfaces → Composition** - Sequence - CLI → Bootstrap
296. **Cross-Layer Communication** - Sequence - Full stack call
297. **Port Implementation** - Sequence - Port → Adapter
298. **Dependency Flow** - Flowchart - Constructor injection chain
299. **Event Propagation** - Sequence - Domain events → Handlers
300. **Error Propagation** - Sequence - Exception bubbling
301. **Configuration Flow** - Sequence - YAML → Config objects
302. **Observability Flow** - Sequence - Tracing/metrics/logging
303. **Data Flow Across Layers** - Sequence - DTO → Entity → VO
304. **Service Coordination** - Sequence - Multiple services interaction
305. **Resource Cleanup** - Sequence - aclose() cascade

### 5.2 Component Interactions (20)
306. **Runner ↔ Executor** - Sequence - Pipeline execution
307. **Executor ↔ Processor** - Sequence - Batch processing
308. **Processor ↔ Transformer** - Sequence - Transformation
309. **Processor ↔ Writer** - Sequence - Storage write
310. **Writer ↔ Storage** - Sequence - Delta operations
311. **Adapter ↔ HTTPClient** - Sequence - API request
312. **HTTPClient ↔ RateLimiter** - Sequence - Rate limiting
313. **HTTPClient ↔ CircuitBreaker** - Sequence - Fault tolerance
314. **LockManager ↔ LockPort** - Sequence - Lock lifecycle
315. **CheckpointManager ↔ CheckpointPort** - Sequence - State persistence
316. **QuarantineManager ↔ QuarantinePort** - Sequence - Quarantine ops
317. **Observer ↔ Services** - Sequence - Observability integration
318. **Preflight ↔ HealthChecks** - Sequence - Pre-run validation
319. **Postrun ↔ DQAnalyzers** - Sequence - DQ analysis
320. **Postrun ↔ VacuumService** - Sequence - Cleanup
321. **MemoryMonitor ↔ BatchExecutor** - Sequence - Adaptive sizing
322. **Heartbeat ↔ LockManager** - Sequence - TTL refresh
323. **Shutdown ↔ Runner** - Sequence - Graceful stop
324. **Factory ↔ Registry** - Sequence - Component creation
325. **CLI ↔ Entrypoints** - Sequence - Command execution

### 5.3 Provider Interactions (14)
326. **ChEMBL API Integration** - Sequence - ChEMBL requests
327. **PubChem API Integration** - Sequence - PubChem requests
328. **UniProt API Integration** - Sequence - UniProt requests
329. **CrossRef API Integration** - Sequence - CrossRef requests
330. **OpenAlex API Integration** - Sequence - OpenAlex requests
331. **PubMed API Integration** - Sequence - NCBI E-utilities
332. **SemanticScholar API Integration** - Sequence - S2 API
333. **ChEMBL Entity Mapping** - Activity - DTO → Entity
334. **PubChem Response Parsing** - Activity - XML/JSON parsing
335. **UniProt FASTA Parsing** - Activity - FASTA format
336. **CrossRef Fallback** - Sequence - Primary → Fallback
337. **PubMed XML Processing** - Activity - XML parsing
338. **Rate Limit Coordination** - Sequence - Multi-provider limits
339. **Health Check Probes** - Sequence - All providers

### 5.4 Storage Interactions (16)
340. **Bronze Write Flow** - Sequence - File system operations
341. **Silver Merge Flow** - Sequence - Delta merge logic
342. **Gold Write Flow** - Sequence - Validated write
343. **Delta Transaction** - Sequence - ACID commit
344. **VACUUM Operation** - Sequence - Delta cleanup
345. **Checkpoint Save Flow** - Sequence - State write
346. **Checkpoint Load Flow** - Sequence - State read
347. **Quarantine Write Flow** - Sequence - Failed record save
348. **Metadata Write Flow** - Sequence - YAML sidecar
349. **Archive Operation** - Sequence - Bronze archival
350. **Content Hash Check** - Sequence - Deduplication
351. **Schema Validation** - Sequence - Pandera validation
352. **Gold Filtering** - Sequence - JSON exclusion
353. **SCD2 Implementation** - Sequence - Type 2 slowly changing
354. **Delta History Query** - Sequence - Time travel
355. **Forensic Retrieval** - Sequence - Historical data access

### 5.5 DQ & Validation (15)
356. **DQ Check Flow** - Sequence - Complete DQ process
357. **Soft Threshold Check** - Activity - 5% warning
358. **Hard Threshold Check** - Activity - 20% failure
359. **Bronze DQ Analysis** - Sequence - Bronze layer DQ
360. **Silver DQ Analysis** - Sequence - Silver layer DQ
361. **Gold DQ Analysis** - Sequence - Gold layer DQ
362. **DQ Report Generation** - Sequence - Report creation
363. **DQ Metrics Emission** - Sequence - Prometheus metrics
364. **Schema Violation Detection** - Activity - Schema mismatch
365. **Field Validation** - Activity - Single field rules
366. **Cross-Field Validation** - Activity - Multi-field rules
367. **Conditional Validation** - Activity - If-then rules
368. **SMILES Validation** - Activity - Chemical validation
369. **Molecular Weight Validation** - Activity - MW range check
370. **Activity Value Validation** - Activity - pChEMBL validation

---

## Категория 6: Состояния и Жизненные Циклы (40 диаграмм)

### 6.1 Aggregate Lifecycles (10)
371. **PipelineRun States** - State - PENDING → RUNNING → COMPLETED/FAILED
372. **PipelineRun Transitions** - State - All state transitions
373. **Batch States** - State - OPEN → SEALED → WRITING → COMMITTED
374. **Batch Lifecycle** - Sequence - Creation → Sealing → Commit
375. **QuarantineEntry States** - State - NEW → UNDER_REVIEW → RESOLVED
376. **QuarantineEntry Lifecycle** - Sequence - Creation → Resolution
377. **StageResult States** - State - SUCCESS/FAILED/SKIPPED
378. **Event Collection** - Sequence - collect_events() flow
379. **Aggregate Immutability** - Activity - State protection
380. **Aggregate Persistence** - Sequence - Event sourcing

### 6.2 Component Lifecycles (15)
381. **Pipeline Lifecycle** - State - Full pipeline states
382. **Lock Lifecycle** - State - Acquire → Heartbeat → Release
383. **Checkpoint Lifecycle** - State - Create → Update → Load
384. **Circuit Breaker Lifecycle** - State - Closed → Open → Half-Open
385. **HTTP Request Lifecycle** - Sequence - Request → Retry → Response
386. **Batch Processing Lifecycle** - Sequence - Create → Process → Write
387. **Record Processing Lifecycle** - Sequence - Fetch → Transform → Write
388. **Transformer Lifecycle** - Sequence - Setup → Transform → Teardown
389. **Writer Lifecycle** - Sequence - Open → Write → Close
390. **Adapter Lifecycle** - Sequence - Initialize → Use → Cleanup
391. **Service Lifecycle** - Sequence - Start → Run → Stop
392. **Observer Lifecycle** - Sequence - Setup → Observe → Report
393. **MemoryMonitor Lifecycle** - Sequence - Initialize → Monitor → Adjust
394. **Heartbeat Lifecycle** - Sequence - Start → Beat → Stop
395. **Shutdown Lifecycle** - Sequence - Signal → Cleanup → Exit

### 6.3 Session & Run Types (15)
396. **Incremental Run** - Flowchart - Resume from checkpoint
397. **Backfill Run** - Flowchart - Historical data load
398. **Rebuild Run** - Flowchart - Full rebuild
399. **Dry-Run Mode** - Flowchart - Preview without writes
400. **Run Type Decision** - Flowchart - Mode selection
401. **Session Initialization** - Sequence - Setup phase
402. **Session Execution** - Sequence - Main execution
403. **Session Termination** - Sequence - Cleanup phase
404. **Multi-Pipeline Session** - Sequence - RunAll execution
405. **Composite Pipeline Session** - Sequence - Composite execution
406. **Export Session** - Sequence - Data export flow
407. **Maintenance Session** - Sequence - VACUUM/cleanup
408. **Health Check Session** - Sequence - Health validation
409. **Quarantine Review Session** - Sequence - Quarantine inspection
410. **Config Validation Session** - Sequence - Config check

---

## Категория 7: Конфигурация и Схемы (30 диаграмм)

### 7.1 Configuration (15)
411. **PipelineConfig Structure** - Class - Complete configuration
412. **RuntimeConfig Structure** - Class - CLI parameters
413. **DQConfig Structure** - Class - DQ thresholds
414. **ValidationConfig Structure** - Class - Validation rules
415. **TableConfig Structure** - Class - Table names/keys
416. **Config Loading Flow** - Sequence - YAML → Objects
417. **Config Validation** - Activity - Config schema validation
418. **Config Overrides** - Flowchart - CLI → ENV → File priority
419. **FilterConfig Building** - Sequence - Filter construction
420. **Default Config** - Activity - Default values
421. **Provider-Specific Config** - Class - Per-provider settings
422. **Entity-Specific Config** - Class - Per-entity settings
423. **DQ Rules Configuration** - Tree - Hierarchical rules
424. **Medallion Policy Config** - Class - Clear/VACUUM policies
425. **Write Mode Config** - Class - Silver/Gold write modes

### 7.2 Schemas (15)
426. **Bronze Schema** - ER - JSONL structure
427. **Silver Schema** - ER - Delta table schema
428. **Gold Schema** - ER - Validated Delta schema
429. **ChEMBL Activity Schema** - Class - Pandera schema
430. **ChEMBL Molecule Schema** - Class - Pandera schema
431. **PubChem Compound Schema** - Class - Pandera schema
432. **UniProt Protein Schema** - Class - Pandera schema
433. **CrossRef Publication Schema** - Class - Pandera schema
434. **Metadata Schema** - Class - _metadata.yaml structure
435. **Checkpoint Schema** - Class - Checkpoint JSON structure
436. **Quarantine Schema** - Class - Quarantine entry schema
437. **DQ Report Schema** - Class - DQ report structure
438. **Audit Schema** - Class - Audit trail schema
439. **Schema Evolution** - Flowchart - Schema versioning
440. **Schema Validation Flow** - Sequence - Pandera validation

---

## Категория 8: Provider-Specific (70 диаграмм)

### 8.1 ChEMBL (15)
441. **ChEMBL Adapter Architecture** - Component - Full adapter
442. **ChEMBL Entity Mapper** - Class - Entity mapping
443. **ChEMBL Activity Flow** - Sequence - Activity pipeline
444. **ChEMBL Molecule Flow** - Sequence - Molecule pipeline
445. **ChEMBL Target Flow** - Sequence - Target pipeline
446. **ChEMBL Assay Flow** - Sequence - Assay pipeline
447. **ChEMBL DTO Models** - Class - All DTO classes
448. **ChEMBL Health Check** - Sequence - Status endpoint
449. **ChEMBL Pagination** - Sequence - Paginated fetch
450. **ChEMBL Error Handling** - Flowchart - Error classification
451. **ChEMBL Rate Limiting** - Activity - No rate limit
452. **ChEMBL Response Parsing** - Activity - JSON parsing
453. **ChEMBL Transform Logic** - Activity - Activity transform
454. **ChEMBL Compound Record** - Sequence - Compound flow
455. **ChEMBL Cell Line** - Sequence - Cell line flow

### 8.2 PubChem (10)
456. **PubChem Adapter Architecture** - Component - Full adapter
457. **PubChem Entity Mapper** - Class - Entity mapping
458. **PubChem Compound Flow** - Sequence - Compound pipeline
459. **PubChem Fetch Strategies** - Class - Multiple strategies
460. **PubChem Health Check** - Sequence - Lightweight query
461. **PubChem Rate Limiting** - Activity - 5 req/sec
462. **PubChem Response Parsing** - Activity - XML/JSON parsing
463. **PubChem Transform Logic** - Activity - Compound transform
464. **PubChem Error Handling** - Flowchart - Error classification
465. **PubChem Pagination** - Sequence - Batch fetching

### 8.3 UniProt (10)
466. **UniProt Adapter Architecture** - Component - Full adapter
467. **UniProt Entity Mapper** - Class - Entity mapping
468. **UniProt Protein Flow** - Sequence - Protein pipeline
469. **UniProt ID Mapping Flow** - Sequence - ID mapping
470. **UniProt FASTA Parsing** - Activity - FASTA format
471. **UniProt Health Check** - Sequence - Search probe
472. **UniProt Rate Limiting** - Activity - 100 req/sec
473. **UniProt Response Parsing** - Activity - TSV/FASTA parsing
474. **UniProt Transform Logic** - Activity - Protein transform
475. **UniProt Error Handling** - Flowchart - Error classification

### 8.4 CrossRef (10)
476. **CrossRef Adapter Architecture** - Component - Full adapter
477. **CrossRef Entity Mapper** - Class - Entity mapping
478. **CrossRef Publication Flow** - Sequence - Publication pipeline
479. **CrossRef Fallback Strategy** - Sequence - Primary → Fallback
480. **CrossRef Health Check** - Sequence - Works endpoint
481. **CrossRef Rate Limiting** - Activity - Polite pool
482. **CrossRef Response Parsing** - Activity - JSON parsing
483. **CrossRef Transform Logic** - Activity - Publication transform
484. **CrossRef Error Handling** - Flowchart - Error classification
485. **CrossRef Pagination** - Sequence - Cursor-based pagination

### 8.5 OpenAlex (5)
486. **OpenAlex Adapter Architecture** - Component - Full adapter
487. **OpenAlex Entity Mapper** - Class - Entity mapping
488. **OpenAlex Work Flow** - Sequence - Work pipeline
489. **OpenAlex Rate Limiting** - Activity - 10 req/sec
490. **OpenAlex Transform Logic** - Activity - Work transform

### 8.6 PubMed (10)
491. **PubMed Adapter Architecture** - Component - Full adapter
492. **PubMed Entity Mapper** - Class - Entity mapping
493. **PubMed Article Flow** - Sequence - Article pipeline
494. **PubMed XML Processing** - Activity - XML parsing
495. **PubMed E-utilities Flow** - Sequence - NCBI API
496. **PubMed Health Check** - Sequence - EInfo endpoint
497. **PubMed Rate Limiting** - Activity - 3 req/sec
498. **PubMed Response Parsing** - Activity - XML to entity
499. **PubMed Transform Logic** - Activity - Article transform
500. **PubMed Error Handling** - Flowchart - Error classification

---

## Приоритизация для Выбора TOP-50

Каждая диаграмма будет оценена по критериям:

1. **Архитектурная важность** (1-10): Насколько критична для понимания архитектуры
2. **Документационная ценность** (1-10): Полезность для новых разработчиков
3. **Частота использования** (1-10): Как часто нужна при работе с проектом
4. **Сложность без диаграммы** (1-10): Насколько сложно понять без визуализации
5. **Охват кодовой базы** (1-10): Сколько компонентов покрывает

**Формула приоритета**: `(Arch * 2 + Doc * 1.5 + Freq * 1.5 + Complex * 2 + Coverage * 1) / 8`

---

*Следующий шаг: Оценка и выбор TOP-50 диаграмм*
