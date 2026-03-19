# Class Diagram: 11 Storage

- Исходная диаграмма: `class-diagrams/11-storage.mmd`

## Описание
Диаграмма Storage Components показывает архитектурную модель модуля `11-storage` и фиксирует контракты, роли и отношения между сущностями слоя `Class / Interface`. Основной фокус: Bronze/Silver/Gold writers and supporting classes. На схеме отражено примерно 16 классов и 17 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые элементы для быстрого чтения: BaseDeltaWriter, BronzeWriter, SilverWriter, GoldWriter, DeltaReader, ArrowDataConverter.

## Метаданные
- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата метаданных: `2026-03-01`
