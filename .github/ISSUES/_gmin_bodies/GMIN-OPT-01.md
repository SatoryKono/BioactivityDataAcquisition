## Summary

Необязательное визуальное ослабление вспомогательной DQ-панели 9101: `colorMode=background` → `colorMode=value`, сохранив primary 9401, текстовые состояния и все thresholds.

**Blocked until:** #10388–#10391 и реальный render (не PNG). **Parent:** #10387.

## Provenance

- Audit 11.09.2026, SHA `850fcb7`.
- Priority: P3 / optional. Size: S.

## Problem

На DQ `bioetl-dq-v2.json`:

- 9401 `Monitor DQ Current Status` — `colorMode=background` (primary verdict).
- 9101 `Monitor DQ Threshold State` — тоже `colorMode=background` (`gridPos` 8×5 at y=8).

Оба background-mode конкурируют за внимание. Это гипотеза дизайна, не доказанный дефект. Без подтверждённой конкуренции за внимание оставлять текущий вид.

Runtime 9401 имеет `colorMode=none` на другом dashboard; это **не** лицензия унифицировать все headline cards вслепую.

## Proposed change (только после рендера)

1. Снять screenshots 9101 vs 9401 на healthy / WARN / CRIT / UNKNOWN, dark/light.
2. Если 9101 реально конкурирует с 9401 — сменить **только** 9101 на `colorMode=value`.
3. Сохранить mappings, thresholds, `textMode`, data links, `gridPos`.
4. Согласовать с design contract; **не** вводить blanket-исключение в tests и не менять общий профиль всех current-status panels.

## Do not ship if

- Нет confirmed attention competition на реальном Grafana render.
- Изменение ломает first-window contrast/readability без выигрыша.
- Приходится ослаблять 9401 или трогать thresholds.

## Files

- `grafana/dashboards/bioetl-dq-v2.json` (panel 9101 `options.colorMode` only)
- точечный allowlist presentation field в tests, если контракт проверяет `colorMode`
- `docs/01-requirements/DASHBOARD_REQUIREMENTS.md` / design-system — только если роль visualization явно нормирована

## Acceptance

- [ ] Evidence: screenshots before/after на закреплённом runtime.
- [ ] 9401 остаётся primary background (или документированное иное решение).
- [ ] Текстовые состояния и thresholds 9101 неизменны.
- [ ] Normalized diff: только `options.colorMode` у 9101 (+ test allowlist).

## Test plan

Существующие DQ first-screen / metric-semantics tests. Не добавлять blanket skip.
