______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Composite Pipeline Workflow Full

- Исходная диаграмма: `views/29-composite-pipeline-workflow-full.mermaid`

## Описание

Эта views-диаграмма Composite Pipeline Workflow Full представляет срез типа full для родительской схемы (root) и использует нотацию unknown. Она нужна для детального анализа выбранного аспекта архитектуры без перегрузки полного графа лишними элементами. В метке view зафиксировано назначение: Full. Такой формат облегчает трассировку связей между full-версией и специализированными представлениями overview/domain/infra/dataflow, что важно для ревью, онбординга и проверки архитектурной консистентности документации. Ключевые блоки этой версии включают: Phase 1: Initialization, Phase 2: Seed Pipeline, Phase 3: Dependencies, Phase 3.5: Key Extraction, Phase 4: Fan-Out Enrichment. Их состав показывает, какие границы ответственности и каналы взаимодействия автор выбрал для текущего аналитического фокуса. Показательные узлы в диаграмме: Phase 1: Initialization, [S] Load CompositeConfig from YAML, [S] CompositePreflightValidationService • validate seed • validate enrichers • check silver tables, [S] bootstrap_composite_runner() → CompositePipelineRunner, Phase 2: Seed Pipeline, [S] Run Seed Pipeline (e.g., chembl_publication). По ним можно проверить корректность терминологии, соответствие имен портов/адаптеров и логичность маршрутов данных или управляющих вызовов. Диаграмма предназначена для практического использования в технических обсуждениях, регрессионной валидации диаграмм и синхронизации с кодовой структурой проекта. Она помогает быстро обнаруживать расхождения между задуманной архитектурой и фактической реализацией компонентов.

## Метаданные

- Тип: `unknown`
- View: `Full`
- Parent: `(root)`
