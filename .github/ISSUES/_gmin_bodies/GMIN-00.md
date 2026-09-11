## Summary

Минимальный пакет правок семи shipped Grafana dashboards: исправить неверные scope/time подписи, нейтрализовать статические пояснения, открывать выбранный run сразу в identity-панели и явно обозначить top-N границы сводок.

Это **не** замена portfolio и **не** повтор DUX3–DUX6 / VIS-20260908. Источник: targeted comparison сохранённой дизайн-концепции с `origin/main` на 11.09.2026.

## Provenance

- Дата аудита: 11.09.2026 14:22 EDT.
- Pinned SHA: [`850fcb7424bc8962c5d70bf52663fff8c488f1e0`](https://github.com/SatoryKono/BioactivityDataAcquisition/tree/850fcb7424bc8962c5d70bf52663fff8c488f1e0/grafana/dashboards).
- Норматив: [`docs/01-requirements/DASHBOARD_REQUIREMENTS.md`](https://github.com/SatoryKono/BioactivityDataAcquisition/blob/850fcb7424bc8962c5d70bf52663fff8c488f1e0/docs/01-requirements/DASHBOARD_REQUIREMENTS.md).
- Предшественники (закрыты, не переоткрывать как failed): DUX5 #7116, DUX6 #7139, VIS-20260908 #10258.
- Связанные открытые измерения: #10170 (contrast/reflow). Не блокирует базовый пакет, но рендер-приёмка MIN-02/MIN-03 пересекается.

## Решение аудита

Оставить семь UID, native Stat/Table/Time series/State timeline, существующие панели, PromQL/HTTP targets, selectors, mappings, thresholds, reducers, `noValue` и `gridPos`. Navigation bus остаётся `0..6`. Configuration не входит в primary portfolio. Runs & Trust не создаётся новым UID.

PNG из чата **не** являются эталоном бизнес-семантики: это сгенерированные иллюстрации, не рендеры Grafana. Не переносить coverage-проценты, causal confidence, incident lifecycle `Investigating`, Trust Score и противоречивые Healthy+DEGRADED состояния.

## Доставка

Рекомендуемый порядок: **#10388 → #10389 → #10390 → #10391**, затем решение по рендерам для OPT.

| Code | Pri | Size | Issue |
| --- | --- | --- | --- |
| GMIN-01 | P1 | S | [#10388](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/10388) Исправить scope/time подписи |
| GMIN-02 | P2 | S | [#10389](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/10389) Нейтральные статические banners |
| GMIN-03 | P1 | S–M | [#10390](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/10390) `viewPanel=3022` в primary Run-link 3010 |
| GMIN-04 | P2 | S | [#10391](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/10391) Qualifier «до 2 / до 3 / до 5» |
| GMIN-OPT-01 | P3 | S | [#10392](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/10392) DQ 9101 `colorMode=value` после рендера |
| GMIN-OPT-02 | P3 | S | [#10393](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/10393) Trust 9418 freshness column только при наличии поля |

Бюджет базового пакета: **0** новых dashboards, **0** удалённых dashboards, **0** новых data panels, **0** новых metrics/datasources, **0** изменений data queries, **0** переносов `gridPos`. Меняются тексты/названия, локальный HTML статических пояснений и один существующий data link. Сопровождающие тесты и docs — только затронутые контракты.

## Явно вне scope

- Новая instrumentation, Trust Score, causal confidence, Configuration dashboard, live-run roster, неподтверждённые SLA.
- Logs/traces datasource, recovery actions, merge Bronze/Silver/Gold funnel.
- Подъём forensic detail на первый экран, уменьшение шрифта/высоты таблиц, смена refresh «как на PNG».
- Замена top-N полной таблицей, удаление unique evidence panels.
- Повторный запуск nav generator без просмотра diff (`NAV_HEIGHT=3` и Trust geometry map уже заданы).
- Global CSS, новый plugin, обход HTML sanitizer.

## Definition of done (epic)

- [ ] #10388: пять scope-ошибок исправлены; source/scope/time basis согласованы с существующими запросами.
- [ ] #10389: статические инструкции нейтральны в healthy и failed fixtures; WARN/CRIT панелей данных остаются заметны.
- [ ] #10390: строка Run Explorer сразу показывает identity выбранного run; Back восстанавливает контекст; если `viewPanel` не открывает nested collapsed panel — изменение не выпускается.
- [ ] #10391: границы top-N видны без Inspect; queries/limit/sort не меняются.
- [ ] Нормализованный diff не меняет datasource, variable query, targets, reducers, transformations, states, mappings, thresholds, `gridPos`.
- [ ] Title/copy contracts синхронизированы, а не обойдены.
- [ ] Численное снижение времени диагностики **не** заявляется без измерения на одинаковых сценариях.

## Рендер-приёмка (общий контур)

Закреплённый Grafana runtime, одна fixture-матрица: healthy, degraded, failed, unknown/no-data, stale, datasource error. Viewport 1366×768 и 1920×1080, dark/light, zoom 200%. Полные UUID, длинные reason values, число строк выше limit. Запрет выпуска при clipping основной причины/действия, подмене unknown на zero, потерянной identity или росте first-load бюджета.
