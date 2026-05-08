______________________________________________________________________

Version: 0.3.0
Status: draft
Class: repo-only
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last synchronized: '2026-05-08'

______________________________________________________________________

# D-02 Provider Integration Handbook (Draft Sync Note)

## Назначение

D-02 фиксирует будущую структуру unified provider handbook.
Сейчас документ является draft-слоем синхронизации и не заменяет канонические guides/reference.

## Канонические источники

- `docs/03-guides/add-new-source.md`
- `docs/03-guides/add-pipeline-existing-source.md`
- `docs/03-guides/pipeline-configuration.md`
- `docs/04-reference/providers/README.md`
- `docs/04-reference/templates/provider-spec-template.md`
- `docs/00-project/RULES.md`

## Текущие зоны дрейфа

- В проекте уже есть детальные шаги и шаблоны в guides/reference, поэтому дублирование этих шагов в D-02 быстро устаревает.
- Команды проверки и acceptance criteria нужно держать в одном месте (guides/testing/schema tooling), а в D-02 оставлять только консолидированный маршрут.
- Provider onboarding split по нескольким каноническим страницам корректен; D-02 должен выступать как карта, а не как вторая нормативная инструкция.

## План синхронизации D-02

1. Держать в D-02 только integration flow map: `provider config -> adapter -> registration -> first entity pipeline -> tests/docs`.
1. Все исполняемые команды оставлять в `03-guides` и ссылаться на них без копирования.
1. Для каждого этапа добавить owner-ссылку на канонический doc вместо переписывания требований.

## Критерии промоушена в future published handbook

1. D-02 не содержит дублированных нормативных checklists.
1. Каждая стадия onboarding имеет ровно один canonical reference link.
1. Проверки CI и validation команды перечислены только через ссылки на актуальные guides.
