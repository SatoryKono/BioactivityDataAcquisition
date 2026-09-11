## Summary

В primary data link колонки `Run` панели 3010 добавить `viewPanel=3022`, сохранив row `pipeline` / `run_type` / `run_id` и время. Переход остаётся на UID `bioetl-run-explorer-v1`.

**Depends on:** #10388. **Parent:** #10387.

## Provenance

- Audit 11.09.2026, SHA `850fcb7`.
- Priority: P1. Size: S–M (M из-за обязательной browser-проверки collapsed panel).

## Problem

Сейчас primary link 3010 выбирает run и предлагает вручную раскрыть Selected Run Details:

```text
title: Select this run (then expand Selected Run Details below)
url: /d/bioetl-run-explorer-v1/6-run-explorer?${workflow:queryparam}&var-pipeline=${__data.fields.Pipeline}&var-run_type=${__data.fields.run_type}&var-run_id=${__value.raw}&${__url_time_range}
```

`viewPanel=3022` уже используется в других current-run handoff (например Overview/DQ/Incident selected-run summary). На 3010 его нет.

Тест `tests/integration/test_dashboard_scope_refactor.py` проверяет `viewPanel=3022` у summary-панелей, но не у browse-index 3010.

## Proposed change

В существующий **единственный** primary data link колонки `Run`:

- сохранить `var-pipeline`, `var-run_type`, `var-run_id=${__value.raw}`, `${__url_time_range}` и текущую сериализацию;
- добавить `viewPanel=3022`;
- обновить title, чтобы не обещать обязательный поиск секции (например «Open this run identity»).

Это не новые вкладки, не JS auto-expand Row, не merge Trust+Run Explorer.

## Gate: не выпускать без browser proof

`3022` (`Inspect Run Identity`) лежит внутри collapsed row. Если Grafana `viewPanel` на закреплённом runtime **не** открывает nested collapsed panel, изменение **не выпускается**. Обещание одного клика без этой проверки недопустимо.

Fixture: выбран selector B, оператор открывает строку A, в target показана identity A; Back восстанавливает контекст (pipeline/run_type/run_id/time). Другие mandatory links и доступ к full run evidence сохраняются.

Отдельно проверить focused-panel route: неизменный список запросов dashboard не доказывает неизменную сетевую нагрузку.

## Out of scope

- Новые tabs / scenes rewrite / UID cutover.
- Автораскрытие Row через JS.
- Изменение HTTP query 3010 (`limit=10`) или состава колонок.
- Удаление collapsed default у Selected Run Details.

## Files

- `grafana/dashboards/bioetl-run-explorer-v1.json` (override matcher `Run`, `id=3010`)
- `tests/integration/test_grafana_dashboard_links.py`
- `tests/integration/test_dashboard_scope_refactor.py` (точечно расширить на 3010)
- title/copy contracts, если меняется link title

## Acceptance

- [ ] URL содержит `viewPanel=3022` и row identity (`Pipeline`, `run_type`, raw `run_id`) плюс `${__url_time_range}`.
- [ ] `targetBlank=false`; same UID.
- [ ] Browser fixture A/B проходит на закреплённой Grafana.
- [ ] Если focus не открывает 3022 — PR не merge.
- [ ] Прочие mandatory links неизменны.
- [ ] Normalized diff: только этот data link (+ тесты/docs контракта).

## Test plan

```text
pytest tests/integration/test_grafana_dashboard_links.py tests/integration/test_dashboard_scope_refactor.py tests/integration/test_grafana_dashboard_first_screen_contract.py -q
```

Browser (обязательно): Grafana 10.4.x из текущего provisioning, collapsed Selected Run Details, click Run on row A while selectors show B.
