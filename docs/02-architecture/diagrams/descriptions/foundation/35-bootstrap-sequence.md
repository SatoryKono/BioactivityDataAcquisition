______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-08'

______________________________________________________________________

# Composition Layer Bootstrap Sequence

- Исходная диаграмма: `foundation/35-bootstrap-sequence.mmd`

## Описание

Диаграмма «Composition Layer Bootstrap Sequence» из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Mixed (System / Component / Class)». В комментариях исходника зафиксирован фокус диаграммы: RULES.md §1.1 (Composition Root), composition/bootstrap/runtime/. Схема имеет плотность порядка 28 узлов и 27 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: Step 1: Logger, Step 2: Configuration, Step 3: Observability Bundle, Step 4: Storage, Step 5: HTTP Client, Step 6: Data Source. Показательные узлы для быстрого чтения: BootstrapLogger.configure(), StructlogLogger (JSON, ISO timestamps, run_id binding), ConfigLoader.load(pipeline_name), PipelineYamlConfig (base defaults merged with entity.yaml), DQ + Filter config loaders, ObservabilityBundle.

## Метаданные

- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-03-24`
- Узлы: `28`
