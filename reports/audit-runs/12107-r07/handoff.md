# Handoff #12107 R07

Live-копия handoff для открытого PR [#12290](https://github.com/SatoryKono/BioactivityDataAcquisition/pull/12290). Merge, Resolve и закрытие issue не выполнялись.

## Владелец

- Запрошенная сессия `14271333931892187511`: статус `FAILED`, сообщён 2026-10-19 в 21:09:55 MSK (последнее изменение 21:06:18 MSK); источник — `acceptance-review.json`. Артефакт Jules не найден, новый запуск не начинался.
- Этот прогон: `bc-2b108baa-1992-4e1d-8bcc-c8f5a3524a22`.
- Ветка PR: `cursor_back/adapter-port-owner-map-4a22`; PR открыт, не merged (проверено через GitHub API).
- Карантины `#12030`, `#12266`, `#12044` и PR `#12262` не снимались.

## Идентичность

- HEAD и head PR: `081edb00c14cb6f124f16f683ae0ea6754bc341d`.
- Ветка текущих исправлений: `coderabbit/fix-audit-review-findings/b93de22d`.
- Tracked diff PR непуст: карта и acceptance/governance-артефакты уже включены в tracked tree. Локальные исправления review находятся поверх указанного HEAD и ещё не закоммичены.
- Последний commit: `fix(audit): keep R07 scanners out of the Sonar new-code set`; исполняемые исходники отчёта хранятся как `.snapshot`.
- Исходное сканирование сохранено с pin commit `2c018779765294f6f61191e9f6ade860ada94861`, tree `2bcf21522cfc5f3e935a391276a3585400032108`.
- source_tree_sha256 исходной карты: `6d24fa02c167aa32f697e19ff55580157b05013a7a45e02b03f0e39e33449bd0`.
- adapter-owner-map.json sha256: `6b39eef8bf65aacbd63b165bbe2d5295d0ca3726a12410f97108e77b7844625c`.
- Историческая копия handoff и байты исходной карты сохранены без изменений.

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

`runtime_smoke.snapshot` exit 0 (исходный прогон). `load_providers` вернул 8 имён: chembl, crossref, openalex, pubchem, pubmed, semanticscholar, uniprot, uniprot_idmapping. Все восемь есть как `provider:*` строки. Pipeline registry: 22 имени. `__all__` getattr: 250 ok / 0 fail. HTTP-клиенты не создавались.

## Baseline

- `report-domain-ports-inventory --check` exit 0: 89 `*Port` Protocol, 89 runtime_checkable. Скан подтвердил те же 89 и отдельно насчитал 635 Protocol-классов во всём `src/bioetl`.
- `report-port-adapter-factory-coverage --check` exit 0. Это `TRACKED_PORTS`, не universe R07.
- `ChemblAdapter` — `NOT_VERIFIABLE`: structural `DataSourcePort` + `FilterableDataSourcePort` + `HealthCheckPort`, регистрация `registration_bio.py`, тесты есть, но не из contract-allowlist.

## Проверки

- source-tree manifest `--check` exit 0.
- Обновление governance-артефактов выполнено: remote-main baseline, test-governance, telemetry rebind и debt-governance. После обновления `refresh-governance-artifacts --check` exit 0; команды и результаты сохранены в `acceptance-review.json`.
- Новый coverage capture не создавался; telemetry rebind не является новым измерением. `src/bioetl` не менялся, module-coverage source hash сохранён.
- Текущий повтор `refresh-governance-artifacts --check` остановлен (exit 1): локальный tracking ref `origin/main` не совпадает с remote main. Это отдельный результат текущей проверки, а не результат исторического обновления выше.
- Mirror parity не запускался: runtime trees не менялись.

## Выходы

- `reports/audit-runs/12107-r07/adapter-owner-map.json`
- `reports/audit-runs/12107-r07/adapter-owner-map.md`
- `reports/audit-runs/12107-r07/r08-lifecycle-inventory.json` (148 строк, owner не назначен)
- `reports/audit-runs/12107-r07/r09-storage-surface-inventory.json` (567 строк)
- follow-up без conformance assert для adapter/factory/noop/provider: 192
- UNREACHABLE: 10, список в markdown
