______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Title: CLI Entry Point to Pipeline Execution Full Chain

- Исходная диаграмма: `foundation/37-cli-entry-full-chain.mmd`

## Описание

Диаграмма Title: CLI Entry Point to Pipeline Execution Full Chain показывает актуальный путь от `click`-команды до финального exit code после выделения `CliRunOrchestrationService`, policy-level `run_command_flow()`, runtime helper’ов и `PipelineRunnerService`. Она представлена в формате `flowchart` и служит опорной foundation-view для понимания того, как CLI normalization, destructive-policy, prepared execution, composition runtime build и `PipelineRunner.run()` связываются в один наблюдаемый execution chain.

Ключевые узлы здесь: `build_run_command_input()`, `run_command_flow()`, `CliRunOrchestrationService.prepare_execution_request()`, `CliRunOrchestrationService.execute_pipeline()`, `run_pipeline_async()`, `get_pipeline_runner_service()`, `build_pipeline_runner()`, `PipelineRunnerService.run()`, `PipelineRunExecutionService.execute()`, `PipelineRunner.run()`, `RunResult`, `_finalize_run_result()`. По этой схеме удобно проверять, что CLI больше не выглядит как прямой вызов в bootstrap, а проходит через явный policy и service orchestration path.

## Метаданные

- Тип: `flowchart`
- Уровень: `Component / Class`
- Дата метаданных: `2026-03-24`
