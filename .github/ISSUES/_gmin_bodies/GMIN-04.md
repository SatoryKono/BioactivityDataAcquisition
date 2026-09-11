## Summary

Сделать видимым ограничение компактных сводок: Overview 9002 «до 2», Runtime 9101 «до 3», DQ 9102 «до 5». Queries, fields и сортировка не меняются. Не добавлять total-count query ради «2 из N».

**Depends on:** #10388. **Parent:** #10387.

## Provenance

- Audit 11.09.2026, SHA `850fcb7`.
- Priority: P2. Size: S.

## Problem

Компактность полезна, но границу сводки нужно видеть без Inspect.

| Dashboard | Panel | Title сейчас | Limit |
| --- | --- | --- | --- |
| Overview | 9002 | `Review Domain Status` | `topk(2, max by (input) (...))` |
| Pipeline Diagnostics | 9101 | `Review Runtime Blockers` | `topk(3, ...)` |
| Data Quality | 9102 | `Inspect Current DQ Reasons` | `topk(5, ...)` (audit: limit 5) |

Большая fixture с числом строк выше limit выглядит как полный fleet.

Не утверждать, что локальный top-N является глобальной бизнес-приоритетностью: сортировка остаётся существующей.

## Proposed change

Добавить короткий qualifier в **существующий** заголовок **или** существующее пояснение: «до 2» / «до 3» / «до 5».

Если qualifier обрезается в title — короткая подпись в существующем scope/description, **без** увеличения `gridPos.h`.

Сохранить существующие detail links и их владельцев.

Layout 9102 не менять (reasons уже на первом экране: `x=8,y=8,w=16,h=5`).

## Out of scope

- Новые queries, `count()`, «2 of N».
- Изменение `topk`/`limit`, полей, sort, transformations.
- Перенос blockers повторно на Overview.
- OPT-01 (DQ 9101 colorMode).

## Files

- `grafana/dashboards/bioetl-overview-v2.json`
- `grafana/dashboards/bioetl-runtime.json`
- `grafana/dashboards/bioetl-dq-v2.json`
- Title-based tests, если qualifier идёт в `title`:
  - `tests/integration/test_grafana_dashboard_first_screen_contract.py` (`Inspect Current DQ Reasons`, `Review Domain Status`)
  - `tests/integration/test_grafana_overview_config.py`
  - `tests/integration/test_pipeline_runtime_dashboard.py`
  - `tests/integration/test_grafana_dashboard_metric_semantics.py`
  - `tests/integration/test_grafana_layout_and_metadata.py`
  - `tests/integration/test_dashboard_first_window_containment.py`
- docs panel inventories / `panel-content-contract.yaml` при смене title

Предпочтение: qualifier в description/banner, если title-lock слишком широкий; иначе обновить все title contracts в том же PR.

## Acceptance

- [ ] Большая fixture не выглядит полным fleet.
- [ ] Ограничение читается без Inspect.
- [ ] Длинный заголовок не обрезается; высота панели не растёт.
- [ ] `topk`/`limit`, поля, sort, links неизменны.
- [ ] Не заявляется, что top-N = global business priority.

## Test plan

```text
pytest tests/integration/test_grafana_dashboard_first_screen_contract.py tests/integration/test_grafana_overview_config.py tests/integration/test_pipeline_runtime_dashboard.py tests/integration/test_grafana_dashboard_metric_semantics.py -q
```

Рендер: fixture с числом domain/blocker/reason строк > limit; zoom 200%; clipping qualifier запрещён.
