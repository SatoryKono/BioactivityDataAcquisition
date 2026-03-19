# Title: CLI Entry Point to Pipeline Execution Full Chain

- Исходная диаграмма: `foundation/37-cli-entry-full-chain.mmd`

## Описание
Диаграмма Title: CLI Entry Point to Pipeline Execution Full Chain из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате flowchart и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 37-cli-entry-full-chain. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §1.1 (Interfaces Layer), interfaces/cli/. Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Ключевые блоки/подграфы включают: Interfaces Layer (Click), Application Service Layer, Composition Layer, Application Core, Result & Exit. Их состав отражает главные границы ответственности и маршруты взаимодействия между подсистемами или слоями. Показательные узлы диаграммы: Interfaces Layer (Click), $ bioetl run --pipeline chembl_activity\n--run-type incremental\n--resume, Parse CLI Arguments • pipeline_name • run_type (RunType enum) • resume flag, Build RunOptions • pipeline_name • run_type • resume: bool, Application Service Layer, PipelineRunnerService.run() • lookup pipeline in registry • validate run options. Они позволяют быстро сопоставлять термины, роли сервисов и артефакты данных между моделью и реализацией. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные
- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`
