# Реестр архитектурных решений (ADR)

**ADR** (Architecture Decision Records) — это документы, фиксирующие значимые архитектурные решения проекта. Каждый ADR описывает контекст, рассмотренные альтернативы и обоснование выбранного подхода.

Все ADR расположены в директории [`docs/02-architecture/decisions/`](https://github.com/SatoryKono/BioactivityDataAcquisition/tree/main/docs/02-architecture/decisions/).

---

## Список ADR

| # | Название | Краткое описание |
|---|---------|-----------------|
| ADR-001 | Delta Lake vs Parquet | Выбор Delta Lake вместо чистого Parquet для ACID-транзакций и schema enforcement |
| ADR-002 | Medallion Architecture | Принятие трёхуровневой медальонной архитектуры (Bronze/Silver/Gold) |
| ADR-003 | In-Memory Locking Strategy | Стратегия блокировок в памяти через MemoryLock для локального развёртывания |
| ADR-004 | Pydantic vs Dataclasses | Выбор Pydantic вместо стандартных dataclasses для валидации конфигураций |
| ADR-005 | Composition Layer Separation | Выделение слоя композиции (DI) как отдельного модуля, а не части Interfaces |
| ADR-006 | Logger & Metrics Ports | Порты для логгера и метрик — абстракция наблюдаемости через Protocol |
| ADR-007 | Circuit Breaker Implementation | Реализация паттерна Circuit Breaker для устойчивости к сбоям внешних API |
| ADR-008 | Graceful Shutdown Strategy | Стратегия корректного завершения работы пайплайнов |
| ADR-009 | PaginatedFetcherMixin Design | Дизайн миксина для пагинированного извлечения данных из API |
| ADR-010 | Local-Only Deployment | Стратегия исключительно локального развёртывания без внешних сервисов |
| ADR-011 | Отказ от механизма Watermark | Удаление механизма водяных знаков (watermark) из пайплайна |
| ADR-012 | Storage Clear Contract & Run ID | Контракт очистки хранилища и консистентность Run ID |
| ADR-013 | Асинхронная очистка хранилища | Асинхронная очистка хранилища в PipelineRunner |
| ADR-014 | Deterministic Writes | Детерминированные записи и повторные попытки для воспроизводимости |
| ADR-015 | Pipeline Services Lifecycle | Управление жизненным циклом сервисов пайплайна |
| ADR-016 | Error Handling Strategy | Стратегия обработки ошибок: классификация, карантин, восстановление |
| ADR-017 | Observability Architecture | Архитектура наблюдаемости: метрики, трассировка, логирование через порты |
| ADR-018 | Строгая валидация Gold-схем | Строгая валидация данных на уровне Gold с дополнительными ограничениями |
| ADR-019 | Observability Port Enforcement | Принудительное использование портов наблюдаемости во всех слоях |
| ADR-020 | Декомпозиция BasePipeline | Разложение BasePipeline на более мелкие компоненты |
| ADR-021 | Внедрение DDD Aggregates | Внедрение паттерна DDD Aggregates в доменный слой |
| ADR-022 | NoOp Tracing | NoOp-трассировка для локального развёртывания без внешних collector |
| ADR-023 | Паттерны передачи entity_type | Паттерны передачи entity_type в трансформерах |
| ADR-024 | Entity Naming Unification | Унификация именования сущностей по всем провайдерам |
| ADR-025 | Pipeline Configuration Unification | Унификация конфигурации пайплайнов |
| ADR-026 | Composite Pipeline Pattern | Паттерн композитного пайплайна для объединения seed и enricher |
| ADR-027 | DQ Rules Externalization | Вынос правил качества данных во внешние YAML-конфигурации |
| ADR-028 | Filter Rules Externalization | Вынос правил фильтрации во внешние YAML-конфигурации |
| ADR-029 | Output Metadata Unification | Унификация метаданных в выходных данных |
| ADR-030 | Publication Pagination Strategy | Стратегия пагинации публикаций (force-full-scan) |
| ADR-031 | Loading Strategy Formalization | Формализация стратегий загрузки данных |
| ADR-032 | Unified HTTP Client Pattern | Унифицированный HTTP-клиент с общим rate limiting, retry и телеметрией |
| ADR-033 | Publication Validation Strategy | Стратегия валидации метаданных публикаций |
| ADR-034 | Schema↔Domain Configuration Pairs | Связывание схем и доменных конфигураций |
| ADR-035 | JSON Field Typing Policy | Политика типизации JSON-полей (Silver ↔ Gold) |
| ADR-036 | Gold Contract Versioning Policy | Политика версионирования Gold-контрактов |
| ADR-037 | Canonical Schema Generation | Канонический источник схем и генерируемые артефакты |
| ADR-038 | ChEMBL Enum Values Externalization | Вынос ChEMBL enum-значений во внешние YAML-файлы |
| ADR-039 | Unified Entity Config Format | Единый формат конфигурации сущностей |
| ADR-040 | Diagram Governance | Управление диаграммами: правила оформления и размещения |
| ADR-041 | Naming Policy for Skills & Agents | Политика именования Skills, Agents и Commands |
| ADR-042 | Testing Strategy Matrix | Матрица стратегии тестирования и управление фикстурами |
| ADR-043 | Documentation & Knowledge Management | Стратегия документации и управления знаниями |
| ADR-044 | Run Manifest & Ledger Control Plane | Плоскость управления: манифесты запусков и append-only реестры |
| ADR-045 | DQ Contract System | Система DQ-контрактов (Data Quality) для порогового контроля качества |

---

## Как читать ADR

Каждый ADR имеет стандартную структуру:

1. **Статус** — Accepted / Superseded / Deprecated
2. **Контекст** — описание проблемы и предпосылок
3. **Решение** — выбранный подход
4. **Последствия** — преимущества и компромиссы
5. **Альтернативы** — рассмотренные, но отвергнутые варианты

---

## Связанные страницы

- [[Архитектура]] — общая архитектура, в которой реализуются решения из ADR
- [[Medallion-архитектура-данных]] — ADR-002
- [[Конфигурация]] — ADR-025, ADR-027, ADR-028, ADR-039
- [[Тестирование]] — ADR-042
