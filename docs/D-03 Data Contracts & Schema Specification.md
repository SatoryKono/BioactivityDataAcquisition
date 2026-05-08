______________________________________________________________________

Version: 0.3.0
Status: draft
Class: repo-only
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last synchronized: '2026-05-08'

______________________________________________________________________

# D-03 Data Contracts and Schema Specification (Draft Sync Note)

## Назначение

D-03 фиксирует будущий consolidated handbook для contract governance.
Сейчас это draft-layer для синхронизации с уже опубликованным contract contour.

## Канонические источники

- `docs/04-reference/contracts/README.md`
- `docs/04-reference/contracts/gold-schemas.md`
- `docs/03-guides/testing.md`
- `docs/02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md`
- `configs/quality/test_matrix.yaml`

## Текущие зоны дрейфа

- Версионирование, совместимость и CI gates уже описаны в published contract/testing docs; дублирование в D-03 создаёт риск рассинхронизации.
- Contract drift и provider drift checks должны опираться на существующий `tests/contract/` контур, без параллельной системы.
- Операционные детали release communication и compatibility windows должны ссылаться на active ADR/policy, а не поддерживаться отдельным текстом в draft.

## План синхронизации D-03

1. Оставить в D-03 только карту контрактных surfaces: code contracts, generated artifacts, test governance, live contract workflows.
1. Нормативные правила (SemVer, compatibility, CI blockers) ссылать напрямую на ADR/contract docs.
1. Для provider drift reporting описывать только integration points с `tests/contract/` и `scripts/qa`, без дублирования schema snapshot governance.

## Критерии промоушена в future published handbook

1. D-03 не дублирует текст из `contracts/README` и `testing.md`.
1. Все contract workflow шаги покрыты ссылками на исполняемые scripts и test suites.
1. Термины `schema stability`, `provider drift`, `live contracts` определены согласованно с `configs/quality/test_matrix.yaml`.
