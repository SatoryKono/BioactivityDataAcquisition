# Сводка evidence: project-package-topology

Дата: 2026-07-18
Статус: refreshed

Эта сводка фиксирует текущую package topology из `origin/main` после
восстановления evidence DAG. Она является repo-local evidence и не заменяет
canonical architecture guidance в `docs/00-project/` и
`docs/02-architecture/`.

## Current source baseline

- `source_module_count=2237`
- `source_tree_sha256=a37a4d7adf0c835baf182a48843a03e4e95499eb50d64f46332d7ff3a29746bd`
- Module coverage data snapshot: `2026-07-13`
- Source-tree reconciliation date: `2026-07-18`

The coverage snapshot date is retained because this closeout refreshes the
source-tree inventory without substituting a newer coverage run for the
tracked coverage measurements. The module count and source hash above are
recomputed from the current tree by the canonical module-coverage producer.

## Layer topology

| Layer | Python files | First-order packages |
| --- | ---: | ---: |
| `application` | 664 | 6 |
| `composition` | 275 | 5 |
| `domain` | 574 | 21 |
| `infrastructure` | 584 | 20 |
| `interfaces` | 138 | 2 |

The five layers contain 2235 Python files. Together with
`src/bioetl/__init__.py` and `src/bioetl/__main__.py`, this reconciles exactly
to `source_module_count=2237`.

## Evidence gate

- Module-coverage source hash matches the live source tree.
- Layer totals reconcile with the module-coverage inventory.
- Domain I/O, compatibility, dead-code, hotspot, test-governance, flaky-test,
  architecture-scorecard, and remote-main producers run before the final debt
  governance rollup.
- Historical topology observations must not be used as a current count unless
  they are remeasured against this source hash or a newer one.

Статус gate: `PASSED`

## Scope limits

- This evidence confirms structure, not health, ownership, or API quality.
- First-order package counts do not imply a refactoring priority by themselves.
- Deeper topology claims require dedicated, current evidence rather than this
  aggregate summary.
