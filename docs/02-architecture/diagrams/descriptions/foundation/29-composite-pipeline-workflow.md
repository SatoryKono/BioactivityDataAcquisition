---
Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-03-29'
---

# Title: Composite Pipeline Full Workflow — Seed to Gold (ADR-026)

- Исходная диаграмма: `foundation/29-composite-pipeline-workflow.mmd`

## Описание
Диаграмма Title: Composite Pipeline Full Workflow — Seed to Gold (ADR-026) из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате flowchart и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 29-composite-pipeline-workflow. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §2.10 (Composite Pipelines), ADR-026. Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Ключевые блоки/подграфы включают: Phase 1: Initialization, Phase 2: Seed Pipeline, Phase 3: Dependencies, Phase 3.5: Key Extraction, Phase 4: Fan-Out Enrichment. Их состав отражает главные границы ответственности и маршруты взаимодействия между подсистемами или слоями. Показательные узлы диаграммы: Phase 1: Initialization, [S] Load CompositeConfig from YAML, [S] CompositePreflightValidator • validate seed • validate enrichers • check silver tables, [S] bootstrap_composite_runner() → CompositePipelineRunner, Phase 2: Seed Pipeline, [S] Run Seed Pipeline (e.g., chembl_publication). Они позволяют быстро сопоставлять термины, роли сервисов и артефакты данных между моделью и реализацией. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`
