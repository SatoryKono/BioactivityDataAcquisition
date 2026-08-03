______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Observability Stack

- Исходная диаграмма: `architecture/09-observability-stack.mmd`

## Описание

Диаграмма Observability Stack показывает архитектурный срез BioETL на уровне System / Component и использует нотацию flowchart. Материал помогает понять границы ответственности модулей, точки интеграции и зависимости между компонентами в рамках сценария 09-observability-stack. В исходном файле прямо зафиксирован контекст: Logging, Metrics, Tracing architecture.. Это описание задает ожидаемую интерпретацию схемы при техническом ревью и синхронизации документации с кодовой базой. Ключевые контейнеры/подграфы включают: Domain Ports, Application Observability, Infrastructure: Logging, Infrastructure: Metrics, Infrastructure: Tracing. Именно через эти блоки визуализированы границы слоев и маршруты передачи управления или данных. Примеры узлов, отражающих доменную модель и инфраструктуру: Domain Ports, LoggerPort (Protocol) ━━━━━━━━━━━━━━━━━ + bind(\*\*kwargs) + info(msg, \*\*fields) + warning(msg, \*\*fields) + error(msg, \*\*fields) + debug(msg, \*\*fields) + exception(msg, \*\*fields), MetricsPort (Protocol) ━━━━━━━━━━━━━━━━━ + observe_histogram(name, value, labels) + increment_counter(name, labels) + set_gauge(name, value, labels) + close(), TracingPort (Protocol) ━━━━━━━━━━━━━━━━━ + get_tracer(name) → Tracer + close(), DQMonitorPort (Protocol) ━━━━━━━━━━━━━━━━━ + add_metric(name, value) + check_quality() + update_baseline_from_metrics(), Application Observability. По этим сущностям можно проверить согласованность терминов, портов и адаптеров между диаграммой и реализацией. В метаданных указана оценка плотности (@nodes=24), что полезно для контроля читаемости, декомпозиции view-слоев и стабильного рендеринга в CI-пайплайне.

## Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-24`
