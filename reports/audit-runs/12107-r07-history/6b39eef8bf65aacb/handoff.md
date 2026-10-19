# Handoff #12107 R07

Локальный report-only артефакт. Push, новый PR, merge, Resolve и закрытие issue не выполнялись.

## Владелец

- Запрошенная сессия `14271333931892187511`: в репозитории, GitHub search и доступных cloud agents не найдена. Статус `NOT_LOCATED`.
- Этот прогон: `bc-2b108baa-1992-4e1d-8bcc-c8f5a3524a22`.
- Конкурирующей ветки `12107` / adapter-owner на `origin` нет.
- Карантины `#12030`, `#12266`, `#12044` и PR `#12262` не снимались.

## Идентичность

- branch: `cursor_back/adapter-port-owner-map-4a22`
- HEAD = origin/main = `2c018779765294f6f61191e9f6ade860ada94861`
- tree: `2bcf21522cfc5f3e935a391276a3585400032108`
- parents: `019ff673a7e2314ae0f5c6c4bb24982f3bc2bc7f`
- source_tree_sha256: `6d24fa02c167aa32f697e19ff55580157b05013a7a45e02b03f0e39e33449bd0`
- adapter-owner-map.json sha256: `6b39eef8bf65aacbd63b165bbe2d5295d0ca3726a12410f97108e77b7844625c`
- Повторный `git fetch origin main` не сдвинул SHA. `HEAD...origin/main` = `0 0`.
- Tracked diff пуст. Файлы карты игнорируются правилом `/reports/*` и сохранены локально. Новый ratchet и правка `.gitignore` не вводились.
- Нового commit нет: коммитить было нечего в tracked tree, force-add игнорируемого отчёта не делался.

## Знаменатели

| Показатель | Значение |
| --- | ---: |
| universe | 2046 |
| classified | 100.0% |
| owner | 0.0% |
| behavioral conformance | 0.68% (14/2046) |

`classified = 100%` значит, что каждая строка получила класс. Это не полнота владельцев и не conformance. Класс `unresolved` пуст, потому что внешние structural matches записаны как `structural_candidate` (162) и остались в знаменателе.

Verdict: `NOT_VERIFIABLE` 2022, `UNREACHABLE` 10, `VERIFIED` 14, `DEFECT` 0. Ноль `DEFECT` не доказывает отсутствие дефектов: пробел без полностью разрешённых bases остаётся `NOT_VERIFIABLE`.

`VERIFIED` — только bounded rule: полное structural/explicit совпадение, composition/package/runtime reachability и architecture-тест из узкого списка contract-файлов, где функция называет символ и содержит `assert`. Это не исчерпывающее semantic conformance.

Все 2046 строк: `semantic_owner`, `composition_owner`, `lifecycle_owner` = `unassigned-tracking`. CODEOWNERS `@SatoryKono` записан как review owner и не считается semantic owner.

## Smoke

`runtime_smoke.py` exit 0. `load_providers` вернул 8 имён: chembl, crossref, openalex, pubchem, pubmed, semanticscholar, uniprot, uniprot_idmapping. Все восемь есть как `provider:*` строки. Pipeline registry: 22 имени. `__all__` getattr: 250 ok / 0 fail. HTTP-клиенты не создавались.

## Baseline

- `report-domain-ports-inventory --check` exit 0: 89 `*Port` Protocol, 89 runtime_checkable. Скан подтвердил те же 89 и отдельно насчитал 635 Protocol-классов во всём `src/bioetl`.
- `report-port-adapter-factory-coverage --check` exit 0. Это `TRACKED_PORTS`, не universe R07.
- `ChemblAdapter` — `NOT_VERIFIABLE`: structural `DataSourcePort` + `FilterableDataSourcePort` + `HealthCheckPort`, регистрация `registration_bio.py`, тесты есть, но не из contract-allowlist.

## Проверки

- source-tree manifest `--check` exit 0.
- `refresh-governance-artifacts --check` exit 1: stale `architecture-debt-remote-main-baseline.{json,md}`.
- Обновление не запускалось. Семейство remote-main не является предметом этой карты; `refresh_governance_artifacts` не должен переписывать remote-main. Новый capture ради зелёного gate не создавался. `src/bioetl` не менялся, поэтому module-coverage hash и architecture hash guard не пересчитывались в write-режиме.
- Mirror parity не запускался: runtime trees не менялись.

## Выходы

- `reports/audit-runs/12107-r07/adapter-owner-map.json`
- `reports/audit-runs/12107-r07/adapter-owner-map.md`
- `reports/audit-runs/12107-r07/r08-lifecycle-inventory.json` (148 строк, owner не назначен)
- `reports/audit-runs/12107-r07/r09-storage-surface-inventory.json` (567 строк)
- follow-up без conformance assert для adapter/factory/noop/provider: 192
- UNREACHABLE: 10, список в markdown
