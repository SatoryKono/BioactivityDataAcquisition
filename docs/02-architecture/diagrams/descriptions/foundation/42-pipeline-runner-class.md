______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Title: PipelineRunner Collaborator Diagram

- Исходная диаграмма: `foundation/42-pipeline-runner-class.mmd`

## Описание

Диаграмма Title: PipelineRunner Collaborator Diagram показывает актуальную модель `PipelineRunner` после перехода на grouped dependency contract `PipelineRunnerDependencies` и выделенные lifecycle/preflight/postrun collaborators. Она представлена в формате classDiagram и используется как компактная foundation-view для ревью изменений вокруг `application/core/runner.py`, `application/core/pipeline_services.py` и assembly-path из `composition/factories/pipeline/runner_assembly.py`. Уровень детализации обозначен как Component / Class, поэтому схема сфокусирована на инжектируемых зависимостях и orchestration seams, а не на полном внутреннем поведении всех downstream services. Ключевые элементы здесь: `PipelineRunner`, `PipelineRunnerDependencies`, `PipelineService`, `BatchExecutor`, `LockRuntimeService`, `PreflightService`, `PostrunService`, `MedallionLifecycleService`, `PipelineObserver`, `ShutdownSignal`. По этой схеме удобно проверять, что `PipelineRunner` не тянет лишние инфраструктурные детали напрямую и работает через заранее собранные collaborators.

## Метаданные

- Тип: `classDiagram`
- Уровень: `Component / Class`
- Дата метаданных: `2026-03-24`
