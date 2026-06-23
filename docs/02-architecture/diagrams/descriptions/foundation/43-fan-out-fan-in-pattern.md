______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Title: Fan-Out/Fan-In Pattern — Composite Pipeline Enrichment

- Исходная диаграмма: `foundation/43-fan-out-fan-in-pattern.mmd`

## Описание

Диаграмма Title: Fan-Out/Fan-In Pattern — Composite Pipeline Enrichment из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате flowchart и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 43-fan-out-fan-in-pattern. В комментариях исходника зафиксирован фокус диаграммы: Covers: ADR-026 (Composite Pipeline Pattern), application/composite/. Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Ключевые блоки/подграфы включают: Seed Pipeline Result, Key Extraction, Fan-Out (EnrichmentCoordinator), Enricher Silver Tables, Fan-In (MergeService). Их состав отражает главные границы ответственности и маршруты взаимодействия между подсистемами или слоями. Показательные узлы диаграммы: Seed Pipeline Result, Seed Silver Table (e.g., chembl/publication ), Key Extraction, KeyExtractorService.extract_keys() • read seed Silver via DeltaReader • select join_key columns (doi, pmid) • deduplicate → unique key list, DOI Keys (~50,000 unique), PMID Keys (~30,000 unique). Они позволяют быстро сопоставлять термины, роли сервисов и артефакты данных между моделью и реализацией. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные

- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`
