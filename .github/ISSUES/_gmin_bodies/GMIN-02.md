## Summary

Убрать фиксированный warning-акцент у статических scope/provenance banners. Пояснение нейтрально; цвет состояния принадлежит данным.

**Depends on:** #10388. **Parent:** #10387.

## Provenance

- Audit 11.09.2026, SHA `850fcb7`.
- Priority: P2. Size: S.
- Это экспертная оценка визуального риска, не наблюдённая ошибка оператора.

## Problem

Все семь first-window HTML banners используют одну и ту же warning-заливку независимо от данных:

```html
border-left:4px solid #ff9830;background:rgba(255,152,48,0.08)
```

Подтверждено на `origin/main`: Overview 99, Runtime 9400, Provider 9400, DQ 9400, Incident 9400, Trust 9400, Run Explorer 1.

Контракт **закрепляет** этот акцент:

- `tests/integration/test_grafana_provenance_readability_contract.py` — `_REQUIRED_CSS` / `_REQUIRED_CSS_FIRST_WINDOW_H3`
- `tests/integration/test_dux6_residual_contracts.py` — `test_provenance_panels_share_readability_contract` (для не-compact banners)

Оранжевая рамка конкурирует с настоящими WARN/CRIT.

## Proposed change

- Заменить оранжевую рамку на нейтральную (например theme-safe gray/`text`) либо убрать `border-left`.
- Убрать полупрозрачную orange background.
- Текст, размер, padding, line-height, `font-size:16px`, `max-width:96ch`, overflow-wrap — **не менять**.
- Native Grafana chrome не перерисовывать.
- На Trust/Provider применять только к подтверждённым статическим scope banners (`id=9400`), не к динамическим severity panels.
- Не добавлять global CSS, новый plugin, обход HTML sanitizer.

## Out of scope

- Реальные severity mappings/thresholds (`orange` для WARN в Stat/Table остаётся).
- OPT-01 (`colorMode` DQ 9101).
- Унификация Runtime 9401 `colorMode=none` (отличие не доказано как дефект).

## Files

- `grafana/dashboards/bioetl-overview-v2.json`
- `grafana/dashboards/bioetl-runtime.json`
- `grafana/dashboards/bioetl-provider-health-v2.json`
- `grafana/dashboards/bioetl-dq-v2.json`
- `grafana/dashboards/bioetl-incident-v1.json`
- `grafana/dashboards/bioetl-control-plane-v1.json`
- `grafana/dashboards/bioetl-run-explorer-v1.json`
- `tests/integration/test_grafana_provenance_readability_contract.py`
- `tests/integration/test_dux6_residual_contracts.py`
- при необходимости `docs/03-guides/dashboards/design-system.md` (если там зафиксирован orange banner token)

## Acceptance

- [ ] Одни и те же инструкции выглядят нейтрально в healthy и failed fixtures.
- [ ] Фактические WARN/CRIT панелей данных остаются заметны.
- [ ] Authored body ≥16px сохранён.
- [ ] Dark/light, длинный текст, zoom 200% без clipping основного вопроса.
- [ ] Тесты требуют нейтральный banner, а не `#ff9830`.

## Test plan

```text
pytest tests/integration/test_grafana_provenance_readability_contract.py tests/integration/test_dux6_residual_contracts.py tests/integration/test_dashboard_operator_readability.py tests/integration/test_dashboard_first_window_noscroll.py -q
```

Рендер: healthy + failed, dark/light, 1366×768 и 1920×1080, zoom 200%. Скриншот-only style injection запрещён.
