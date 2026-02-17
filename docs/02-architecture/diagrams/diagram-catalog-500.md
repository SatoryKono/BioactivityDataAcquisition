# Каталог кандидатов на диаграммы (500)

*Версия: 1.0 | Дата: 2026-02-17*

Каталог содержит 500 кандидатов для поэтапной визуализации архитектуры. Формат записи стандартизирован: **id, тип, уровень, аудитория, цель, сущности**.

## Формат и правила

- `id`: `D###` (трёхзначный идентификатор).
- `тип`: нотация диаграммы (C4/Sequence/Class и т.д.).
- `уровень`: абстракция от контекста до операционного поведения.
- `аудитория`: основной потребитель диаграммы.
- `цель`: краткая формулировка управленческой/технической пользы.
- `сущности`: ключевые классы/компоненты/потоки, подлежащие включению.

## Список кандидатов

| id   | тип          | уровень        | аудитория              | цель                                         | сущности                                              |
| ---- | ------------ | -------------- | ---------------------- | -------------------------------------------- | ----------------------------------------------------- |
| D001 | C4 Context   | L0-Context     | Architecture Board     | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D002 | C4 Container | L1-Container   | Backend Engineers      | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D003 | Component    | L2-Component   | Data Engineers         | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D004 | Sequence     | L3-Code        | QA/Architecture Tests  | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D005 | Activity     | L4-Operational | Onboarding/New Joiners | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D006 | State        | L0-Context     | SRE/Operations         | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D007 | Class        | L1-Container   | Product/Tech Lead      | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D008 | ERD          | L2-Component   | Architecture Board     | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D009 | Flowchart    | L3-Code        | Backend Engineers      | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D010 | Deployment   | L4-Operational | Data Engineers         | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D011 | C4 Context   | L0-Context     | QA/Architecture Tests  | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D012 | C4 Container | L1-Container   | Onboarding/New Joiners | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D013 | Component    | L2-Component   | SRE/Operations         | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D014 | Sequence     | L3-Code        | Product/Tech Lead      | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D015 | Activity     | L4-Operational | Architecture Board     | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D016 | State        | L0-Context     | Backend Engineers      | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D017 | Class        | L1-Container   | Data Engineers         | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D018 | ERD          | L2-Component   | QA/Architecture Tests  | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D019 | Flowchart    | L3-Code        | Onboarding/New Joiners | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D020 | Deployment   | L4-Operational | SRE/Operations         | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D021 | C4 Context   | L0-Context     | Product/Tech Lead      | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D022 | C4 Container | L1-Container   | Architecture Board     | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D023 | Component    | L2-Component   | Backend Engineers      | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D024 | Sequence     | L3-Code        | Data Engineers         | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D025 | Activity     | L4-Operational | QA/Architecture Tests  | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D026 | State        | L0-Context     | Onboarding/New Joiners | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D027 | Class        | L1-Container   | SRE/Operations         | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D028 | ERD          | L2-Component   | Product/Tech Lead      | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D029 | Flowchart    | L3-Code        | Architecture Board     | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D030 | Deployment   | L4-Operational | Backend Engineers      | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D031 | C4 Context   | L0-Context     | Data Engineers         | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D032 | C4 Container | L1-Container   | QA/Architecture Tests  | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D033 | Component    | L2-Component   | Onboarding/New Joiners | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D034 | Sequence     | L3-Code        | SRE/Operations         | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D035 | Activity     | L4-Operational | Product/Tech Lead      | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D036 | State        | L0-Context     | Architecture Board     | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D037 | Class        | L1-Container   | Backend Engineers      | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D038 | ERD          | L2-Component   | Data Engineers         | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D039 | Flowchart    | L3-Code        | QA/Architecture Tests  | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D040 | Deployment   | L4-Operational | Onboarding/New Joiners | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D041 | C4 Context   | L0-Context     | SRE/Operations         | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D042 | C4 Container | L1-Container   | Product/Tech Lead      | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D043 | Component    | L2-Component   | Architecture Board     | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D044 | Sequence     | L3-Code        | Backend Engineers      | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D045 | Activity     | L4-Operational | Data Engineers         | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D046 | State        | L0-Context     | QA/Architecture Tests  | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D047 | Class        | L1-Container   | Onboarding/New Joiners | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D048 | ERD          | L2-Component   | SRE/Operations         | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D049 | Flowchart    | L3-Code        | Product/Tech Lead      | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D050 | Deployment   | L4-Operational | Architecture Board     | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D051 | C4 Context   | L0-Context     | Backend Engineers      | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D052 | C4 Container | L1-Container   | Data Engineers         | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D053 | Component    | L2-Component   | QA/Architecture Tests  | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D054 | Sequence     | L3-Code        | Onboarding/New Joiners | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D055 | Activity     | L4-Operational | SRE/Operations         | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D056 | State        | L0-Context     | Product/Tech Lead      | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D057 | Class        | L1-Container   | Architecture Board     | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D058 | ERD          | L2-Component   | Backend Engineers      | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D059 | Flowchart    | L3-Code        | Data Engineers         | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D060 | Deployment   | L4-Operational | QA/Architecture Tests  | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D061 | C4 Context   | L0-Context     | Onboarding/New Joiners | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D062 | C4 Container | L1-Container   | SRE/Operations         | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D063 | Component    | L2-Component   | Product/Tech Lead      | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D064 | Sequence     | L3-Code        | Architecture Board     | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D065 | Activity     | L4-Operational | Backend Engineers      | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D066 | State        | L0-Context     | Data Engineers         | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D067 | Class        | L1-Container   | QA/Architecture Tests  | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D068 | ERD          | L2-Component   | Onboarding/New Joiners | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D069 | Flowchart    | L3-Code        | SRE/Operations         | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D070 | Deployment   | L4-Operational | Product/Tech Lead      | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D071 | C4 Context   | L0-Context     | Architecture Board     | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D072 | C4 Container | L1-Container   | Backend Engineers      | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D073 | Component    | L2-Component   | Data Engineers         | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D074 | Sequence     | L3-Code        | QA/Architecture Tests  | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D075 | Activity     | L4-Operational | Onboarding/New Joiners | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D076 | State        | L0-Context     | SRE/Operations         | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D077 | Class        | L1-Container   | Product/Tech Lead      | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D078 | ERD          | L2-Component   | Architecture Board     | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D079 | Flowchart    | L3-Code        | Backend Engineers      | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D080 | Deployment   | L4-Operational | Data Engineers         | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D081 | C4 Context   | L0-Context     | QA/Architecture Tests  | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D082 | C4 Container | L1-Container   | Onboarding/New Joiners | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D083 | Component    | L2-Component   | SRE/Operations         | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D084 | Sequence     | L3-Code        | Product/Tech Lead      | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D085 | Activity     | L4-Operational | Architecture Board     | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D086 | State        | L0-Context     | Backend Engineers      | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D087 | Class        | L1-Container   | Data Engineers         | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D088 | ERD          | L2-Component   | QA/Architecture Tests  | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D089 | Flowchart    | L3-Code        | Onboarding/New Joiners | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D090 | Deployment   | L4-Operational | SRE/Operations         | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D091 | C4 Context   | L0-Context     | Product/Tech Lead      | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D092 | C4 Container | L1-Container   | Architecture Board     | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D093 | Component    | L2-Component   | Backend Engineers      | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D094 | Sequence     | L3-Code        | Data Engineers         | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D095 | Activity     | L4-Operational | QA/Architecture Tests  | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D096 | State        | L0-Context     | Onboarding/New Joiners | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D097 | Class        | L1-Container   | SRE/Operations         | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D098 | ERD          | L2-Component   | Product/Tech Lead      | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D099 | Flowchart    | L3-Code        | Architecture Board     | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D100 | Deployment   | L4-Operational | Backend Engineers      | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D101 | C4 Context   | L0-Context     | Data Engineers         | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D102 | C4 Container | L1-Container   | QA/Architecture Tests  | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D103 | Component    | L2-Component   | Onboarding/New Joiners | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D104 | Sequence     | L3-Code        | SRE/Operations         | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D105 | Activity     | L4-Operational | Product/Tech Lead      | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D106 | State        | L0-Context     | Architecture Board     | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D107 | Class        | L1-Container   | Backend Engineers      | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D108 | ERD          | L2-Component   | Data Engineers         | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D109 | Flowchart    | L3-Code        | QA/Architecture Tests  | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D110 | Deployment   | L4-Operational | Onboarding/New Joiners | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D111 | C4 Context   | L0-Context     | SRE/Operations         | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D112 | C4 Container | L1-Container   | Product/Tech Lead      | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D113 | Component    | L2-Component   | Architecture Board     | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D114 | Sequence     | L3-Code        | Backend Engineers      | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D115 | Activity     | L4-Operational | Data Engineers         | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D116 | State        | L0-Context     | QA/Architecture Tests  | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D117 | Class        | L1-Container   | Onboarding/New Joiners | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D118 | ERD          | L2-Component   | SRE/Operations         | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D119 | Flowchart    | L3-Code        | Product/Tech Lead      | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D120 | Deployment   | L4-Operational | Architecture Board     | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D121 | C4 Context   | L0-Context     | Backend Engineers      | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D122 | C4 Container | L1-Container   | Data Engineers         | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D123 | Component    | L2-Component   | QA/Architecture Tests  | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D124 | Sequence     | L3-Code        | Onboarding/New Joiners | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D125 | Activity     | L4-Operational | SRE/Operations         | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D126 | State        | L0-Context     | Product/Tech Lead      | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D127 | Class        | L1-Container   | Architecture Board     | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D128 | ERD          | L2-Component   | Backend Engineers      | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D129 | Flowchart    | L3-Code        | Data Engineers         | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D130 | Deployment   | L4-Operational | QA/Architecture Tests  | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D131 | C4 Context   | L0-Context     | Onboarding/New Joiners | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D132 | C4 Container | L1-Container   | SRE/Operations         | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D133 | Component    | L2-Component   | Product/Tech Lead      | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D134 | Sequence     | L3-Code        | Architecture Board     | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D135 | Activity     | L4-Operational | Backend Engineers      | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D136 | State        | L0-Context     | Data Engineers         | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D137 | Class        | L1-Container   | QA/Architecture Tests  | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D138 | ERD          | L2-Component   | Onboarding/New Joiners | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D139 | Flowchart    | L3-Code        | SRE/Operations         | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D140 | Deployment   | L4-Operational | Product/Tech Lead      | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D141 | C4 Context   | L0-Context     | Architecture Board     | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D142 | C4 Container | L1-Container   | Backend Engineers      | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D143 | Component    | L2-Component   | Data Engineers         | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D144 | Sequence     | L3-Code        | QA/Architecture Tests  | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D145 | Activity     | L4-Operational | Onboarding/New Joiners | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D146 | State        | L0-Context     | SRE/Operations         | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D147 | Class        | L1-Container   | Product/Tech Lead      | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D148 | ERD          | L2-Component   | Architecture Board     | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D149 | Flowchart    | L3-Code        | Backend Engineers      | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D150 | Deployment   | L4-Operational | Data Engineers         | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D151 | C4 Context   | L0-Context     | QA/Architecture Tests  | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D152 | C4 Container | L1-Container   | Onboarding/New Joiners | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D153 | Component    | L2-Component   | SRE/Operations         | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D154 | Sequence     | L3-Code        | Product/Tech Lead      | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D155 | Activity     | L4-Operational | Architecture Board     | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D156 | State        | L0-Context     | Backend Engineers      | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D157 | Class        | L1-Container   | Data Engineers         | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D158 | ERD          | L2-Component   | QA/Architecture Tests  | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D159 | Flowchart    | L3-Code        | Onboarding/New Joiners | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D160 | Deployment   | L4-Operational | SRE/Operations         | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D161 | C4 Context   | L0-Context     | Product/Tech Lead      | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D162 | C4 Container | L1-Container   | Architecture Board     | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D163 | Component    | L2-Component   | Backend Engineers      | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D164 | Sequence     | L3-Code        | Data Engineers         | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D165 | Activity     | L4-Operational | QA/Architecture Tests  | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D166 | State        | L0-Context     | Onboarding/New Joiners | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D167 | Class        | L1-Container   | SRE/Operations         | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D168 | ERD          | L2-Component   | Product/Tech Lead      | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D169 | Flowchart    | L3-Code        | Architecture Board     | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D170 | Deployment   | L4-Operational | Backend Engineers      | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D171 | C4 Context   | L0-Context     | Data Engineers         | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D172 | C4 Container | L1-Container   | QA/Architecture Tests  | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D173 | Component    | L2-Component   | Onboarding/New Joiners | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D174 | Sequence     | L3-Code        | SRE/Operations         | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D175 | Activity     | L4-Operational | Product/Tech Lead      | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D176 | State        | L0-Context     | Architecture Board     | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D177 | Class        | L1-Container   | Backend Engineers      | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D178 | ERD          | L2-Component   | Data Engineers         | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D179 | Flowchart    | L3-Code        | QA/Architecture Tests  | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D180 | Deployment   | L4-Operational | Onboarding/New Joiners | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D181 | C4 Context   | L0-Context     | SRE/Operations         | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D182 | C4 Container | L1-Container   | Product/Tech Lead      | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D183 | Component    | L2-Component   | Architecture Board     | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D184 | Sequence     | L3-Code        | Backend Engineers      | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D185 | Activity     | L4-Operational | Data Engineers         | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D186 | State        | L0-Context     | QA/Architecture Tests  | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D187 | Class        | L1-Container   | Onboarding/New Joiners | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D188 | ERD          | L2-Component   | SRE/Operations         | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D189 | Flowchart    | L3-Code        | Product/Tech Lead      | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D190 | Deployment   | L4-Operational | Architecture Board     | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D191 | C4 Context   | L0-Context     | Backend Engineers      | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D192 | C4 Container | L1-Container   | Data Engineers         | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D193 | Component    | L2-Component   | QA/Architecture Tests  | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D194 | Sequence     | L3-Code        | Onboarding/New Joiners | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D195 | Activity     | L4-Operational | SRE/Operations         | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D196 | State        | L0-Context     | Product/Tech Lead      | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D197 | Class        | L1-Container   | Architecture Board     | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D198 | ERD          | L2-Component   | Backend Engineers      | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D199 | Flowchart    | L3-Code        | Data Engineers         | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D200 | Deployment   | L4-Operational | QA/Architecture Tests  | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D201 | C4 Context   | L0-Context     | Onboarding/New Joiners | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D202 | C4 Container | L1-Container   | SRE/Operations         | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D203 | Component    | L2-Component   | Product/Tech Lead      | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D204 | Sequence     | L3-Code        | Architecture Board     | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D205 | Activity     | L4-Operational | Backend Engineers      | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D206 | State        | L0-Context     | Data Engineers         | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D207 | Class        | L1-Container   | QA/Architecture Tests  | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D208 | ERD          | L2-Component   | Onboarding/New Joiners | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D209 | Flowchart    | L3-Code        | SRE/Operations         | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D210 | Deployment   | L4-Operational | Product/Tech Lead      | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D211 | C4 Context   | L0-Context     | Architecture Board     | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D212 | C4 Container | L1-Container   | Backend Engineers      | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D213 | Component    | L2-Component   | Data Engineers         | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D214 | Sequence     | L3-Code        | QA/Architecture Tests  | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D215 | Activity     | L4-Operational | Onboarding/New Joiners | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D216 | State        | L0-Context     | SRE/Operations         | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D217 | Class        | L1-Container   | Product/Tech Lead      | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D218 | ERD          | L2-Component   | Architecture Board     | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D219 | Flowchart    | L3-Code        | Backend Engineers      | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D220 | Deployment   | L4-Operational | Data Engineers         | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D221 | C4 Context   | L0-Context     | QA/Architecture Tests  | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D222 | C4 Container | L1-Container   | Onboarding/New Joiners | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D223 | Component    | L2-Component   | SRE/Operations         | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D224 | Sequence     | L3-Code        | Product/Tech Lead      | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D225 | Activity     | L4-Operational | Architecture Board     | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D226 | State        | L0-Context     | Backend Engineers      | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D227 | Class        | L1-Container   | Data Engineers         | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D228 | ERD          | L2-Component   | QA/Architecture Tests  | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D229 | Flowchart    | L3-Code        | Onboarding/New Joiners | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D230 | Deployment   | L4-Operational | SRE/Operations         | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D231 | C4 Context   | L0-Context     | Product/Tech Lead      | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D232 | C4 Container | L1-Container   | Architecture Board     | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D233 | Component    | L2-Component   | Backend Engineers      | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D234 | Sequence     | L3-Code        | Data Engineers         | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D235 | Activity     | L4-Operational | QA/Architecture Tests  | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D236 | State        | L0-Context     | Onboarding/New Joiners | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D237 | Class        | L1-Container   | SRE/Operations         | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D238 | ERD          | L2-Component   | Product/Tech Lead      | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D239 | Flowchart    | L3-Code        | Architecture Board     | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D240 | Deployment   | L4-Operational | Backend Engineers      | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D241 | C4 Context   | L0-Context     | Data Engineers         | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D242 | C4 Container | L1-Container   | QA/Architecture Tests  | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D243 | Component    | L2-Component   | Onboarding/New Joiners | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D244 | Sequence     | L3-Code        | SRE/Operations         | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D245 | Activity     | L4-Operational | Product/Tech Lead      | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D246 | State        | L0-Context     | Architecture Board     | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D247 | Class        | L1-Container   | Backend Engineers      | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D248 | ERD          | L2-Component   | Data Engineers         | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D249 | Flowchart    | L3-Code        | QA/Architecture Tests  | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D250 | Deployment   | L4-Operational | Onboarding/New Joiners | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D251 | C4 Context   | L0-Context     | SRE/Operations         | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D252 | C4 Container | L1-Container   | Product/Tech Lead      | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D253 | Component    | L2-Component   | Architecture Board     | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D254 | Sequence     | L3-Code        | Backend Engineers      | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D255 | Activity     | L4-Operational | Data Engineers         | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D256 | State        | L0-Context     | QA/Architecture Tests  | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D257 | Class        | L1-Container   | Onboarding/New Joiners | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D258 | ERD          | L2-Component   | SRE/Operations         | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D259 | Flowchart    | L3-Code        | Product/Tech Lead      | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D260 | Deployment   | L4-Operational | Architecture Board     | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D261 | C4 Context   | L0-Context     | Backend Engineers      | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D262 | C4 Container | L1-Container   | Data Engineers         | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D263 | Component    | L2-Component   | QA/Architecture Tests  | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D264 | Sequence     | L3-Code        | Onboarding/New Joiners | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D265 | Activity     | L4-Operational | SRE/Operations         | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D266 | State        | L0-Context     | Product/Tech Lead      | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D267 | Class        | L1-Container   | Architecture Board     | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D268 | ERD          | L2-Component   | Backend Engineers      | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D269 | Flowchart    | L3-Code        | Data Engineers         | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D270 | Deployment   | L4-Operational | QA/Architecture Tests  | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D271 | C4 Context   | L0-Context     | Onboarding/New Joiners | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D272 | C4 Container | L1-Container   | SRE/Operations         | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D273 | Component    | L2-Component   | Product/Tech Lead      | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D274 | Sequence     | L3-Code        | Architecture Board     | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D275 | Activity     | L4-Operational | Backend Engineers      | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D276 | State        | L0-Context     | Data Engineers         | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D277 | Class        | L1-Container   | QA/Architecture Tests  | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D278 | ERD          | L2-Component   | Onboarding/New Joiners | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D279 | Flowchart    | L3-Code        | SRE/Operations         | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D280 | Deployment   | L4-Operational | Product/Tech Lead      | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D281 | C4 Context   | L0-Context     | Architecture Board     | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D282 | C4 Container | L1-Container   | Backend Engineers      | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D283 | Component    | L2-Component   | Data Engineers         | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D284 | Sequence     | L3-Code        | QA/Architecture Tests  | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D285 | Activity     | L4-Operational | Onboarding/New Joiners | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D286 | State        | L0-Context     | SRE/Operations         | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D287 | Class        | L1-Container   | Product/Tech Lead      | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D288 | ERD          | L2-Component   | Architecture Board     | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D289 | Flowchart    | L3-Code        | Backend Engineers      | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D290 | Deployment   | L4-Operational | Data Engineers         | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D291 | C4 Context   | L0-Context     | QA/Architecture Tests  | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D292 | C4 Container | L1-Container   | Onboarding/New Joiners | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D293 | Component    | L2-Component   | SRE/Operations         | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D294 | Sequence     | L3-Code        | Product/Tech Lead      | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D295 | Activity     | L4-Operational | Architecture Board     | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D296 | State        | L0-Context     | Backend Engineers      | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D297 | Class        | L1-Container   | Data Engineers         | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D298 | ERD          | L2-Component   | QA/Architecture Tests  | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D299 | Flowchart    | L3-Code        | Onboarding/New Joiners | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D300 | Deployment   | L4-Operational | SRE/Operations         | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D301 | C4 Context   | L0-Context     | Product/Tech Lead      | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D302 | C4 Container | L1-Container   | Architecture Board     | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D303 | Component    | L2-Component   | Backend Engineers      | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D304 | Sequence     | L3-Code        | Data Engineers         | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D305 | Activity     | L4-Operational | QA/Architecture Tests  | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D306 | State        | L0-Context     | Onboarding/New Joiners | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D307 | Class        | L1-Container   | SRE/Operations         | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D308 | ERD          | L2-Component   | Product/Tech Lead      | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D309 | Flowchart    | L3-Code        | Architecture Board     | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D310 | Deployment   | L4-Operational | Backend Engineers      | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D311 | C4 Context   | L0-Context     | Data Engineers         | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D312 | C4 Container | L1-Container   | QA/Architecture Tests  | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D313 | Component    | L2-Component   | Onboarding/New Joiners | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D314 | Sequence     | L3-Code        | SRE/Operations         | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D315 | Activity     | L4-Operational | Product/Tech Lead      | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D316 | State        | L0-Context     | Architecture Board     | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D317 | Class        | L1-Container   | Backend Engineers      | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D318 | ERD          | L2-Component   | Data Engineers         | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D319 | Flowchart    | L3-Code        | QA/Architecture Tests  | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D320 | Deployment   | L4-Operational | Onboarding/New Joiners | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D321 | C4 Context   | L0-Context     | SRE/Operations         | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D322 | C4 Container | L1-Container   | Product/Tech Lead      | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D323 | Component    | L2-Component   | Architecture Board     | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D324 | Sequence     | L3-Code        | Backend Engineers      | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D325 | Activity     | L4-Operational | Data Engineers         | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D326 | State        | L0-Context     | QA/Architecture Tests  | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D327 | Class        | L1-Container   | Onboarding/New Joiners | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D328 | ERD          | L2-Component   | SRE/Operations         | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D329 | Flowchart    | L3-Code        | Product/Tech Lead      | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D330 | Deployment   | L4-Operational | Architecture Board     | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D331 | C4 Context   | L0-Context     | Backend Engineers      | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D332 | C4 Container | L1-Container   | Data Engineers         | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D333 | Component    | L2-Component   | QA/Architecture Tests  | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D334 | Sequence     | L3-Code        | Onboarding/New Joiners | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D335 | Activity     | L4-Operational | SRE/Operations         | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D336 | State        | L0-Context     | Product/Tech Lead      | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D337 | Class        | L1-Container   | Architecture Board     | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D338 | ERD          | L2-Component   | Backend Engineers      | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D339 | Flowchart    | L3-Code        | Data Engineers         | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D340 | Deployment   | L4-Operational | QA/Architecture Tests  | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D341 | C4 Context   | L0-Context     | Onboarding/New Joiners | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D342 | C4 Container | L1-Container   | SRE/Operations         | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D343 | Component    | L2-Component   | Product/Tech Lead      | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D344 | Sequence     | L3-Code        | Architecture Board     | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D345 | Activity     | L4-Operational | Backend Engineers      | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D346 | State        | L0-Context     | Data Engineers         | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D347 | Class        | L1-Container   | QA/Architecture Tests  | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D348 | ERD          | L2-Component   | Onboarding/New Joiners | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D349 | Flowchart    | L3-Code        | SRE/Operations         | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D350 | Deployment   | L4-Operational | Product/Tech Lead      | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D351 | C4 Context   | L0-Context     | Architecture Board     | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D352 | C4 Container | L1-Container   | Backend Engineers      | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D353 | Component    | L2-Component   | Data Engineers         | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D354 | Sequence     | L3-Code        | QA/Architecture Tests  | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D355 | Activity     | L4-Operational | Onboarding/New Joiners | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D356 | State        | L0-Context     | SRE/Operations         | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D357 | Class        | L1-Container   | Product/Tech Lead      | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D358 | ERD          | L2-Component   | Architecture Board     | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D359 | Flowchart    | L3-Code        | Backend Engineers      | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D360 | Deployment   | L4-Operational | Data Engineers         | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D361 | C4 Context   | L0-Context     | QA/Architecture Tests  | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D362 | C4 Container | L1-Container   | Onboarding/New Joiners | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D363 | Component    | L2-Component   | SRE/Operations         | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D364 | Sequence     | L3-Code        | Product/Tech Lead      | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D365 | Activity     | L4-Operational | Architecture Board     | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D366 | State        | L0-Context     | Backend Engineers      | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D367 | Class        | L1-Container   | Data Engineers         | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D368 | ERD          | L2-Component   | QA/Architecture Tests  | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D369 | Flowchart    | L3-Code        | Onboarding/New Joiners | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D370 | Deployment   | L4-Operational | SRE/Operations         | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D371 | C4 Context   | L0-Context     | Product/Tech Lead      | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D372 | C4 Container | L1-Container   | Architecture Board     | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D373 | Component    | L2-Component   | Backend Engineers      | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D374 | Sequence     | L3-Code        | Data Engineers         | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D375 | Activity     | L4-Operational | QA/Architecture Tests  | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D376 | State        | L0-Context     | Onboarding/New Joiners | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D377 | Class        | L1-Container   | SRE/Operations         | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D378 | ERD          | L2-Component   | Product/Tech Lead      | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D379 | Flowchart    | L3-Code        | Architecture Board     | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D380 | Deployment   | L4-Operational | Backend Engineers      | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D381 | C4 Context   | L0-Context     | Data Engineers         | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D382 | C4 Container | L1-Container   | QA/Architecture Tests  | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D383 | Component    | L2-Component   | Onboarding/New Joiners | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D384 | Sequence     | L3-Code        | SRE/Operations         | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D385 | Activity     | L4-Operational | Product/Tech Lead      | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D386 | State        | L0-Context     | Architecture Board     | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D387 | Class        | L1-Container   | Backend Engineers      | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D388 | ERD          | L2-Component   | Data Engineers         | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D389 | Flowchart    | L3-Code        | QA/Architecture Tests  | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D390 | Deployment   | L4-Operational | Onboarding/New Joiners | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D391 | C4 Context   | L0-Context     | SRE/Operations         | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D392 | C4 Container | L1-Container   | Product/Tech Lead      | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D393 | Component    | L2-Component   | Architecture Board     | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D394 | Sequence     | L3-Code        | Backend Engineers      | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D395 | Activity     | L4-Operational | Data Engineers         | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D396 | State        | L0-Context     | QA/Architecture Tests  | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D397 | Class        | L1-Container   | Onboarding/New Joiners | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D398 | ERD          | L2-Component   | SRE/Operations         | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D399 | Flowchart    | L3-Code        | Product/Tech Lead      | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D400 | Deployment   | L4-Operational | Architecture Board     | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D401 | C4 Context   | L0-Context     | Backend Engineers      | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D402 | C4 Container | L1-Container   | Data Engineers         | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D403 | Component    | L2-Component   | QA/Architecture Tests  | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D404 | Sequence     | L3-Code        | Onboarding/New Joiners | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D405 | Activity     | L4-Operational | SRE/Operations         | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D406 | State        | L0-Context     | Product/Tech Lead      | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D407 | Class        | L1-Container   | Architecture Board     | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D408 | ERD          | L2-Component   | Backend Engineers      | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D409 | Flowchart    | L3-Code        | Data Engineers         | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D410 | Deployment   | L4-Operational | QA/Architecture Tests  | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D411 | C4 Context   | L0-Context     | Onboarding/New Joiners | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D412 | C4 Container | L1-Container   | SRE/Operations         | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D413 | Component    | L2-Component   | Product/Tech Lead      | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D414 | Sequence     | L3-Code        | Architecture Board     | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D415 | Activity     | L4-Operational | Backend Engineers      | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D416 | State        | L0-Context     | Data Engineers         | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D417 | Class        | L1-Container   | QA/Architecture Tests  | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D418 | ERD          | L2-Component   | Onboarding/New Joiners | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D419 | Flowchart    | L3-Code        | SRE/Operations         | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D420 | Deployment   | L4-Operational | Product/Tech Lead      | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D421 | C4 Context   | L0-Context     | Architecture Board     | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D422 | C4 Container | L1-Container   | Backend Engineers      | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D423 | Component    | L2-Component   | Data Engineers         | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D424 | Sequence     | L3-Code        | QA/Architecture Tests  | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D425 | Activity     | L4-Operational | Onboarding/New Joiners | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D426 | State        | L0-Context     | SRE/Operations         | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D427 | Class        | L1-Container   | Product/Tech Lead      | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D428 | ERD          | L2-Component   | Architecture Board     | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D429 | Flowchart    | L3-Code        | Backend Engineers      | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D430 | Deployment   | L4-Operational | Data Engineers         | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D431 | C4 Context   | L0-Context     | QA/Architecture Tests  | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D432 | C4 Container | L1-Container   | Onboarding/New Joiners | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D433 | Component    | L2-Component   | SRE/Operations         | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D434 | Sequence     | L3-Code        | Product/Tech Lead      | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D435 | Activity     | L4-Operational | Architecture Board     | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D436 | State        | L0-Context     | Backend Engineers      | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D437 | Class        | L1-Container   | Data Engineers         | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D438 | ERD          | L2-Component   | QA/Architecture Tests  | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D439 | Flowchart    | L3-Code        | Onboarding/New Joiners | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D440 | Deployment   | L4-Operational | SRE/Operations         | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D441 | C4 Context   | L0-Context     | Product/Tech Lead      | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D442 | C4 Container | L1-Container   | Architecture Board     | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D443 | Component    | L2-Component   | Backend Engineers      | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D444 | Sequence     | L3-Code        | Data Engineers         | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D445 | Activity     | L4-Operational | QA/Architecture Tests  | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D446 | State        | L0-Context     | Onboarding/New Joiners | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D447 | Class        | L1-Container   | SRE/Operations         | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D448 | ERD          | L2-Component   | Product/Tech Lead      | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D449 | Flowchart    | L3-Code        | Architecture Board     | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D450 | Deployment   | L4-Operational | Backend Engineers      | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D451 | C4 Context   | L0-Context     | Data Engineers         | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D452 | C4 Container | L1-Container   | QA/Architecture Tests  | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D453 | Component    | L2-Component   | Onboarding/New Joiners | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D454 | Sequence     | L3-Code        | SRE/Operations         | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D455 | Activity     | L4-Operational | Product/Tech Lead      | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D456 | State        | L0-Context     | Architecture Board     | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D457 | Class        | L1-Container   | Backend Engineers      | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D458 | ERD          | L2-Component   | Data Engineers         | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D459 | Flowchart    | L3-Code        | QA/Architecture Tests  | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D460 | Deployment   | L4-Operational | Onboarding/New Joiners | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D461 | C4 Context   | L0-Context     | SRE/Operations         | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D462 | C4 Container | L1-Container   | Product/Tech Lead      | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D463 | Component    | L2-Component   | Architecture Board     | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D464 | Sequence     | L3-Code        | Backend Engineers      | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D465 | Activity     | L4-Operational | Data Engineers         | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D466 | State        | L0-Context     | QA/Architecture Tests  | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D467 | Class        | L1-Container   | Onboarding/New Joiners | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D468 | ERD          | L2-Component   | SRE/Operations         | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D469 | Flowchart    | L3-Code        | Product/Tech Lead      | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D470 | Deployment   | L4-Operational | Architecture Board     | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D471 | C4 Context   | L0-Context     | Backend Engineers      | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D472 | C4 Container | L1-Container   | Data Engineers         | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D473 | Component    | L2-Component   | QA/Architecture Tests  | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D474 | Sequence     | L3-Code        | Onboarding/New Joiners | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D475 | Activity     | L4-Operational | SRE/Operations         | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D476 | State        | L0-Context     | Product/Tech Lead      | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D477 | Class        | L1-Container   | Architecture Board     | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D478 | ERD          | L2-Component   | Backend Engineers      | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D479 | Flowchart    | L3-Code        | Data Engineers         | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D480 | Deployment   | L4-Operational | QA/Architecture Tests  | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D481 | C4 Context   | L0-Context     | Onboarding/New Joiners | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D482 | C4 Container | L1-Container   | SRE/Operations         | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D483 | Component    | L2-Component   | Product/Tech Lead      | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D484 | Sequence     | L3-Code        | Architecture Board     | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D485 | Activity     | L4-Operational | Backend Engineers      | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D486 | State        | L0-Context     | Data Engineers         | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D487 | Class        | L1-Container   | QA/Architecture Tests  | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D488 | ERD          | L2-Component   | Onboarding/New Joiners | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D489 | Flowchart    | L3-Code        | SRE/Operations         | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D490 | Deployment   | L4-Operational | Product/Tech Lead      | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
| D491 | C4 Context   | L0-Context     | Architecture Board     | Проверка границ слоёв и правил импортов      | PipelineRunner; BatchExecutor; RecordProcessor        |
| D492 | C4 Container | L1-Container   | Backend Engineers      | Объяснение end-to-end ETL-потока             | MemoryLock; LockService; RuntimeConfig                |
| D493 | Component    | L2-Component   | Data Engineers         | Документация Medallion lifecycle             | BronzeWriter; SilverWriter; GoldWriter                |
| D494 | Sequence     | L3-Code        | QA/Architecture Tests  | Трассировка отказов и retry/circuit breaker  | CircuitBreaker; UnifiedHTTPClient; RateLimiter        |
| D495 | Activity     | L4-Operational | Onboarding/New Joiners | Анализ DQ-порогов и quarantine-потока        | DQConfig; QuarantineEntry; DQMetrics                  |
| D496 | State        | L0-Context     | SRE/Operations         | Навигация по DI composition root             | bootstrap_pipeline; factories; registry               |
| D497 | Class        | L1-Container   | Product/Tech Lead      | Контроль соответствия ADR-010 (local-only)   | domain ports; infrastructure adapters; interfaces CLI |
| D498 | ERD          | L2-Component   | Architecture Board     | Коммуникация архитектурных решений для ревью | Provider adapters (ChEMBL/PubChem/UniProt)            |
| D499 | Flowchart    | L3-Code        | Backend Engineers      | Подготовка к архитектурному аудиту           | HashService; canonical JSON; content hash             |
| D500 | Deployment   | L4-Operational | Data Engineers         | Ускорение onboarding и передачи знаний       | CheckpointPort; StateStore; run_id correlation        |
