# Codex Branches Summary — 2026-02-24 (04:11–09:11 UTC)

Анализ 34 веток `codex/*` за последние 5 часов.
Отобрано **18 веток с изменениями в коде** (`.py`, `.json`, `.yaml`).
Исключены 13 веток только с `.md` документацией и 3 пустые ветки (без diff от main).

---

## Группа 1: Метрики и Observability

**3 ветки, ~443 строк изменений, затрагивают domain/ports, application, infrastructure**

| Ветка | Файлы | Изменения | Суть |
|-------|-------|-----------|------|
| `codex/expand-metricsport-with-new-methods` | 14 .py | +260/−54 | Расширяет `MetricsPort` методами quarantine и DQ validation метрик. Обновляет `NoOpMetrics`, `PrometheusMetrics`, инструментирует `quarantine-manager`, `batch-metrics`, `data-quality-service`. Добавлены тесты. |
| `codex/enforce-single-canonical-mapping-end-to-end` | 4 .py, 1 .json | +148/−12 | Унифицирует маппинг состояний circuit breaker. Выделяет `circuit-breaker-mapping.py`, убирает дубликаты маппинга в `metrics.py` и `circuit-breaker.py`. Обновляет Grafana dashboard. Тесты добавлены. |
| `codex/update-metrics-implementation-instructions` | 2 .py, 1 .md | +35/−1 | Документирует policy расширения `MetricsPort`. Добавляет `record-custom-event` и `observe-pipeline-duration` в port и prometheus-реализацию. |

**Оценка:** Связанная группа — все три ветки расширяют систему метрик. `expand-metricsport` — основная, остальные дополняют. Потенциальные конфликты в `observability.py` и `prometheus-metrics.py` при мерже.

---

## Группа 2: Удаление deprecated кода

**4 ветки, ~866 строк удалено, затрагивают bootstrap, extractors, schemas**

| Ветка | Файлы | Изменения | Суть |
|-------|-------|-----------|------|
| `codex/remove-deprecated-code-from-bioetl` | 15 .py | −456 | Удаляет deprecated aliases и `DeprecationWarning` emissions из bootstrap (assembly, runtime, CLI), extractors (crossref, openalex, pubmed, semanticscholar), composite-config. Удаляет тесты deprecation warnings целиком. |
| `codex/remove-deprecated-code-in-bioetl` | 14 .py | +94/−321 | Аналогичная задача, но мягче: удаляет `DeprecationWarning` из compatibility paths, заменяет тесты deprecation на тесты alias bootstrap (`test-alias-bootstrap-functions.py`). |
| `codex/remove-deprecated-code-from-bioetl-oqx9dz` | 2 .py | +4/−15 | Точечное удаление deprecated `ArticleSchema` alias в PubMed schemas. |
| `codex/remove-deprecated-code-from-bioetl-6ecjp0` | 1 .py | +12/−60 | Рефакторинг `scripts/lint-terminology.py` — восстановление совместимости wrapper. |

**Оценка:** Ветки `remove-deprecated-code-from-bioetl` и `remove-deprecated-code-in-bioetl` — конкурирующие подходы к одной задаче. Первая удаляет жёстко (включая тесты), вторая — сохраняет alias-тесты. Нужно выбрать одну стратегию. Ветки `-oqx9dz` и `-6ecjp0` — самостоятельные точечные исправления.

---

## Группа 3: Cleanup мёртвого кода

**2 ветки, ~23 строки удалено, только infrastructure**

| Ветка | Файлы | Изменения | Суть |
|-------|-------|-----------|------|
| `codex/cleanup-dead-and-unused-code-3j1ahg` | 5 .py | −8 | Удаляет неиспользуемые импорты и no-op statements из infrastructure adapters/storage. |
| `codex/cleanup-dead-and-unused-code` | 5 .py | +5/−15 | Удаляет невозможные async-generator ветки (bare `return` after `yield`) в адаптерах crossref, openalex, semanticscholar, uniprot, filterable-mixin. |

**Оценка:** Безопасные, неконфликтующие cleanup-ы. Можно мержить оба.

---

## Группа 4: Рефакторинг PubMed Resume

**1 ветка, +76/−2, infrastructure + tests**

| Ветка | Файлы | Изменения | Суть |
|-------|-------|-----------|------|
| `codex/refactor-code-for-data-merging-after-reload-1sq8e7` | 2 .py | +76/−2 | Добавляет обработку resume offset в `pubmed-client.py` для пропуска уже обработанных записей при перезапуске. Тесты добавлены. |

**Оценка:** Самостоятельная фича. Остальные 3 ветки с тем же префиксом содержат только `.md` анализ (планы рефакторинга), поэтому исключены.

---

## Группа 5: Grafana дашборды

**6 веток, изменения только в `.json`, затрагивают `grafana/dashboards/`**

| Ветка | Файлы | Изменения | Суть |
|-------|-------|-----------|------|
| `codex/update-bioetl-provider-health-dashboard-dss28t` | 1 .json | +38/−11 | Добавляет repeating latency gauge panel. |
| `codex/add-datalinks-and-version-increment-in-dashboards` | 2 .json | +27/−4 | Добавляет cross-links между дашбордами, bump версий. |
| `codex/update-grafana-dashboard-panels` | 3 .json | +26/−132 | Компактная grid layout, упрощение header panels. |
| `codex/update-bioetl-provider-health-dashboard` | 1 .json | +106/−48 | Переход на provider label semantics. |
| `codex/update-gauge-panels-in-grafana-dashboards` | 2 .json | +6/−10 | Обновление DQ gauge thresholds. |
| `codex/update-grafana-dashboard-settings` | 1 .json | +3/−3 | Стандартизация defaults в bioetl-simple. |

**Оценка:** Высокий риск конфликтов — 5 из 6 веток трогают одни и те же JSON-файлы. Нужна последовательная интеграция с разрешением конфликтов.

---

## Группа 6: Naming Audit Config

**2 ветки, изменения в `.yaml` + `.md`**

| Ветка | Файлы | Изменения | Суть |
|-------|-------|-----------|------|
| `codex/conduct-naming-compliance-audit-r1a4c4` | 1 .yaml, 1 .md | +166/−1 | Naming exceptions config + audit report (путь: `docs/99-archive/reports/`). |
| `codex/conduct-naming-compliance-audit` | 1 .yaml, 1 .md | +134/−1 | Тот же naming exceptions config, отчёт в поддиректории `adr-024-naming-audit/`. |

**Оценка:** Дублирующие ветки. Различается только расположение отчёта. Выбрать одну.

---

## Сводная статистика

| Группа | Веток | Файлов | Добавлено | Удалено | Основные слои |
|--------|-------|--------|-----------|---------|---------------|
| Метрики | 3 | 21 | +443 | −67 | domain/ports, application, infrastructure |
| Deprecated | 4 | 32 | +110 | −852 | composition/bootstrap, application/pipelines |
| Cleanup | 2 | 10 | +5 | −23 | infrastructure/adapters |
| PubMed Resume | 1 | 2 | +76 | −2 | infrastructure/adapters/pubmed |
| Dashboards | 6 | 10 | +206 | −208 | grafana/dashboards |
| Naming Config | 2 | 4 | +300 | −2 | configs, docs |
| **Итого** | **18** | **79** | **+1140** | **−1154** | — |

## План консолидации

### Карта конфликтов (по файлам)

```
observability.py ─────── expand-metricsport ◄──► enforce-single-canonical
prometheus-metrics.py ── expand-metricsport ◄──► update-metrics-instructions
metrics.py ────────────── expand-metricsport ◄──► enforce-single-canonical

12 файлов bootstrap ──── remove-deprecated-from ◄══► remove-deprecated-in  (ВЗАИМОИСКЛЮЧАЮЩИЕ)

provider-health-v2.json ── update-provider-health ◄──► update-provider-health-dss28t
                                                  ◄──► update-grafana-dashboard-panels
                                                  ◄──► enforce-single-canonical-mapping
dq-v2.json ──────────────── add-datalinks ◄──► update-grafana-dashboard-panels
                                          ◄──► update-gauge-panels
overview-v2.json ────────── add-datalinks ◄──► update-grafana-dashboard-panels
                                          ◄──► update-gauge-panels
```

### Решения по дублирующимся веткам

| Пара | Выбор | Обоснование |
|------|-------|-------------|
| `remove-deprecated-from` vs `remove-deprecated-in` | **`remove-deprecated-in`** | Сохраняет alias-тесты (`test-alias-bootstrap-functions.py`) вместо удаления coverage. `remove-deprecated-from` удаляет `--init--.py` файлов пакетов — потенциально ломает импорты. |
| `conduct-naming-compliance-audit` vs `-r1a4c4` | **`-r1a4c4`** | Более свежая. YAML-структура проще (`adr-024-known-exceptions` vs `exception-registry`). Отчёт в плоской директории — консистентно с остальными отчётами. |

### Ветки к отклонению

| Ветка | Причина |
|-------|---------|
| `codex/remove-deprecated-code-from-bioetl` | Дублируется `remove-deprecated-in`, но агрессивнее — удаляет `--init--.py` и все тесты без замены |
| `codex/conduct-naming-compliance-audit` | Дублируется `-r1a4c4`, менее удобная структура YAML |

### Фазы интеграции

```
Фаза 1 ──┬── cleanup-dead-and-unused-code          (5 py, −15)
(cleanup) └── cleanup-dead-and-unused-code-3j1ahg   (5 py, −8)
              Нет пересечений между собой. Нет пересечений с другими фазами.
              Merge order: любой. Конфликты: нет.

Фаза 2 ──┬── remove-deprecated-code-in-bioetl       (14 py, +94/−321)
(deprec.) ├── remove-deprecated-code-from-bioetl-oqx9dz  (2 py, +4/−15)
          └── remove-deprecated-code-from-bioetl-6ecjp0   (1 py, +12/−60)
              Основная ветка: `-in-bioetl`. Точечные `-oqx9dz` и `-6ecjp0` не
              пересекаются с ней. Merge order: основная первой, потом точечные.
              Конфликты: нет (разные файлы).

Фаза 3 ──── refactor-code-for-data-merging-after-reload-1sq8e7  (2 py, +76/−2)
(pubmed)    Полностью изолирована (pubmed-client.py + тест).
            Конфликты: нет.

Фаза 4 ──┬── expand-metricsport-with-new-methods    (14 py, +260/−54)
(metrics) ├── enforce-single-canonical-mapping       (4 py + 1 json, +148/−12)
          └── update-metrics-implementation-instructions  (2 py + 1 md, +35/−1)
              Конфликтные файлы:
              • observability.py — expand-metricsport + enforce-single (оба добавляют методы)
              • prometheus-metrics.py — expand-metricsport + update-metrics (оба расширяют класс)
              • metrics.py — expand-metricsport + enforce-single (оба модифицируют)
              Merge order: expand-metricsport → enforce-single-canonical → update-metrics.
              Конфликты: ОЖИДАЮТСЯ в 3 файлах, ручное разрешение.

Фаза 5 ──┬── update-bioetl-provider-health-dashboard     (1 json, +106/−48)  ← базовая семантика
(grafana) ├── update-bioetl-provider-health-dashboard-dss28t  (1 json, +38/−11)
          ├── update-grafana-dashboard-panels              (3 json, +26/−132)
          ├── add-datalinks-and-version-increment          (2 json, +27/−4)
          ├── update-gauge-panels-in-grafana-dashboards    (2 json, +6/−10)
          └── update-grafana-dashboard-settings            (1 json, +3/−3)  ← изолирована
              Конфликтная матрица:
              • provider-health-v2.json: 3 ветки + enforce-single из Фазы 4
              • dq-v2.json: 3 ветки
              • overview-v2.json: 3 ветки
              • bioetl-simple.json: только update-grafana-dashboard-settings
              Merge order: provider-health (baseline) → dss28t (gauge) →
                dashboard-panels (layout) → datalinks → gauge-panels → settings.
              Конфликты: ГАРАНТИРОВАНЫ в JSON. Рекомендация — после первого мержа
              rebas'ить оставшиеся и разрешать по одной.

Фаза 6 ──── conduct-naming-compliance-audit-r1a4c4  (1 yaml + 1 md, +166/−1)
(naming)    Изолирована. Конфликты: нет.
```

### Визуальная последовательность

```
main ─── Фаза 1 (cleanup) ─── Фаза 2 (deprecated) ─── Фаза 3 (pubmed) ───┐
         2 ветки, 0 конфл.     3 ветки, 0 конфл.       1 ветка, 0 конфл.  │
                                                                            │
    ┌───────────────────────────────────────────────────────────────────────┘
    │
    └─── Фаза 4 (metrics) ──── Фаза 5 (grafana) ──── Фаза 6 (naming) ─── ✓
         3 ветки, ~3 конфл.     6 веток, ~8 конфл.    1 ветка, 0 конфл.
```

### Итого

| Метрика | Значение |
|---------|----------|
| Веток к интеграции | 16 из 18 (2 отклонены как дубли) |
| Фаз | 6 |
| Ожидаемых конфликтов | ~11 (3 в метриках, ~8 в дашбордах) |
| Безконфликтных фаз | 4 из 6 (фазы 1–3, 6) |
| Фаз с ручным разрешением | 2 (фазы 4, 5) |

### Рекомендации

1. **Фазы 1–3** можно выполнить автоматически (merge --no-ff) без ручного вмешательства.
2. **Фаза 4 (metrics)** — после мержа `expand-metricsport`, rebase двух оставшихся веток на main и разрешить конфликты в `observability.py`, `prometheus-metrics.py`, `metrics.py`.
3. **Фаза 5 (grafana)** — наиболее трудоёмкая. JSON-конфликты плохо мержатся автоматически. Альтернатива: взять самую полную ветку (`update-grafana-dashboard-panels`) как базу и cherry-pick отдельных изменений из остальных.
4. **Тесты** — после каждой фазы прогонять `pytest tests/architecture/ -v` и `pytest tests/unit/ -x`.
5. **Параллелизация** — фазы 1–3 можно мержить параллельно (нет пересечений), затем merge main в рабочую ветку и продолжить фазы 4–6 последовательно.
