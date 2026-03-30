---
Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-03-29'
---

# Title: Composite Pipeline Phase Lifecycle (FSM)

- Исходная диаграмма: `foundation/48-composite-phase-lifecycle.mmd`

## Описание
Диаграмма Title: Composite Pipeline Phase Lifecycle (FSM) из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате stateDiagram и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 48-composite-phase-lifecycle. В комментариях исходника зафиксирован фокус диаграммы: Covers: domain/composite/state.py, application/composite/fsm_helper.py. Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `stateDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`
