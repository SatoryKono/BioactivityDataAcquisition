______________________________________________________________________

Version: 0.3.0
Status: draft
Class: repo-only
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last synchronized: '2026-05-08'

______________________________________________________________________

# D-06 Data Quality and Quarantine Handbook (Draft Sync Note)

## Назначение

D-06 фиксирует структуру будущего consolidated handbook по DQ и Quarantine.
Сейчас это non-normative draft, синхронизированный с текущими published guides/runbooks и CLI surface.

## Канонические источники

- `docs/03-guides/dq-configuration.md`
- `docs/03-guides/running-pipelines.md`
- `docs/04-reference/cli.md`
- `docs/05-operations/runbooks/quarantine-management.md`
- `docs/05-operations/runbooks/pipeline-failure-dq.md`
- `docs/05-operations/runbooks/dq-failure-investigation.md`

## Текущая validated модель (summary)

- DQ defaults: `soft_fail=0.05`, `hard_fail=0.20`, `invalid_record_policy=quarantine`.
- Quarantine CLI surface: `inspect`, `stats`, `replay`, `purge`, `resolve`.
- Persisted operator statuses: `NEW`, `IGNORED`, `REPROCESSED`.
- `quarantine replay` подготавливает/маркирует записи для reprocessing; не выполняет полный pipeline rerun.

## Текущие зоны дрейфа

- Основной риск дрейфа связан с дублированием CLI/runtime semantics между guide/reference/runbook слоями.
- D-06 не должен повторно описывать полный operator workflow, который уже живёт в `runbooks`.
- Любые изменения DQ/quarantine semantics должны сначала фиксироваться в code + canonical docs.

## План синхронизации D-06

1. Держать в D-06 только summary и map на канонические документы.
1. Не дублировать command tables из `docs/04-reference/cli.md`.
1. Не дублировать инцидентные процедуры из `docs/05-operations/runbooks/*`.
1. При изменении DQ/quarantine behavior обновлять D-06 только после синхронизации канонических источников.

## Критерии промоушена в future published handbook

1. Утверждён единый owner workflow для DQ/quarantine docs cascade.
1. В D-06 отсутствует нормативное дублирование CLI/runbook.
1. Все statements в D-06 трассируются к каноническим docs и проверяемым runtime surfaces.
