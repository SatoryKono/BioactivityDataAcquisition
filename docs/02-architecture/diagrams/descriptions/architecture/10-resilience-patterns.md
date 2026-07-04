______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Resilience Patterns

- Исходная диаграмма: `architecture/10-resilience-patterns.mmd`

## Описание

Диаграмма Resilience Patterns показывает архитектурный срез BioETL на уровне System / Component и использует нотацию flowchart. Материал помогает понять границы ответственности модулей, точки интеграции и зависимости между компонентами в рамках сценария 10-resilience-patterns. В исходном файле прямо зафиксирован контекст: Circuit Breaker, Rate Limiter, Retry, Health Check patterns.

**Это описание задает ожидаемую интерпретацию схемы при техническом ревью и синхронизации документации с кодовой базой.**

**Ключевые контейнеры/подграфы:**

- **Domain Ports**: Интерфейсы (protocols) для инверсии зависимостей — CircuitBreakerPort, RateLimiterPort, HealthCheckPort
- **Circuit Breaker Pattern**: Трёхсостояние finite state machine (CLOSED → OPEN → HALF_OPEN) для защиты от каскадных сбоев
- **State Machine**: Визуализирует переходы состояний (failure threshold → OPEN, recovery timeout → HALF_OPEN, success → CLOSED)
- **Rate Limiter (Token Bucket)**: Контроль нагрузки на внешние сервисы через квоты (ChEMBL: 5 req/s, UniProt: 100 req/s и т.д.)
- **Retry Logic**: Экспоненциальная задержка + jitter для переполняемых запросов

**Data Source Decorators** (в нижней части диаграммы):

- **CircuitBreakerDataSourceDecorator**: Оборачивает DataSourcePort, добавляя защиту от cascading failures
- **RetryingDataSourceDecorator**: Оборачивает DataSourcePort, добавляя retry logic с exponential backoff. Использует delegation pattern с private aliases (\_data_source, \_retry_config, \_logger, \_metrics) для compliance с архитектурными правилами NAME-004

Оба декоратора — composable и применяются к любой реализации DataSourcePort (ChEMBL, PubMed, UniProt и т.д.).

**Примеры узлов**, отражающих доменную модель и инфраструктуру: Domain Ports, CircuitBreakerPort (Protocol) -------- + get_state() + call(fn), RateLimiterPort (Protocol) -------- + acquire(tokens) + try_acquire(), HealthCheckPort (Protocol) -------- + check_health(), Circuit Breaker Pattern, CircuitBreaker -------- provider failure_threshold recovery_timeout.

По этим сущностям можно проверить согласованность терминов, портов и адаптеров между диаграммой и реализацией. В метаданных указана оценка плотности (@nodes=15), что полезно для контроля читаемости, декомпозиции view-слоев и стабильного рендеринга в CI-пайплайне.

## Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-03-08` (обновлено: расширено описание Data Source Decorators и delegation pattern)
- Связь: Детализирует архитектуру decorators из class diagram 10-adapters
