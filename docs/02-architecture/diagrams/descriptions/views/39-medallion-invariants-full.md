______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Medallion Invariants Full

- Исходная диаграмма: `views/39-medallion-invariants-full.mermaid`

## Описание

Эта views-диаграмма Medallion Invariants Full представляет срез типа full для родительской схемы (root) и использует нотацию unknown. Она нужна для детального анализа выбранного аспекта архитектуры без перегрузки полного графа лишними элементами. В метке view зафиксировано назначение: Full. Такой формат облегчает трассировку связей между full-версией и специализированными представлениями overview/domain/infra/dataflow, что важно для ревью, онбординга и проверки архитектурной консистентности документации. Ключевые блоки этой версии включают: RunType Enum (domain/types.py), MedallionLifecycleService\\n(application/services/medallion_lifecycle.py), INCREMENTAL Path, BACKFILL Path, REBUILD Path. Их состав показывает, какие границы ответственности и каналы взаимодействия автор выбрал для текущего аналитического фокуса. Показательные узлы в диаграмме: RunType Enum (domain/types.py), RunType.INCREMENTAL 'Fetch new data since last run', RunType.BACKFILL 'Re-fetch a date range', RunType.REBUILD 'Full clean rebuild', MedallionLifecycleService\\n(application/services/medallion_lifecycle.py), Check RunType. По ним можно проверить корректность терминологии, соответствие имен портов/адаптеров и логичность маршрутов данных или управляющих вызовов. Диаграмма предназначена для практического использования в технических обсуждениях, регрессионной валидации диаграмм и синхронизации с кодовой структурой проекта. Она помогает быстро обнаруживать расхождения между задуманной архитектурой и фактической реализацией компонентов.

## Метаданные

- Тип: `unknown`
- View: `Full`
- Parent: `(root)`
