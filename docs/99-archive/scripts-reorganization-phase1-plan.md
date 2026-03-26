# Plan Reorganization of Scripts - Phase 1

*Status: archived | Archived on: 2026-03-26 | Reason: historical working plan moved from repository root during cleanup*

This document is preserved as a historical planning artifact. It is not normative
for current repository behavior.

---

# План реорганизации скриптов — Фаза 1

## Скрипты по расписанию → `scripts/scheduled-{domain}/`

### Концепция именования

Формат: `scheduled-{текущее_название_группы}`.
Это отражает периодичность (scheduled) и сохраняет предметную область.

---

### 1.1 `scripts/scheduled-diagrams/` (из `scripts/diagrams/`)

**Workflow:** `diagram-nightly.yml` (cron: `20 2 * * *` → по заданию меняем на еженедельный)

Перечень скриптов, вызываемых **ТОЛЬКО** из nightly workflow:

| # | Скрипт | Что проверяет | Расписание |
|---|--------|---------------|------------|
| 1 | `run_diagram_nightly_suite.py` | Phase 2 nightly suite (DIAG-T024..T029): render integrity, class method render, padding, PDF image bounds. Агрегирует результаты в JSON/MD отчёт | cron (nightly → weekly) |
| 2 | `enforce_diagram_quality_budget.py` | Бюджет качества диаграмм: проверяет max hard failures, max DIAG-T022/T023, max lint errors, max nightly errors/warnings. Fail CI при превышении | cron, после всех nightly checks |
| 3 | `check_diagram_visual_smoke.py` | Visual smoke baseline drift (DIAG-T026): сравнение rendered SVG с baseline manifest. Обнаруживает визуальный регресс | cron (nightly → weekly) |

**НЕ переносятся** — используются и в pre-commit, и в PR CI, и в nightly:
- `lint_diagrams.py` — pre-commit hook + nightly
- `check_diagram_artifacts.py` — nightly + PR
- `check_svg_text_visibility.py` — nightly + PR canary
- `check_diagram_quality_gates.py` — nightly + PR
- `validate_mermaid_syntax.sh` — nightly canary + PR
- `prune_orphan_nodes.py` — pre-commit hook

**Почему именно эти 3:** grep по всем workflows и `.pre-commit-config.yaml` показал, что остальные diagram-скрипты вызываются из нескольких контекстов. Эти 3 — исключительно nightly.

---

### 1.2 `scripts/scheduled-ci/` (из `scripts/ci/`)

**Workflow:** `quality-debt-weekly.yml` (cron: `45 4 * * 1`, каждый понедельник)

| # | Скрипт | Что проверяет | Расписание |
|---|--------|---------------|------------|
| 1 | `report_quality_debt_weekly.py` | Еженедельный снимок архитектурного долга: total/expired/new exemptions, growth violations по scorecard, integral score по quarters. Выход: JSON + MD | Понедельник 04:45 UTC |

**НЕ переносятся** из `scripts/ci/`:
- `run_pytest_resilient.py` — push/PR (event-based)
- `quality_integral_gate.py` — push/PR (event-based)
- `check_e2e_matrix_skip_rate.py` — и schedule, и push/PR (dual-context)
- `check_e2e_rerun_stability.py` — не используется ни одним workflow (orphan?)

---

### 1.3 `scripts/scheduled-docs/` (из `scripts/docs/`)

**Workflow:** `docs-kpi-weekly.yml` (cron: `30 4 * * 1`, каждый понедельник)

| # | Скрипт | Что проверяет | Расписание |
|---|--------|---------------|------------|
| 1 | `report_docs_kpi.py` | Еженедельные KPI документации: количество страниц не в mkdocs nav, orphan pages, прогресс к deadline. Fail при breach of hard limits | Понедельник 04:30 UTC |

---

### 1.4 `scripts/scheduled-data/` — **ОТМЕНЯЕТСЯ**

`vacuum.yml` вызывает `bioetl maintenance vacuum-all` (CLI command), а не
`scripts/data/vacuum_delta.py`. Скрипт `vacuum_delta.py` — standalone утилита
для ручного запуска, а не scheduled. Переносить не нужно.

---

### 1.5 Новый скрипт: `scripts/scheduled-ci/report_quality_debt_changed.py`

**Требование:** аналог `report_quality_debt_weekly.py`, запускаемый при изменении кода.

**Логика:**
1. Получает список изменённых файлов через `git diff --name-only origin/main...HEAD`
2. Маппит файлы на модули BioETL (`src/bioetl/domain/` → domain, и т.д.)
3. Фильтрует exemptions registry по затронутым модулям/слоям
4. Генерирует инкрементальный debt snapshot (только по затронутым areas)
5. Выводит JSON + MD отчёт

**Интеграция:** Добавить step в `tests.yml` (smoke-check job) или отдельный workflow с trigger `on: push/pull_request`.

---

### Полный список команд переноса

```bash
# === 1.1 scheduled-diagrams ===
mkdir -p scripts/scheduled-diagrams
git mv scripts/diagrams/run_diagram_nightly_suite.py scripts/scheduled-diagrams/
git mv scripts/diagrams/enforce_diagram_quality_budget.py scripts/scheduled-diagrams/
git mv scripts/diagrams/check_diagram_visual_smoke.py scripts/scheduled-diagrams/

# === 1.2 scheduled-ci ===
mkdir -p scripts/scheduled-ci
git mv scripts/ci/report_quality_debt_weekly.py scripts/scheduled-ci/

# === 1.3 scheduled-docs ===
mkdir -p scripts/scheduled-docs
git mv scripts/docs/report_docs_kpi.py scripts/scheduled-docs/
```

### Обновления ссылок после переноса

#### A. GitHub workflows (обновить пути)

| Файл | Старый путь | Новый путь |
|------|-------------|------------|
| `.github/workflows/diagram-nightly.yml` | `scripts/diagrams/run_diagram_nightly_suite.py` | `scripts/scheduled-diagrams/run_diagram_nightly_suite.py` |
| `.github/workflows/diagram-nightly.yml` | `scripts/diagrams/enforce_diagram_quality_budget.py` | `scripts/scheduled-diagrams/enforce_diagram_quality_budget.py` |
| `.github/workflows/diagram-nightly.yml` | `scripts/diagrams/check_diagram_visual_smoke.py` | `scripts/scheduled-diagrams/check_diagram_visual_smoke.py` |
| `.github/workflows/quality-debt-weekly.yml` | `scripts/ci/report_quality_debt_weekly.py` | `scripts/scheduled-ci/report_quality_debt_weekly.py` |
| `.github/workflows/docs-kpi-weekly.yml` | `scripts/docs/report_docs_kpi.py` | `scripts/scheduled-docs/report_docs_kpi.py` |
| `.github/workflows/diagram-nightly.yml` | cron: `20 2 * * *` (daily) | cron: `20 2 * * 0` (weekly, Sunday) |

#### B. `scripts/catalog.yaml` — добавить 3 новые группы

```yaml
scheduled-diagrams:
  path: scripts/scheduled-diagrams
  purpose: Scheduled (weekly) diagram regression, quality budget, visual smoke

scheduled-ci:
  path: scripts/scheduled-ci
  purpose: Scheduled (weekly) architecture debt snapshots and on-change debt analysis

scheduled-docs:
  path: scripts/scheduled-docs
  purpose: Scheduled (weekly) documentation KPI metrics
```

#### C. Makefile — обновить targets (если есть ссылки на перенесённые скрипты)

#### D. `configs/quality/scripts_inventory_manifest.json` — обновить пути

#### E. `__main__.py` — создать dispatcher для каждой новой группы

#### F. `scripts/diagrams/__main__.py` — убрать записи о перенесённых скриптах

#### G. `scripts/ci/__main__.py` и `scripts/docs/__main__.py` — убрать записи

---

### Резюме Phase 1

| Действие | Количество |
|----------|-----------|
| Новых папок | 3 (`scheduled-diagrams`, `scheduled-ci`, `scheduled-docs`) |
| Перенесённых скриптов | 5 (3 diagrams + 1 ci + 1 docs) |
| Новых скриптов | 1 (`report_quality_debt_changed.py`) |
| Обновлений workflows | 3 файла |
| Обновлений catalog | 1 файл |
| Обновлений manifest | 1 файл |
| Новых `__main__.py` | 3 файла |

---

**Жду подтверждения для выполнения Phase 1.**
