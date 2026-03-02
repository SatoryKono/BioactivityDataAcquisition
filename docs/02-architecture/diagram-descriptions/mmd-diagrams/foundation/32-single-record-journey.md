# Title: Record Processing Pipeline — Single Record Journey

- Исходная диаграмма: `mmd-diagrams/foundation/32-single-record-journey.mmd`

## Описание
Диаграмма Title: Record Processing Pipeline — Single Record Journey из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате flowchart и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 32-single-record-journey. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §2.1-§2.6 (Data Flow, DQ), §2.8 (Normalization). Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Ключевые блоки/подграфы включают: 1. External API, 2. Bronze Layer, 3. Transform (RecordProcessor), 4. Validate, 5. Route Decision. Их состав отражает главные границы ответственности и маршруты взаимодействия между подсистемами или слоями. Показательные узлы диаграммы: 1. External API, REST API Response (e.g., ChEMBL /activity), 2. Bronze Layer, BronzeWriter.write_bronze() • JSONL serialization • zstd compression • atomic rename • _manifest.json, 3. Transform (RecordProcessor), BatchTransformer.transform(). Они позволяют быстро сопоставлять термины, роли сервисов и артефакты данных между моделью и реализацией. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`
