______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Title: Five-Layer Import Matrix Enforcement (ARCH-001)

- Исходная диаграмма: `foundation/27-import-matrix-enforcement.mmd`

## Описание

Диаграмма Title: Five-Layer Import Matrix Enforcement (ARCH-001) из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате flowchart и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 27-import-matrix-enforcement. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §1.1, docs/00-project/ai/rules/bioetl-ai-rules.md ARCH-001. Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Ключевые блоки/подграфы включают: Legend, BioETL Five-Layer Architecture, Enforcement Mechanism. Их состав отражает главные границы ответственности и маршруты взаимодействия между подсистемами или слоями. Показательные узлы диаграммы: Legend, ✅ Allowed Import, ❌ Forbidden Import, BioETL Five-Layer Architecture, <b>Interfaces Layer</b> CLI (Click), HealthServer <i>src/bioetl/interfaces/</i>, <b>Composition Layer</b> GenericPipelineFactory, RunnerFactory ServicesBuilder, PipelineRegistry <i>src/bioetl/composition/</i>. Они позволяют быстро сопоставлять термины, роли сервисов и артефакты данных между моделью и реализацией. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные

- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`
