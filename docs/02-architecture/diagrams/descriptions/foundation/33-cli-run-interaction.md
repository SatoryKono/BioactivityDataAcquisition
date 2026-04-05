______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Title: CLI Run Command → PipelineRunner Full Interaction

- Исходная диаграмма: `foundation/33-cli-run-interaction.mmd`

## Описание

Диаграмма Title: CLI Run Command → PipelineRunner Full Interaction из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате sequenceDiagram и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 33-cli-run-interaction. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §1.1 (Interfaces → Composition → Application). Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Значимые участники последовательностей: User, CLI (Click) interfaces/cli/, PipelineRunnerService application/services/, bootstrap_pipeline() composition/bootstrap/, RunnerFactory composition/factories/. По этим участникам удобно валидировать порядок вызовов, точки отказа и стратегию обработки ошибок. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные

- Тип: `sequenceDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`
