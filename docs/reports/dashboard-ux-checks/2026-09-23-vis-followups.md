# Визуальные исправления Grafana #10614–#10624

Проверка кандидата в изолированной ветке `codex/grafana-vis-10614-10624`, базовый commit `670633e6ec68`. Это не подтверждение внедрения в main и не разрешение закрыть issues. Семь тестовых копий в Grafana 12.0.0 используют реальные Prometheus-данные и read-only копию существовавших run reports (1785 файлов). Новые pipelines для заполнения панелей не запускались. Исходные dashboards и run evidence не изменялись через UI.

Браузерные размеры: 1920×1080 и 1000×900, тёмная тема, диапазон Last 24 hours. Для сохранённого запуска использован `chembl_molecule`, `incremental`, `7dfad8f0-1f7b-51c4-8bdd-785defb2fb31`; для общих списков — All / SELECT RUN. Полные URL, время и размеры приложены в [журнале снимков](assets/2026-09-23-vis/screenshots.json). Внешний runtime source ID копии: `433d86cfb2ec03d9bd23b033ce50aae985e0e7bf71a8873544ccf23927c90af5`; он обозначает конфигурацию источника, а не git SHA кандидата.

| Issue / панель | Изменение и результат | Проверка перед закрытием |
| --- | --- | --- |
| P1 #10614 Run Explorer / 3010 | Terminal Event age считается от completed_at; running — от последнего события. Недостоверная дата остаётся UNKNOWN. | Unit cases terminal/running/missing/future; сверить сохранённый report после deployment. |
| P1 #10615 Overview / 9018–9020 | Полная ширина, 8 tracks на странице, ось 290 px. Убрано наложение подписей без удаления series. | Повторить страницы tracks на production и обеих ширинах. |
| P2 #10616 Run Explorer / 3010, 9451 | Короткий display ID сохраняет полный UUID в ссылках; UNKNOWN читается целиком. Evidence action открывает точный report. | Полный UUID/Report и WARN/INCOMPLETE route после deployment. |
| P2 #10617 Trust / 9413–9415, 7 | Три колонки Check / Reason / Status, удалено дублирование reason, постоянная table legend. Реальный manifest показывает 7 читаемых проверок. | Обе ширины, длинные причины, сохранённый и текущий контексты. |
| P2 #10618 Overview / 215, 20215, 9010–9011 | Скрыты технические route-поля; таблицы увеличены и сбалансированы. Видны 7 строк и полный Run Type. | Проверить все страницы action list и пустые выборки. |
| P2 #10619 Pipeline Diagnostics / 238, 240, 9105, 22460, 2461 | Постоянные легенды; records/s; единицы lag без двойной подписи. Полный stage list на 1000 px показывает 15 из 21 строк. | Stage/Run Type scope и сохранение численных значений. |
| P2 #10620 Provider Health / 114, 105, 9104 | Одновременно видны provider/status/check time/age; исторический degraded count нейтрален; уменьшен акцент telemetry. | Исторический счётчик не воспринимается как текущий health. |
| P2 #10621 Data Quality / 9102, 9, 1 | Pipeline в таблице причин, отдельные Gold/Silver evidence destinations, горизонтальные полные error categories, единые stage colors с Runtime. | Gold link реально открыл panel 156 и сохранил Run ID и time; проверить Silver и все states после deployment. |
| P2 #10622 Incident / 22010, 9400 | Длинные поля переносятся, удалена налезающая пагинация; баннер объясняет GLOBAL и UNVERIFIED. | Проверить весь список внутри обычного dashboard и view panel. |
| P2 #10623 Общий selected-run блок | Одна нейтральная строка Choose a run; канонические API verdicts не изменены. Поля сводных зеркал сохраняются. | SELECT RUN не превращается в UNKNOWN из-за отсутствующего поля; выбранный run сохраняет INCOMPLETE/WARN. |
| P3 #10624 Общая типографика | Компактные stat values 20 px / labels 14 px, более полезная высота таблиц и постоянные легенды. | Финальный обзор семи дашбордов на exact merged SHA. |

## Проверки и ограничения

Последний широкий dashboard-прогон: **816 passed, 9 skipped**; HTTP unit-прогон: **160 passed**. После последней короткой подписи DQ выполнены регрессии idempotence / metric preservation / action coverage и размер HTTP-модуля: **14 passed**. Два source-inventory guards до commit пропускались штатно из-за dirty source tree; их требуется повторить после commit. Canonical renderer и Scenes ledger обновлены.

Полный архитектурный прогон до финальных правок: **4748 passed, 40 failed, 80 skipped**. Нельзя считать его PASS. Прямое превышение лимита selected_run_status устранено выделением `_selected_run_presentation.py`; форматирование затронутых файлов исправлено. Остальные ошибки включают существующие application complexity, facade LOC и рассинхронизацию governance artifacts; полный baseline-сравнительный прогон не выполнен, поэтому все 40 ошибок не объявляются фоновыми.

Во время проверки тестовый HTTP-сервер завершился. Реальный QUERY ERROR зафиксирован отдельно: источник не был представлен как OK; сервер восстановлен и заполненная validation-таблица повторно проверена. Копия report evidence предшествует более новым catalog runs: их Missing — ограничение копии, не доказательство потери production reports. VALID EMPTY, TELEMETRY MISSING, UNKNOWN и INCOMPLETE не заменялись искусственными нулями.

GitHub Actions имеет внешний billing blocker: [Tests run 35823938507](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/35823938507), annotation: “The job was not started because your account is locked due to a billing issue.” Требуется CI на SHA PR, merge, deployment и финальная визуальная приёмка. Issues #10614–#10624 остаются открытыми до этой проверки. Наличие локальных screenshots не означает полного state-matrix PASS.

Runtime/skills не изменены; синхронизация AI runtime mirrors неприменима. PromQL и состав metric series сохраняются регрессионным тестом. Prometheus-only вариант не изменялся; отдельная браузерная приёмка этого варианта не выполнена.

## Скриншоты

- [00-run-explorer-narrow-loaded](assets/2026-09-23-vis/00-run-explorer-narrow-loaded.jpg)
- [02-overview-narrow-tracks](assets/2026-09-23-vis/02-overview-narrow-tracks.jpg)
- [after-run-narrow-top](assets/2026-09-23-vis/after-run-narrow-top.jpg)
- [after-run-wide-top](assets/2026-09-23-vis/after-run-wide-top.jpg)
- [after-run-wide-selection](assets/2026-09-23-vis/after-run-wide-selection.jpg)
- [after-run-narrow-selection](assets/2026-09-23-vis/after-run-narrow-selection.jpg)
- [after-overview-wide-tracks](assets/2026-09-23-vis/after-overview-wide-tracks.jpg)
- [after-overview-narrow-tracks](assets/2026-09-23-vis/after-overview-narrow-tracks.jpg)
- [after-overview-wide-failed](assets/2026-09-23-vis/after-overview-wide-failed.jpg)
- [after-overview-narrow-failed](assets/2026-09-23-vis/after-overview-narrow-failed.jpg)
- [after-trust-narrow-validation](assets/2026-09-23-vis/after-trust-narrow-validation.jpg)
- [after-trust-wide-validation](assets/2026-09-23-vis/after-trust-wide-validation.jpg)
- [after-trust-narrow-query-error](assets/2026-09-23-vis/after-trust-narrow-query-error.jpg)
- [after-runtime-narrow-full-stage](assets/2026-09-23-vis/after-runtime-narrow-full-stage.jpg)
- [after-provider-narrow-raw](assets/2026-09-23-vis/after-provider-narrow-raw.jpg)
- [after-provider-wide-counts](assets/2026-09-23-vis/after-provider-wide-counts.jpg)
- [after-provider-narrow-counts](assets/2026-09-23-vis/after-provider-narrow-counts.jpg)
- [after-dq-narrow-errors](assets/2026-09-23-vis/after-dq-narrow-errors.jpg)
- [after-dq-gold-destination](assets/2026-09-23-vis/after-dq-gold-destination.jpg)
- [after-incident-narrow-full](assets/2026-09-23-vis/after-incident-narrow-full.jpg)
- [after-incident-wide-full](assets/2026-09-23-vis/after-incident-wide-full.jpg)
