______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Exception Hierarchy Full

- Исходная диаграмма: `views/50-exception-hierarchy-full.mermaid`

## Описание

Эта views-диаграмма Exception Hierarchy Full представляет срез типа full для родительской схемы (root) и использует нотацию unknown. Она нужна для детального анализа выбранного аспекта архитектуры без перегрузки полного графа лишними элементами. В метке view зафиксировано назначение: Full. Такой формат облегчает трассировку связей между full-версией и специализированными представлениями overview/domain/infra/dataflow, что важно для ревью, онбординга и проверки архитектурной консистентности документации. Показательные узлы в диаграмме: Exception (Python built-in), BioETLError domain/exceptions/base.py error_type: ErrorType context: dict, CriticalError error_type = CRITICAL Action: ABORT pipeline, RecoverableError error_type = RECOVERABLE Action: RETRY with backoff, DataQualityError error_type = DATA_QUALITY Action: QUARANTINE record, InvalidStateError current_state, attempted_operation. По ним можно проверить корректность терминологии, соответствие имен портов/адаптеров и логичность маршрутов данных или управляющих вызовов. Диаграмма предназначена для практического использования в технических обсуждениях, регрессионной валидации диаграмм и синхронизации с кодовой структурой проекта. Она помогает быстро обнаруживать расхождения между задуманной архитектурой и фактической реализацией компонентов.

## Метаданные

- Тип: `unknown`
- View: `Full`
- Parent: `(root)`
