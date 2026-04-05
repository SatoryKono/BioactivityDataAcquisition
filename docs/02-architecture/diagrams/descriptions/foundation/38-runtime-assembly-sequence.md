______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Title: Runtime Assembly Sequence — build_pipeline_runner to PipelineRunner

- Исходная диаграмма: `foundation/38-runtime-assembly-sequence.mmd`

## Описание

Диаграмма Title: Runtime Assembly Sequence — build_pipeline_runner to PipelineRunner из foundation-набора фиксирует актуальный runtime assembly path проекта BioETL после выноса composition wiring в `runner_builder`, `GenericPipelineFactory`, `factory_method_helpers`, `_creation_wiring` и `runner_assembly`. Она представлена в формате sequenceDiagram и служит опорной схемой для ревью изменений в composition/bootstrap/factories runtime path. Уровень детализации обозначен как Component / Class, поэтому схема фокусируется не на общем bootstrap-контексте, а на конкретной цепочке создания `PipelineRunner`: инициализация registry, подготовка runtime inputs, factory-level pipeline creation, service bundle wiring и финальная runner assembly. В комментариях исходника зафиксирован фокус диаграммы: Covers: composition/runtime_builders/runner_builder.py, composition/factories/pipeline/{assembler,factory_method_helpers,\_creation_wiring,runner_assembly}.py, ADR-005. Это помогает держать в синхроне визуальную модель и текущие ownership seams. Значимые участники последовательностей: `build_pipeline_runner`, `PipelineRegistry`, `prepare_runner_inputs()`, `GenericPipelineFactory`, `factory_method_helpers`, `services/bundle.py`, `_creation_wiring.py`, `runner_assembly.py`. По этим участникам удобно валидировать forwarding runtime/settings/observability, config fallback, cached bronze branch и границу между pipeline creation и runner assembly.

## Метаданные

- Тип: `sequenceDiagram`
- Уровень: `Component / Class`
- Дата метаданных: `2026-03-24`
