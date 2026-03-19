# Title: YAML Configuration Resolution Chain

- Исходная диаграмма: `foundation/46-yaml-config-resolution.mmd`

## Описание
Диаграмма Title: YAML Configuration Resolution Chain из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате flowchart и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 46-yaml-config-resolution. В комментариях исходника зафиксирован фокус диаграммы: Covers: infrastructure/config/pipeline_config_api.py, infrastructure/config/, domain/config/. Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Ключевые блоки/подграфы включают: YAML File Hierarchy, DQ Config Hierarchy (DQConfigLoader), Filter Config Hierarchy (FilterConfigLoader), Infrastructure Config Loaders, Domain Config Objects (Frozen). Их состав отражает главные границы ответственности и маршруты взаимодействия между подсистемами или слоями. Показательные узлы диаграммы: YAML File Hierarchy, configs/base/pipeline.yaml (global defaults), configs/providers/{provider}.yaml (provider defaults), configs/entities/{provider}/{entity}.yaml (pipeline config), configs/providers/{provider}.yaml (source config), DQ Config Hierarchy (DQConfigLoader). Они позволяют быстро сопоставлять термины, роли сервисов и артефакты данных между моделью и реализацией. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-27`
