______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Application Layer Class Diagram Infra

- Исходная диаграмма: `views/06-application-layer-class-diagram-infra.mermaid`

## Описание

Эта views-диаграмма Application Layer Class Diagram Infra представляет срез типа infra для родительской схемы `06-application-layer-class-diagram-full.mermaid` и использует нотацию `flowchart`. Она показывает runner-side orchestration и его support collaborators: `PipelineRunner`, `RunnerDependencies`, `PipelineService`, `LockCoordinator`, `CheckpointRuntimeService`, `PreflightService`, `PostrunService`, `MedallionLifecycleService`, `PipelineObserver`, `BatchExecutor`, `BatchTracingManagerService`, `BatchMetricsRecorderService`.

По этой схеме удобно проверять, как application runtime стыкуется с lifecycle и observability seams, не смешивая это с transform logic. Важно и то, что view уже не опирается на старые `RecordProcessor` / `PipelineExecutor`, а отражает текущую dependency shape вокруг `PipelineRunner` и `RunnerDependencies`.

## Метаданные

- Тип: `flowchart`
- View: `Infrastructure-Mapping`
- Parent: `06-application-layer-class-diagram-full.mermaid`
