______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Title: Exception Hierarchy — Full Tree

- Исходная диаграмма: `foundation/50-exception-hierarchy.mmd`

## Описание

Диаграмма Title: Exception Hierarchy — Full Tree из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате flowchart и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 50-exception-hierarchy. В комментариях исходника зафиксирован фокус диаграммы: Covers: domain/exceptions/ (base, network, validation, internal, infrastructure, data_quality). Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Показательные узлы диаграммы: Exception (Python built-in), BioETLError domain/exceptions/base.py error_type: ErrorType context: dict, CriticalError error_type = CRITICAL Action: ABORT pipeline, RecoverableError error_type = RECOVERABLE Action: RETRY with backoff, DataQualityError error_type = DATA_QUALITY Action: QUARANTINE record, InvalidStateError current_state, attempted_operation. Они позволяют быстро сопоставлять термины, роли сервисов и артефакты данных между моделью и реализацией. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные

- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`
