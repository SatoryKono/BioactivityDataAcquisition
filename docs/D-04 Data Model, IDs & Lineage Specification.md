______________________________________________________________________

Version: 0.3.0
Status: draft
Class: repo-only
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last synchronized: '2026-05-08'

______________________________________________________________________

# D-04 Data Model, IDs and Lineage Specification (Draft Sync Note)

## Назначение

D-04 сохраняется как draft-рамка для будущего unified handbook по model/identity/lineage.
Нормативные правила текущего runtime определяются опубликованными architecture/reference документами.

## Канонические источники

- `docs/02-architecture/data-layers.md`
- `docs/04-reference/hash-policy.md`
- `docs/04-reference/contracts/README.md`
- `docs/04-reference/contracts/run-manifest-ledger.md`
- `docs/02-architecture/decisions/ADR-012-storage-clear-contract-and-run-id.md`
- `docs/02-architecture/decisions/ADR-029-output-metadata-unification.md`

## Текущие зоны дрейфа

- В D-04 исторически смешивались normative contract rules и проектные гипотезы по lineage evolution.
- Для identity/hash behavior source of truth уже закреплён в hash-policy + коде; переписывание этих правил в D-04 создаёт рассинхронизацию.
- Control-plane lineage/provenance contract уже покрыт отдельным published документом `run-manifest-ledger.md`.

## План синхронизации D-04

1. Использовать D-04 как навигационную карту между data layers, hash-policy, output metadata и control-plane contracts.
1. Любые изменения identity/hash semantics документировать сначала в hash-policy/ADR, а в D-04 оставлять только ссылочный summary.
1. Линейдж-полевая таксономия и storage guarantees должны ссылаться на published contract docs, а не дублироваться здесь.

## Критерии промоушена в future published handbook

1. D-04 содержит только согласованную модель терминов и cross-links к каноническим правилам.
1. Нет повторного описания low-level алгоритмов, уже закреплённых в `hash-policy` и коде.
1. Все runtime-facing lineage guarantees ссылаются на соответствующие ADR/contract pages.
