______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Idempotent Processing Guards

- Исходная диаграмма: `architecture/21-idempotent-processing-guards.mmd`

## Описание

Диаграмма Idempotent Processing Guards показывает runtime-механику безопасного rerun/resume через locks, checkpoint identity и publication guards и использует нотацию sequenceDiagram. Она помогает проверить, что resume policy, ownership validation и checkpoint compatibility образуют единый control-plane контракт, а не набор несвязанных safeguard-механизмов. В исходном файле прямо зафиксирован контекст: how locks, checkpoint identity, and publication guards make reruns/resume safe. Участники диаграммы: LockRuntimeService, LockPort, HeartbeatTask, CompositeCheckpointService, CheckpointLoadService, CheckpointCompatibilityService, PipelineRunner / CompositeRunner, Writers / artifact publication. По этим взаимодействиям можно сверять семантику resume, safe publication под активным lock owner и корректность graceful shutdown против successful finish.

## Метаданные

- Тип: `sequenceDiagram`
- Уровень: `Runtime / Control Plane`
- Дата метаданных: `2026-03-28`
