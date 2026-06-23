______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Title: Error Classification Decision Tree — Full Logic

- Исходная диаграмма: `foundation/41-error-classification-tree.mmd`

## Описание

Диаграмма Title: Error Classification Decision Tree — Full Logic из foundation-набора фиксирует устойчивый архитектурный или процессный паттерн проекта BioETL. Она представлена в формате flowchart и служит базовым ориентиром для инженерного анализа, ревью изменений и обсуждения технических решений. Уровень детализации обозначен как Mixed (System / Component / Class), поэтому схема подходит одновременно для быстрой навигации по контексту и для проверки корректности зависимостей, контрактов и потоков обработки данных в рамках сценария 41-error-classification-tree. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §3.1 (Error Handling), domain/exceptions/. Это снижает неоднозначность интерпретации и помогает поддерживать консистентность между визуальной документацией, ADR-решениями и реальным кодом. Ключевые блоки/подграфы включают: HTTP Branch Outcomes, Domain Branch Outcomes, Infrastructure Branch Outcomes, Error Actions. Их состав отражает главные границы ответственности и маршруты взаимодействия между подсистемами или слоями. Показательные узлы диаграммы: Error Occurred, HTTP Status Code?, Domain Error?, Infrastructure Error?, [E] ServiceAuthenticationError\\n(CriticalError)\\n→ FAIL FAST, no retry\\n→ Check API key config, [E] ApiError\\n(RecoverableError)\\n→ Log warning\\n→ Skip entity. Они позволяют быстро сопоставлять термины, роли сервисов и артефакты данных между моделью и реализацией. Дополнительно в метаданных указан показатель плотности (@nodes=n/a), что полезно при контроле читаемости и планировании декомпозиции диаграмм на более узкие представления.

## Метаданные

- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-02-24`
