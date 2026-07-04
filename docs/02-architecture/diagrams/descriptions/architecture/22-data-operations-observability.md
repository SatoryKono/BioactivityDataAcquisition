______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Data Operations Observability

- Исходная диаграмма: `architecture/22-data-operations-observability.mmd`

## Описание

Диаграмма Data Operations Observability показывает, как logs, metrics, tracing и control-plane signals остаются коррелированными без high-cardinality metric labels, и использует нотацию flowchart. Она нужна для проверки observability contract между runtime producers, application observability ports, infrastructure adapters и monitoring/diagnosis surface. В исходном файле прямо зафиксирован контекст: how logs, metrics, tracing, and control-plane signals stay correlated without high-cardinality metric labels. Ключевые подграфы: Runtime event producers, Application observability contracts, Infrastructure observability, Published signals, Monitoring and diagnosis. Показательные узлы: PipelineObserver, LoggerPort, MetricsPort, TracingPort, UnifiedLogger / structlog, Prometheus scrape. Через них можно сверять low-cardinality policy, run-level correlation anchors и точку стыка между runtime events и operational drill-down tooling.

## Метаданные

- Тип: `flowchart`
- Уровень: `System / Runtime`
- Дата метаданных: `2026-03-28`
