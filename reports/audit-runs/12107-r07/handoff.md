# Handoff #12107 R07

Live-копия для открытого PR #12290. Merge и закрытие issue не выполнялись. Приёмка остаётся `NOT_ACCEPTED`.

## Владелец

- Запрошенная сессия `14271333931892187511`: статус `FAILED`. Источник — `acceptance-review.json`. Артефакт Jules не найден, новый запуск не начинался.
- Этот прогон: `bc-2b108baa-1992-4e1d-8bcc-c8f5a3524a22`.
- Ветка PR: `cursor_back/adapter-port-owner-map-4a22`.
- Карантины `#12030`, `#12266`, `#12044` и PR `#12262` не снимались.

## Идентичность

- branch: `cursor_back/adapter-port-owner-map-4a22`
- Исходный pin скана сохранён: HEAD `2c018779765294f6f61191e9f6ade860ada94861`, tree `2bcf21522cfc5f3e935a391276a3585400032108`, source_tree_sha256 `6d24fa02c167aa32f697e19ff55580157b05013a7a45e02b03f0e39e33449bd0`.
- Исторические байты карты: `reports/audit-runs/12107-r07-history/6b39eef8bf65aacb/adapter-owner-map.json`, sha256 `6b39eef8bf65aacbd63b165bbe2d5295d0ca3726a12410f97108e77b7844625c`.
- Живая карта после исправления same-file reachability: sha256 `44ce5e1207bcd9b1287427f925e0a4bf789c1547dc1ac2df15271fc0c986db55`.
- Файлы карты закоммичены в ветке. Tracked diff не пуст.
- Обновление governance-артефактов выполнено, и `refresh-governance-artifacts --check` после него вернул exit 0. Новый capture покрытия не создавался. `src/bioetl` этой правкой не менялся.

## Знаменатели

| Показатель | Значение |
| --- | ---: |
| universe | 2046 |
| classified | 100.0% |
| owner | 0.0% |
| behavioral conformance | 0.68% (14/2046) |

`classified = 100%` значит, что каждая строка получила класс. Это не полнота владельцев и не conformance.

Verdict живой карты: `NOT_VERIFIABLE` 2031, `UNREACHABLE` 1, `VERIFIED` 14, `DEFECT` 0. Ноль `DEFECT` не доказывает отсутствие дефектов. Историческая гистограмма до same-file исправления: `NOT_VERIFIABLE` 2022, `UNREACHABLE` 10.

Девять прежних `UNREACHABLE` имели обращение по имени в том же файле, включая `create_registered_pipeline_registry` и `rebase_local_data_path`. Они переведены в `NOT_VERIFIABLE`. Единственный оставшийся `UNREACHABLE`: `create_observability_bundle` в `src/bioetl/composition/bootstrap/runtime/observability_assembly.py`.

`VERIFIED` — только bounded rule: полное structural/explicit совпадение, composition/package/runtime reachability и architecture-тест из узкого списка contract-файлов. Упоминание класса рядом с любым `assert` не доказывает проверку методов порта. 14 строк остаются `VERIFIED` только по этой bounded rule.

Все 2046 строк: `semantic_owner`, `composition_owner`, `lifecycle_owner` = `unassigned-tracking`. CODEOWNERS `@SatoryKono` записан как review owner и не считается semantic owner.

## Smoke

Записанный `smoke_returncode` равен 0: `load_providers` вернул 8 имён, registry — 22, `__all__` getattr — 250 ok / 0 fail. `runtime_smoke.snapshot` возвращает 1, если `errors` непуст или хотя бы одна строка `getattr` имеет `ok` не `True`. Успешный прогон заканчивается кодом 0.

## Индекс портов

`port-relationship-index.json` группирует связи по `name@path`. Одноимённые `ContractPolicyProtocol` из domain и application больше не сливаются в один порт.

## Проверки

- source-tree pin скана не пересчитывался: правка классифицирует уже снятые строки и не меняет `src/bioetl`.
- Mirror parity не запускался: runtime trees не менялись.
