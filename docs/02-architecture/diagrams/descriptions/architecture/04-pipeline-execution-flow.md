______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Pipeline Execution Lifecycle

- Исходная диаграмма: `architecture/04-pipeline-execution-flow.mmd`

## Описание

Диаграмма Pipeline Execution Lifecycle показывает архитектурный срез BioETL на уровне System / Component и использует нотацию sequenceDiagram. Материал помогает понять границы ответственности модулей, точки интеграции и зависимости между компонентами в рамках сценария 04-pipeline-execution-flow. В исходном файле прямо зафиксирован контекст: Sequence of phases in a single pipeline run.. Это описание задает ожидаемую интерпретацию схемы при техническом ревью и синхронизации документации с кодовой базой. Важные участники взаимодействий: CLI / Interfaces, Bootstrap, PipelineRunner, PreflightService, LockRuntimeService. Их последовательность полезна для анализа порядка вызовов, мест возможных ошибок и проверки архитектурных контрактов. В метаданных указана оценка плотности (@nodes=12), что полезно для контроля читаемости, декомпозиции view-слоев и стабильного рендеринга в CI-пайплайне.

## Метаданные

- Тип: `sequenceDiagram`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-24`
