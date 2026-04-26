______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Title: Application Core Component Collaboration

- Исходная диаграмма: `foundation/40-application-core-collaboration.mmd`

## Описание

Диаграмма Title: Application Core Component Collaboration из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате flowchart и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 40-application-core-collaboration. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §1.1 (Application Layer), application/core/. Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Ключевые блоки/подграфы включают: PipelineRunner (application/core/runner.py), Lifecycle Services, Pre/Post Services, Batch Execution, Observability. Их состав отражает главные границы ответственности и маршруты взаимодействия между подсистемами или слоями. Показательные узлы диаграммы: PipelineRunner (application/core/runner.py), run() — main orchestrator, Lifecycle Services, LockCoordinator • acquire(key, owner, ttl=90s) • release(key, owner) • validate_ownership(), HeartbeatService • start() • stop(), CheckpointManagerService • read_checkpoint() • save_checkpoint(). Они позволяют быстро сопоставлять термины, роли сервисов и артефакты данных между моделью и реализацией. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные

- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`
