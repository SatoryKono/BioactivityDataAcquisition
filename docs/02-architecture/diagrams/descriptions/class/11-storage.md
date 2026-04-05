______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Class Diagram: 11 Storage

- Исходная диаграмма: `class-diagrams/11-storage.mmd`

## Описание

Диаграмма Storage Components показывает архитектурный срез storage layer и фиксирует ключевые writer/reader/converter families вокруг Bronze, Silver и Gold путей записи. Схему стоит читать как representative class view: она помогает увидеть основные storage seams, но не заменяет полный инвентарь support-модулей, metadata helpers и вспомогательных реализаций. Ключевые элементы для быстрого чтения: `BaseDeltaWriter`, `BronzeWriter`, `SilverWriter`, `GoldWriter`, `DeltaReader`, `ArrowDataConverter`.

## Метаданные

- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата метаданных: `2026-03-20`
