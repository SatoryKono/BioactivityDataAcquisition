# Resilience Patterns

- Исходная диаграмма: `mmd-diagrams/architecture/10-resilience-patterns.mmd`

## Описание
Диаграмма Resilience Patterns показывает архитектурный срез BioETL на уровне System / Component и использует нотацию flowchart. Материал помогает понять границы ответственности модулей, точки интеграции и зависимости между компонентами в рамках сценария 10-resilience-patterns. В исходном файле прямо зафиксирован контекст: Circuit Breaker, Rate Limiter, Retry, Health Check patterns.. Это описание задает ожидаемую интерпретацию схемы при техническом ревью и синхронизации документации с кодовой базой. Ключевые контейнеры/подграфы включают: Domain Ports, Circuit Breaker Pattern, State Machine, Rate Limiter (Token Bucket), Provider Rate Limits. Именно через эти блоки визуализированы границы слоев и маршруты передачи управления или данных. Примеры узлов, отражающих доменную модель и инфраструктуру: Domain Ports, CircuitBreakerPort (Protocol) -------- + get_state() + call(fn), RateLimiterPort (Protocol) -------- + acquire(tokens) + try_acquire(), HealthCheckPort (Protocol) -------- + check_health(), Circuit Breaker Pattern, CircuitBreaker -------- provider failure_threshold recovery_timeout. По этим сущностям можно проверить согласованность терминов, портов и адаптеров между диаграммой и реализацией. В метаданных указана оценка плотности (@nodes=15), что полезно для контроля читаемости, декомпозиции view-слоев и стабильного рендеринга в CI-пайплайне.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-24`
