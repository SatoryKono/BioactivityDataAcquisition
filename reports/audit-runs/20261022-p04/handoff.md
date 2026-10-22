# P04 infrastructure audit handoff

Прогон `20261022-p04`. Стадия P04, concern: infrastructure adapters, storage atomicity, lifecycle ownership.
Код `src/bioetl` в этом прогоне не менялся. Ремедиация портов и новый crash-прогон не входят в diff.

## Ревизия

- Проверенный код: `ee83860e7902adcd5eebff163514df97a6c5f5f4` (`origin/main` на момент повторной проверки).
- Пустой относительно аудита коммит Jules: `d1f4bb351cca664c8057d97f201b4c1426a65927`.
- В том коммите добавлен только корневой `review_plan_script.py` с телом `print("Creating plan review request")`.
- Время проверки, UTC: `2026-10-22T07:26:37Z`.

## Почему CI был красным

Прогон `39736306466`.

- Fast governance, шаг cleanliness: `review_plan_script.py` не входит в `.github/root-allowlist.txt`.
- Class lane: `tests/architecture/test_root_hygiene_review_registry.py::test_no_tracked_repository_root_scripts_remain` ожидает пустой список корневых `*.py`.
- Классификатор помечает этот путь как `fail_closed_unclassified_path`, поэтому остальные path-scoped шаги остаются `skipped` и агрегатор их не принимает.

Файл удалён. Пустой diff тоже ломает гейт (`fail_closed_empty_diff`, как в P03). Этот каталог оставляет классифицируемый diff под `reports/**`.

## Слияние с main

Текстовых конфликтов с `origin/main` не было. Ветка отставала на три коммита: отчёт P03, синхронизация docs-governance и bump virtualenv. Они влиты merge-коммитом до этого handoff.

## CodeRabbit

Первый проход пропустил draft. После снятия draft ревью на `6e875ddf98` оставило два замечания: счётчик `PORT_ADAPTER_CASES` был 8 при семи элементах кортежа, а раздел «Повтор» не отделял выполненные проверки от команд повтора. Оба замечания закрыты в этом handoff.

## Проверенные факты

| Факт | Значение |
| --- | ---: |
| Python-файлы `src/bioetl/infrastructure` | 682 |
| Прямые наследники `*Port` | 19 |
| Пары в `PORT_ADAPTER_CASES` | 7 |
| Строки `_REGISTERED_ADAPTERS` | 8 |
| Корневые скрипты на `origin/main` | 0 |

Постоянный исторический owner map: `reports/audit-runs/12107-r07/adapter-owner-map.md`.
Свежей матрицы create/close кампании `20261022` нет.

## Findings

1. `AUDIT-20261022-INFRA-001` / `INFRA-ADAPTER-CONFORMANCE`. Статус `NOT_PROVEN`, вердикт `ABSENCE_DISPROVEN`. Набор сигнатурного conformance уже лежит в `tests/architecture/test_adapter_port_conformance.py`. Он не перечисляет все 19 прямых наследников.
2. `AUDIT-20261022-INFRA-002` / `INFRA-STORAGE-CRASH-RECOVERY`. Статус `NOT_PROVEN`, вердикт `NOT_VERIFIABLE`. Хелперы `atomic_write` и `_replace_with_retry` и их юнит-тесты есть. Обрыв процесса по Bronze, Silver и Gold здесь не запускался.
3. `AUDIT-20261022-INFRA-003` / `INFRA-LIFECYCLE-OWNERSHIP`. Статус `NOT_PROVEN`, вердикт `NOT_VERIFIABLE`. Историческая карта 12107 не заменяет свежий обход composition root.

Машиночитаемая копия: `reports/audit-runs/20261022-p04/findings.json`.
Манифест: `reports/audit-runs/20261022-p04/audit-manifest.json`.

## Вне объёма

- Расширение `PORT_ADAPTER_CASES`.
- Crash-кампания слоёв хранения.
- Матрица create/close и смена бюджетов технического долга.

## Выполненные проверки

Команды ниже запускались локально на дереве с отчётом P04. Это не вывод GitHub Actions.

| Команда | Результат |
| --- | --- |
| `.venv/bin/python -m scripts.docs generate-cleanup-inventory --check` | exit 0, inventory is synchronized |
| `.venv/bin/python -m scripts.docs check-links --report-json reports/docs-link-check-report.json` | exit 0, All checks passed |
| `.venv/bin/python -m pytest tests/architecture/test_root_hygiene_review_registry.py::test_no_tracked_repository_root_scripts_remain tests/architecture/test_documentation_cleanup_inventory.py::test_documentation_cleanup_inventory_check_passes -q --tb=short` | exit 0, две точки |
| `.venv/bin/python scripts/engineering/repo/check_no_partial_tree.py --base origin/main --tip HEAD` | exit 0, no partial-tree commits |
| `.venv/bin/python scripts/engineering/ci/pr_gate.py classify` для diff `origin/main...HEAD` | `unclassified_files` пуст |

Прогон `39736306466` на коммите с `review_plan_script.py` завершился с `failure`. Это прошлый красный CI, не проверка этого handoff.

## Не запускались

- `pytest tests/unit/`
- `mypy --strict src/bioetl/`
- Crash-прогон Bronze, Silver и Gold
- Полный обход composition root
- Повторный `coderabbit review --agent`

GitHub PR Gate на head после merge `main` в момент этой правки ещё не был принят как доказательство: локальные команды выше его не заменяют.

## Команды повтора фактов

Эти команды не входили в таблицу выполненных проверок. Они заново читают те же источники.

```text
rg -n "PORT_ADAPTER_CASES" tests/architecture/test_adapter_port_conformance.py
rg -n "def atomic_write" src/bioetl/infrastructure/storage/support/atomic_ops.py
test -f reports/audit-runs/12107-r07/adapter-owner-map.md
```
