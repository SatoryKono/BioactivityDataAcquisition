# Сбор доказательств завершён: interfaces-cli-and-public-entrypoint-compat

**Создано объектов evidence:** 6
**Статус gate:** PASSED

## Краткий итог

| ID | Краткое утверждение | Confidence |
|----|----------------------|------------|
| EV-cli-package-root-declares-public-commands-surface-as-compatibility-layer | Package root прямо объявляет `bioetl.interfaces.cli.commands.*` как compatibility surface. | 0.96 |
| EV-cli-run-and-runall-wrappers-are-pure-alias-shims | `run.py` и `run_all.py` — чистые alias shims без собственной orchestration logic. | 0.94 |
| EV-cli-compat-helper-is-centralized-module-aliasing-runtime | `_compat.py` — единый runtime-механизм module alias / reexport для CLI shims. | 0.93 |
| EV-cli-top-level-command-wrappers-are-curated-retained-entrypoints | Top-level command wrappers уже curated как `retained-entrypoint` rows. | 0.97 |
| EV-cli-support-shims-are-freeze-guarded-test-facing-seams | Helper-level shims governed как test-facing / measured-only seams под freeze guards. | 0.95 |
| EV-cli-tests-still-use-public-and-helper-shim-import-paths | Tests всё ещё patch/import именно public wrappers и helper shims. | 0.96 |

## Ключевые выводы

- Внутри CLI есть по меньшей мере две разные compatibility корзины:
  - top-level command wrappers как `retain-as-contract`;
  - helper/policy support seams как measured-only или `retain-with-window`.
- `_compat.py` сейчас выглядит как central retained mechanism и, вероятно, должен удаляться последним внутри CLI compatibility family.
- Если открывать retirement backlog в CLI, то более реалистичный first candidate — не top-level `run.py`, а helper-level support seams после test migration.

## Зафиксированные противоречия

- Wrapper-модули визуально похожи на legacy leftovers, но governance и boundary tests трактуют их как sanctioned public seams.
- Helper-level support shims выглядят ближе к removable compatibility debt, но текущий test suite всё ещё опирается на них как на patch/import targets.

## Оставшиеся пробелы

- Пока не проведена полная import inventory сверка по всем top-level CLI wrappers вне `run/run-all` family.
- Нужна cross-shard проверка: не закреплены ли helper-level seams также docs/governance anchors вне CLI family.
- Decision phase должен определить, считать ли helper shims `retain-with-window` или отдельной migration backlog category.
