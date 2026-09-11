## Summary

Согласовать operator-facing scope/time текст с **существующими** PromQL/HTTP targets. Запросы, selectors, mappings, thresholds, reducers, `noValue` и `gridPos` не менять. Подгонять текст под запрос, а не запрос под текст.

**Parent:** #10387.

## Provenance

- Audit 11.09.2026, SHA [`850fcb7`](https://github.com/SatoryKono/BioactivityDataAcquisition/commit/850fcb7424bc8962c5d70bf52663fff8c488f1e0).
- Priority: P1. Size: S.

## Problem

Подписи называют CURRENT/RANGE/SELECTED RUN не теми объектами, которые реально считают панели.

| Surface | Panel | Сейчас | Факт запроса |
| --- | --- | --- | --- |
| Overview | 99 | `TIME RANGE = Domain Status` | 9002 = instant `topk(2, max by (input) (bioetl_l0_input_status_selected{...}))` |
| Pipeline Diagnostics | 9101 | description начинается с `TIME RANGE · SELECTED RUN` | instant `topk(3, bioetl_runtime_current_blocker_reason_scoped{pipeline,run_type} > 0)` |
| Provider Health | 9401 | description `TIME RANGE · Current verdict` | instant current verdict; link title `Inspect Provider Telemetry Freshness` ведёт в `viewPanel=9104`, а панель 9104 называется `Monitor Telemetry Presence` |
| Incident Workspace | 9401 | title `Monitor Incident Status`; description `CURRENT · TIME RANGE` | instant `max(bioetl_l0_status{pipeline,run_type})`; 2010 остаётся GLOBAL/UNVERIFIED |
| Run Explorer | 3010 | description начинается с `SELECTED RUN · Browse mode` | browse-index last 10 on disk; time picker не фильтрует таблицу |

Нельзя подменять timestamp события временем scrape или rule evaluation. При историческом конце time range статическая подпись AS OF относится к моменту оценки; отсутствие динамического переключения не разрешает называть исторический snapshot live now.

## Proposed change

1. **Overview 99** (`grafana/dashboards/bioetl-overview-v2.json`): CURRENT snapshot = Fleet Health, First Action и Domain Status; selected run = HTTP summary (9603); RANGE = история. Сохранить 9603 и геометрию.
2. **Runtime 9101**: «Блокировки выбранных Pipeline и Run Type на момент оценки; не результат выбранного Run ID». Кратко отметить snapshot и лимит трёх причин (полный qualifier «до 3» — GMIN-04).
3. **Provider 9401**: «Snapshot выбранного provider; fleet ниже имеет другой охват». Переименовать существующую ссылку в **Inspect Provider Telemetry Presence**; URL/`viewPanel=9104` не менять.
4. **Incident 9401**: title → `Monitor Selected-Scope Status`; description объясняет pipeline/run_type snapshot и GLOBAL-природу 2010. Не создавать статус Investigating. Сохранить GLOBAL/UNVERIFIED у 2010.
5. **Run Explorer 3010 / banner id=1**: BROWSE / last 10 on disk, not time-filtered. Не называть таблицу SELECTED RUN.

Краткое статическое объяснение допускается в уже существующей scope-панели. Текст, padding и line-height не раздувать.

## Out of scope

- Любые `expr` / HTTP url / parser / format / instant / range.
- `gridPos`, panel IDs, UID, nav bus, Trust/Run Explorer merge.
- MIN-02 (цвет banners), MIN-03 (`viewPanel=3022`), MIN-04 (видимый qualifier top-N), кроме пересечения copy, которое MIN-04 потом дополнит.

## Files (ожидаемые)

- `grafana/dashboards/bioetl-overview-v2.json`
- `grafana/dashboards/bioetl-runtime.json`
- `grafana/dashboards/bioetl-provider-health-v2.json`
- `grafana/dashboards/bioetl-incident-v1.json`
- `grafana/dashboards/bioetl-run-explorer-v1.json`
- `tests/integration/test_grafana_provenance_readability_contract.py` (`required_copy` для Overview 99 и Run Explorer)
- `tests/integration/test_grafana_dashboard_first_screen_contract.py` и title-based suites, если меняется title 9401
- `docs/03-guides/dashboards/contracts/panel-content-contract.yaml`
- `docs/03-guides/dashboards/panel-title-inventory.md`
- `docs/03-guides/dashboards/panel-contract-inventory.json`
- `grafana/plugins/bioetl-scenes-app/docs/scenes-parity-ledger.json` (если title 9401 входит в parity)

## Acceptance

- [ ] Оператор не принимает агрегат/fleet snapshot за точный Run ID и presence за freshness.
- [ ] На пяти поверхностях source, scope и time basis согласованы с targets.
- [ ] PromQL/HTTP targets, selectors, mappings, thresholds, reducers, `noValue`, `gridPos` бит-в-бит неизменны (кроме текстовых полей и одного link **title** на Provider 9401).
- [ ] Link href/params кроме title Presence не меняются.
- [ ] Title/copy contracts обновлены вместе с JSON, не skipped.
- [ ] Не добавлять global CSS / plugin / sanitizer bypass.

## Test plan

```text
pytest tests/integration/test_grafana_provenance_readability_contract.py tests/integration/test_grafana_dashboard_first_screen_contract.py tests/integration/test_grafana_dashboard_links.py tests/integration/test_dashboard_operator_readability.py tests/integration/test_dashboard_first_window_noscroll.py -q
```

Нормализованный JSON diff: только `options.content`, `description`, `title` (Incident 9401), data-link `title` (Provider 9401).
