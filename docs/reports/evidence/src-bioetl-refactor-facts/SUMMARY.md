# Сводка evidence: src-bioetl-refactor-facts

Дата: 2026-03-26
Статус: завершено

Review note (2026-03-27): included in the repo-wide evidence-pack sweep; see `docs/reports/evidence/project-evidence-rebaseline/06-status/EVIDENCE-PACK-REVIEW-2026-03-27.md` for wave status, retained-vs-reopened interpretation, and current review scope.

## Проверка gate

- Parent evidence required: `5`
- Parent evidence collected: `6`
- All shard gates: `PASSED`
- File coverage with `>=3` facts: `PASSED`
- Object coverage with `>=3` facts: `PASSED`

## Shards

- `root`: `2` files, `0` objects, `6` EV files
- `application`: `305` files, `2329` objects, `6` EV files
- `composition`: `161` files, `671` objects, `6` EV files
- `domain`: `389` files, `2477` objects, `6` EV files
- `infrastructure`: `386` files, `2345` objects, `6` EV files
- `interfaces`: `91` files, `354` objects, `6` EV files

## Top Findings

- `src/bioetl` содержит `1334` Python files и `8176` code objects.
- Наиболее широкий shard по файлам: `domain` (`389` files).
- Наиболее широкий shard по объектам: `domain` (`2477` objects).
- Minimum-facts constraint выполнен для всех file records и object records.
- Family-level density hotspots полезнее для triage, чем общий размер слоя.

## Gaps

- В пакет не включены профили CPU/памяти и git churn.
- Нет decision artifacts (`DEC-*`), только evidence и synthesis.
