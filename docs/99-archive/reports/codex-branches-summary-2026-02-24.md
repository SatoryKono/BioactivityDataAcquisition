# Codex Branches Summary — 2026-02-24 (04:11–09:11 UTC)

Анализ 34 веток `codex/*` за последние 5 часов.
Отобрано **18 веток с изменениями в коде** (`.py`, `.json`, `.yaml`).
Исключены 13 веток только с `.md` документацией и 3 пустые ветки (без diff от main).

---

## Группа 1: Метрики и Observability

**3 ветки, ~443 строк изменений, затрагивают domain/ports, application, infrastructure**

| Ветка | Файлы | Изменения | Суть |
|-------|-------|-----------|------|
| `codex/expand-metricsport-with-new-methods` | 14 .py | +260/−54 | Расширяет `MetricsPort` методами quarantine и DQ validation метрик. Обновляет `NoOpMetrics`, `PrometheusMetrics`, инструментирует `quarantine_manager`, `batch_metrics`, `data_quality_service`. Добавлены тесты. |
| `codex/enforce-single-canonical-mapping-end-to-end` | 4 .py, 1 .json | +148/−12 | Унифицирует маппинг состояний circuit breaker. Выделяет `circuit_breaker_mapping.py`, убирает дубликаты маппинга в `metrics.py` и `circuit_breaker.py`. Обновляет Grafana dashboard. Тесты добавлены. |
| `codex/update-metrics-implementation-instructions` | 2 .py, 1 .md | +35/−1 | Документирует policy расширения `MetricsPort`. Добавляет `record_custom_event` и `observe_pipeline_duration` в port и prometheus-реализацию. |

**Оценка:** Связанная группа — все три ветки расширяют систему метрик. `expand-metricsport` — основная, остальные дополняют. Потенциальные конфликты в `observability.py` и `prometheus_metrics.py` при мерже.

---

## Группа 2: Удаление deprecated кода

**4 ветки, ~866 строк удалено, затрагивают bootstrap, extractors, schemas**

| Ветка | Файлы | Изменения | Суть |
|-------|-------|-----------|------|
| `codex/remove-deprecated-code-from-bioetl` | 15 .py | −456 | Удаляет deprecated aliases и `DeprecationWarning` emissions из bootstrap (assembly, runtime, CLI), extractors (crossref, openalex, pubmed, semanticscholar), composite_config. Удаляет тесты deprecation warnings целиком. |
| `codex/remove-deprecated-code-in-bioetl` | 14 .py | +94/−321 | Аналогичная задача, но мягче: удаляет `DeprecationWarning` из compatibility paths, заменяет тесты deprecation на тесты alias bootstrap (`test_alias_bootstrap_functions.py`). |
| `codex/remove-deprecated-code-from-bioetl-oqx9dz` | 2 .py | +4/−15 | Точечное удаление deprecated `ArticleSchema` alias в PubMed schemas. |
| `codex/remove-deprecated-code-from-bioetl-6ecjp0` | 1 .py | +12/−60 | Рефакторинг `scripts/lint_terminology.py` — восстановление совместимости wrapper. |

**Оценка:** Ветки `remove-deprecated-code-from-bioetl` и `remove-deprecated-code-in-bioetl` — конкурирующие подходы к одной задаче. Первая удаляет жёстко (включая тесты), вторая — сохраняет alias-тесты. Нужно выбрать одну стратегию. Ветки `-oqx9dz` и `-6ecjp0` — самостоятельные точечные исправления.

---

## Группа 3: Cleanup мёртвого кода

**2 ветки, ~23 строки удалено, только infrastructure**

| Ветка | Файлы | Изменения | Суть |
|-------|-------|-----------|------|
| `codex/cleanup-dead-and-unused-code-3j1ahg` | 5 .py | −8 | Удаляет неиспользуемые импорты и no-op statements из infrastructure adapters/storage. |
| `codex/cleanup-dead-and-unused-code` | 5 .py | +5/−15 | Удаляет невозможные async-generator ветки (bare `return` after `yield`) в адаптерах crossref, openalex, semanticscholar, uniprot, filterable_mixin. |

**Оценка:** Безопасные, неконфликтующие cleanup-ы. Можно мержить оба.

---

## Группа 4: Рефакторинг PubMed Resume

**1 ветка, +76/−2, infrastructure + tests**

| Ветка | Файлы | Изменения | Суть |
|-------|-------|-----------|------|
| `codex/refactor-code-for-data-merging-after-reload-1sq8e7` | 2 .py | +76/−2 | Добавляет обработку resume offset в `pubmed_client.py` для пропуска уже обработанных записей при перезапуске. Тесты добавлены. |

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

## Рекомендации по интеграции

1. **Начать с Cleanup** (группа 3) — минимальный риск, нет конфликтов.
2. **Deprecated код** (группа 2) — определиться между жёстким удалением (`remove-deprecated-code-from-bioetl`) и мягким (`remove-deprecated-code-in-bioetl`). Точечные ветки `-oqx9dz` и `-6ecjp0` независимы.
3. **Метрики** (группа 1) — мержить `expand-metricsport` первой, затем `enforce-single-canonical-mapping`, в конце `update-metrics-implementation-instructions`.
4. **PubMed Resume** (группа 4) — независимая, мержить в любой момент.
5. **Дашборды** (группа 5) — мержить последовательно, начиная с `update-bioetl-provider-health-dashboard` (baseline семантика), затем остальные.
6. **Naming Config** (группа 6) — выбрать одну из двух веток (`-r1a4c4` предпочтительнее — более свежая).
