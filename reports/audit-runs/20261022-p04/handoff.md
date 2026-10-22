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

PR был draft. CodeRabbit ревью не запускал и inline-замечаний не оставил. Исправлять нечего.

## Проверенные факты

| Факт | Значение |
| --- | ---: |
| Python-файлы `src/bioetl/infrastructure` | 682 |
| Прямые наследники `*Port` | 19 |
| Пары в `PORT_ADAPTER_CASES` | 8 |
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

## Повтор

```text
rg -n "PORT_ADAPTER_CASES" tests/architecture/test_adapter_port_conformance.py
rg -n "def atomic_write" src/bioetl/infrastructure/storage/support/atomic_ops.py
test -f reports/audit-runs/12107-r07/adapter-owner-map.md
```
