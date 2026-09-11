## Summary

Рассмотреть компактную видимую колонку `evidence_freshness` в Trust panel 9418 **только если** поле реально есть в HTTP frame и помещается в текущие 12×5.

**Blocked until:** #10388–#10391 и проверка frame. **Parent:** #10387.

## Provenance

- Audit 11.09.2026, SHA `850fcb7`.
- Priority: P3 / optional. Size: S.

## Problem

В `grafana/dashboards/bioetl-control-plane-v1.json` panel 9418 есть hidden override:

```json
"matcher": { "id": "byName", "options": "evidence_freshness" }
"properties": [{ "id": "custom.hidden", "value": true }]
```

Selected-run Trust уже существует: Processing и Trust раздельно; Reasons ведёт в 9414. Новый процентный Trust Score или повтор сводки на отдельном dashboard **не нужны**.

## Proposed change (условный)

1. Подтвердить, что `evidence_freshness` присутствует в `pipeline_run_report` / summary frame (не invent field).
2. Если поля нет — **оставить hidden**, не создавать новый endpoint.
3. Если поле есть и 12×5 не переполняется: compact visible column; Processing, Trust, Reasons и full reason trail сохраняются.
4. Если overflow / clipping UUID / потеря Reasons — откатить к current summary.

## Do not ship if

- Поля нет в frame.
- Нужен новый endpoint / metric.
- Ломается 12×5 или first-window budget.
- Появляется Trust Score / causal confidence.

## Files

- `grafana/dashboards/bioetl-control-plane-v1.json` (9418 field override `custom.hidden`)
- HTTP contract / golden summary tests, если колонка становится operator-facing
- title/copy contracts только при смене displayName

## Acceptance

- [ ] Frame proof приложен к PR (sample payload без секретов).
- [ ] Processing / Trust / Reasons не удалены и не сужены до нечитаемости.
- [ ] Handoff 9414 сохранён.
- [ ] Нет нового datasource/query.
- [ ] Overflow → no-change (issue закрывается как wontfix/not doing с evidence).

## Test plan

Trust first-screen + control-plane dashboard tests. Browser: 12×5 at 1366×768 and 1920×1080, full UUID, dark/light.
