# P03 application audit handoff

Прогон `20261022-p03`. Стадия P03, concern: application orchestration.
Код в этом прогоне не менялся. P20 не выполнялся.

## Ревизия

- Проверенный код: `f9d1a55ddf14256fdc1936db2177633f1aa1e724` (`origin/main` на момент повторной проверки).
- Дерево этой ревизии совпадает с деревом до добавления handoff.
- Пустой коммит Jules: `8bdedf27de2006058bd735f10a810cf27f6a30da`.
- Его дерево совпадает с родителем `88101d7ee82a4822ea7cce8710663abece5619f4`.
- Время проверки, UTC: `2026-10-22T06:40:00Z`.

## Почему CI был красным

PR не содержал ни одного изменённого файла. Классификатор `pr_gate` включает все path-scoped гейты с причиной `fail_closed_empty_diff`, а шаги Class lane их пропускают. Агрегатор затем видит `skipped` там, где нужен `success`.

Прогон: `39732860020`.

Слияние с `main` прошло без конфликтов. Пустой коммит оставлен в истории. Этот каталог делает diff непустым.

## Проверенные факты

| Факт | Значение |
| --- | ---: |
| Python-файлы `src/bioetl/application` | 819 |
| Узлы `ClassDef` | 848 |
| Файлы с `CancelledError` | 9 |
| Совпадения `bioetl.infrastructure` | 0 |
| `module-dependency-map.json` violations | 0 |
| Рёбра `application` | application 1650, domain 1132 |
| `source_fingerprint` | `7274aefc0fa32a40f0315a7f40205cae58ae6883d754a782fe56fdaf5f95f6f7` |

Символы `AppLifecycleManager` и `graceful_shutdown` в `src/bioetl/application` отсутствуют.

Постоянный инвентарь портов: `reports/quality/domain-ports-inventory.md`.
Handoff P02 кампании `20261022` в `reports/audit-runs` не найден.

## Findings

1. `AUDIT-20261022-APP-001` / `APP-LIFECYCLE-CANCEL`. Статус `NOT_PROVEN`, вердикт `NOT_VERIFIABLE`. Децентрализованная обработка `CancelledError` подтверждена статически. Утечка ресурсов и обязанность свести её в один класс не подтверждены.
2. `AUDIT-20261022-APP-002` / `APP-P02-MISSING`. Статус `PROVEN` только для отсутствия campaign handoff P02. Вердикт проверки «только порты» — `NOT_VERIFIABLE`. Обхода infrastructure со стороны application карта слоёв не показывает.

Машиночитаемая копия: `reports/audit-runs/20261022-p03/findings.json`.
Манифест: `reports/audit-runs/20261022-p03/audit-manifest.json`.

## Вне объёма

- Ремедиация жизненного цикла.
- Исполнение P02 и P20.
- Изменение бюджетов технического долга.

## Повтор

```text
rg -n "CancelledError" src/bioetl/application --glob '*.py'
rg -n "AppLifecycleManager|graceful_shutdown" src/bioetl/application --glob '*.py'
rg -n "bioetl.infrastructure" src/bioetl/application --glob '*.py'
```
