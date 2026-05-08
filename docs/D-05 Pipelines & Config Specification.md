______________________________________________________________________

Version: 0.3.0
Status: draft
Class: repo-only
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last synchronized: '2026-05-08'

______________________________________________________________________

# D-05 Pipelines and Config Specification (Draft Sync Note)

## Назначение

D-05 остаётся draft-конденсатором для будущей unified pipeline/config спецификации.
Текущие нормативные требования живут в опубликованных guides/reference страницах.

## Канонические источники

- `docs/03-guides/pipeline-configuration.md`
- `docs/03-guides/add-new-source.md`
- `docs/03-guides/add-pipeline-existing-source.md`
- `docs/04-reference/templates/index.md`
- `docs/00-project/RULES.md`
- `scripts/schema/README.md`

## Текущие зоны дрейфа

- Детальные таблицы и команды в D-05 быстро устаревают относительно `pipeline-configuration.md` и `scripts/schema` entry points.
- Runtime config schema validation и strictness policy уже централизованы в guides + tooling, поэтому дублирование в D-05 не добавляет signal.
- Шаблоны и registration workflow должны поддерживаться в `04-reference/templates` и composition guides, а не в отдельном дубле.

## План синхронизации D-05

1. Держать в D-05 только high-level map: config hierarchy, required config surfaces, validation gates.
1. Все исполняемые примеры команд оставлять в `03-guides` и `scripts/schema/README.md`.
1. Для каждой pipeline/config области фиксировать один canonical link вместо повторения текста.

## Критерии промоушена в future published handbook

1. D-05 не содержит копий таблиц и command blocks из канонических guides.
1. Все обязательные секции unified config описаны через ссылочную карту на актуальные документы.
1. Любая правка config workflow сначала отражается в canonical guides/tooling docs, потом в D-05 summary.
