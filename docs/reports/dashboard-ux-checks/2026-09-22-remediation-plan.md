# План исправлений Grafana (GR-DB-CORR) — актуализация

**Дата:** 2026-09-22 (актуализация ~16:50 UTC+3)  
**Статус:** рабочий план  
**Эпик:** #10554  
**SSOT дашбордов:** `grafana/dashboards/*.json`  
**База аудита 0–3:** live (Run Explorer / Trust / Overview / Pipeline Diagnostics)  
**Дашборды 4–6:** JSON-static правки допустимы; live-дополнение — после туннеля/стенда

## Каноническая нумерация

| # | Title | UID / файл |
|---|-------|------------|
| 0 | Run Explorer | `bioetl-run-explorer-v1` |
| 1 | Trust | `bioetl-control-plane-v1` |
| 2 | Overview | `bioetl-overview-v2` |
| 3 | Pipeline Diagnostics | `bioetl-runtime` |
| 4 | Provider Health | `bioetl-provider-health-v2` |
| 5 | Data Quality | `bioetl-dq-v2` |
| 6 | Incident Workspace | `bioetl-incident-v1` |

## Принципы

1. Править только provisioning-JSON в репо (UI-правки перезапишутся).
2. Сначала вводящее в заблуждение → ошибки отображения → косметика.
3. `processing_status` и `trust_status` — **разные оси**; не сливать в один статус.
4. Preview-копии в Grafana UI **не** второй SSOT (в репо preview-JSON нет).
5. Monitoring Docker не поднимать без явного запроса (ADR-010).
6. DoD на JSON-PR:  
   `pytest tests/integration/test_dashboard_operator_readability.py`  
   `pytest tests/integration/test_dashboard_first_window_noscroll.py`

---

## Состояние issues (на момент актуализации)

| Issue | Тема | Статус |
|-------|------|--------|
| #10554 | EPIC GR-DB-CORR | **OPEN** |
| #10571 | ACCEPT матрица без ложного PASS | **OPEN** |
| #10570 | R01–R02 rate/increase / DQ sums | **OPEN** |
| #10557 | D01 Ops deadlines / HTTP 200 errors | **CLOSED** (2026-09-22, #10599) |
| #10568 | V-TABLE ширины/переносы | **CLOSED** (2026-09-22, #10599) |

Связанные уже закрытые ранее в кампании: #10593 (Runtime actions / partial DQ totals) и др. children эпика — см. историю #10554.

**PR #10599** (`96c8a8319e5e`): bounded full run selectors (filter-options budget 20s), table wrap acceptance на 900/1320. Закрыл #10557 и #10568. Явно **не** закрывает #10570 / #10571 / #10554.

---

## Сделано (не повторять)

| Было в черновике | Итог |
|------------------|------|
| B4 частично (медленные run selectors / filter-options) | Снято #10599: полный список options без усечения истории; budget 20s только для filter-options |
| V-TABLE (#10568) | Снято #10599: Pipeline/Workflow wrap, Open report width |
| D01 deadlines / late HTTP 200 (#10557) | Снято #10599 + предшествующие Ops-правки; live re-accept в #10571 |
| Часть Runtime action links / DQ partial totals | Снято #10593 |

---

## Остаток работ

### Фаза A — ложные статусы / скоуп (JSON, приоритет P0/P1)

| ID | Доска | Проблема (проверено в JSON) | Исправление | Effort | Трекает |
|----|-------|-----------------------------|-------------|--------|---------|
| **A1** | 1. Trust, 3. Diagnostics | `$pipeline` default=`unknown` (нет в опциях) → UNKNOWN | Default = All / `$__all` | S | #10554, #10571 |
| **A2** | 3. Diagnostics | Hidden `$provider_hint=chembl` при `pipeline=unknown` | Default пусто/All; согласовать с `$pipeline` | S | #10554 |
| **A3** | 0. Run Explorer | Колонка success vs trust ERROR | **Две оси:** processing + Evidence/Trust verdict (не подмена) | M | #10554, #10571 |
| **A4** | 1. Trust selected-run | `run_id=-` → красные ошибки запросов | Dashboard guard / hide query при `-` + empty «SELECT RUN» (часть noValue уже есть) | S–M | #10554, #10571 |

### Фаза B — навигация и копирайт (JSON-static, пакет)

| ID | Доска | Проблема (проверено в JSON) | Исправление | Effort |
|----|-------|-----------------------------|-------------|--------|
| **B1** | 0. Run Explorer | Data link slug `6-run-explorer` (UID верный) | Унифицировать на `0-run-explorer` или URL без ложного номера | S |
| **B2** | 2. Overview | «Open 2. Runtime…» ведёт на дашборд 3 | «Open 3. Pipeline Diagnostics» | S |
| **B3** | 3. Diagnostics | `http://localhost:9090/targets` | Относительный URL / убрать / runbook | S |
| **B4** | 5. DQ | Footer «0. Control Plane» | «1. Trust» | S |
| **B5** | 5. DQ `$stage` | Дубль «Default selection is All stages.» (×2) | Убрать дубль | S |
| **B6** | 6. Incident | Description: алерты «в collapsed», а Monitor Current Alerts на первом экране | Синхронизировать текст с layout | S |
| **B7** | 0 + 6 | Нет annotation `Annotations & Alerts` | Добавить как у 1–5 | S |
| **B8** | 0–6 nav | Slug vs UID в шине | Пакетом с B1 | S |

### Фаза C — мелочь Run Explorer / Trust

| ID | Проблема | Исправление | Effort |
|----|----------|-------------|--------|
| **C1** | Domains: высота 12 при ~6 рядах | Уменьшить `gridPos.h` | S |
| **C2** | Мёртвый rename `evidence_completeness` → Evidence | Удалить | S |
| **C3** | Chip «1. Trust» как ссылка | aria/disabled или текст | S |
| **C4** | UUID truncate | Документировать или wrap | S |
| **C5** | Workflow везде «—» | Скрыть колонку при пустых данных | S |
| **C6** | UI Preview-копии | Удалить/регенерировать из SSOT; не плодить JSON | S |

### Фаза D — remaining open issues (не «закрыть по JSON»)

| Issue | Что осталось | Критерий закрытия |
|-------|--------------|-------------------|
| **#10570** | R01–R02: `$__interval` / rate windows; DQ soft+hard без подстановки нулей | Live-повтор на актуальном Prometheus + фикс query/recording при подтверждении |
| **#10571** | Полная семантическая/визуальная матрица; нет ложного PASS | Матрица по registry; живые 4–6; dual-channel статусов; без заявления PASS при blocked gaps |
| **#10554** | Эпик | Закрывать **только** когда #10570 и #10571 закрыты (или явно out-of-scope с записью) |

### Фаза E — backend residual (после #10599)

| ID | Тема | Статус |
|----|------|--------|
| **E1** | `run_id=-` контракт (200 + SELECT RUN / valid empty vs 400) | Уточнить live после A4; не регрессировать #10557 |
| **E2** | `*_read_error` → QUERY ERROR / UNAVAILABLE, не failed trust-verdict | Открыто для Trust panels / API |
| **E3** | Global read p95 / miss-серии | Не закрыто #10599; отдельный перф при evidence |
| **E4** | filter-options 20s budget | **Сделано** #10599; мониторить regressions |

---

## Порядок внедрения

1. **PR-1 (Фаза A):** A1–A4 — ложные статусы/скоуп.  
2. **PR-2 (Фаза B):** B1–B8 — навигация/копирайт пакетом.  
3. **PR-3 (Фаза C):** C1–C6 — мелочь.  
4. **#10570:** live reproduce → query/recording fix при подтверждении.  
5. **Live-аудит 4–6** → дополнить план дефектами; затем #10571.  
6. **#10554** — последним.

Не поднимать `docker-compose.monitoring.yml` без явного запроса оператора.

---

## Ответы на открытые вопросы (зафиксировано)

| Вопрос | Ответ |
|--------|--------|
| Где SSOT? | `grafana/dashboards/*.json` |
| success vs trust-verdict? | Оба канала; UI различает |
| Preview-копии? | Не второй SSOT |
| 4–6 до live? | JSON-static (B4–B7) можно сейчас; live — обязателен для #10571 |

---

## DoD чеклист на dashboard-PR

- [ ] Diff только в `grafana/dashboards/*.json` (+ тесты/docs при смене семантики)
- [ ] `pytest tests/integration/test_dashboard_operator_readability.py`
- [ ] `pytest tests/integration/test_dashboard_first_window_noscroll.py`
- [ ] Нет заявления о полном audit PASS
- [ ] Refs на #10554 / дочерние issues в PR body

---

## Источники

- Черновик оператора 2026-09-22 (дашборды 0–3)
- Сверка JSON в checkout `origin/main`
- #10554, #10570, #10571 (open); #10557, #10568 (closed via #10599)
- `docs/reports/dashboard-ux-checks/2026-09-21.md`
- PR #10593, #10599
