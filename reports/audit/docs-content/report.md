# Docs content audit

- **Prompt:** `prompt.docs.audit` 1.2.0
- **MODE:** `audit` (патчи не предлагались)
- **AUDIT_MODE:** `full`
- **LANGUAGE:** `ru`
- **SCOPE:** `README.md`, `docs/`, плюс contributor/security surfaces из чеклиста (`CONTRIBUTING.md`, `.github/CONTRIBUTING.md`, `.github/SECURITY.md`, `CHANGELOG.md`, `LICENSE`)
- **Дата:** 2026-09-15
- **surface_score:** **2** (основной путь верный; есть локальные противоречия и устаревшие фрагменты)
- **Маппинг 0–5:** completeness 4, freshness 3, consistency 3, reproducibility 4 → среднее 3.5 → score 2

Документация как интерфейс между кодом и людьми: цель проекта, uv-bootstrap, Local-Only (ADR-010) и каталог 22+5 пайплайнов воспроизводимы. Автоматические гейты ссылок/drift зелёные. Расхождения — в именовании extra-set, Python-матрице релиза и укороченных lint/docs-check рецептах.

Генераторы MkDocs / publish pipeline **не** входили в этот проход (`prompt.audit.docs-pipeline`).

## Чеклист

- [x] README формулирует назначение проекта (bioactivity ETL → Delta Lake)
- [x] Bootstrap с чистого clone описан (`uv sync` + `python -m scripts.ops setup-plugins`); Windows/WSL разделены (`.venv-win`)
- [x] Команды сверки с манифестами: `pyproject.toml` version `6.1.0`, `requires-python >=3.12`, extras и `Makefile` targets существуют
- [x] Required env: `.github/SECURITY.md` задаёт префикс `BIOETL_{PROVIDER}_{KEY}` без значений секретов
- [x] Относительные ссылки: `check-links --links --specs --configs` exit 0 (2026-09-15T10:56:05Z)
- [x] API/reference не расходились с gated `check-drift` (ports/classes/full/mirrors) exit 0
- [x] Опасного prod-deploy в активных runbooks не найдено; default — Local-Only; Docker помечен как adjunct
- [x] Cleanup inventory `--check` синхронизирован; этот аудит **не** правил Owner/Status/Class и ссылки

## Гейты (командное доказательство)

| Команда | UTC | exit |
| --- | --- | ---: |
| `python -m scripts.docs check-links --links --specs --configs --report-json reports/audit/docs-content/check-links-report.json` | 2026-09-15T10:56:05Z | 0 |
| `python -m scripts.docs check-drift --json` | 2026-09-15T10:56:20Z | 0 |
| `python -m scripts.docs check-drift --ports --classes --json` | 2026-09-15T10:56:27Z | 0 |
| `python -m scripts.docs check-drift --runtime-mirrors --freshness --json` | 2026-09-15T10:56:30Z | 0 |
| `python -m scripts.docs generate-cleanup-inventory --check` | 2026-09-15T10:56:30Z | 0 |

## Находки (PROVEN, по приоритету)

| ID | P | Суть |
| --- | --- | --- |
| DOCS-001 | P2 | `quick-start.md` отождествляет `uv sync --extra tracing` и `make install` (другой набор extras) |
| DOCS-002 | P2 | Диаграмма релиза всё ещё пишет Python 3.11; `release.yml` — только 3.13, `tests.yml` — 3.12 |
| DOCS-003 | P3 | README `ruff check .` ≠ `Makefile` `ruff check src tests scripts` |
| DOCS-004 | P3 | Runbook recovery: `Last verified: 2026-04-03` |
| DOCS-005 | P3 | README docs-check не включает `--runtime-mirrors --freshness` |

Полные поля: `findings.json`.

## Что проверено и совпало

- 22 provider-entity + 5 composite YAML = `docs/04-reference/pipeline-catalog.md` и glob `configs/entities/**/*.yaml`.
- `python -m scripts.ops setup-plugins` и `python -m scripts.engineering.dev setup-mcp` существуют; второй — роутер на `scripts.ai.codex.setup_mcp`.
- `python -m bioetl` задан в `[project.scripts]`.
- `SUPPORT.md` в корне нет — P3 community-file, не ломает bootstrap.

## Diátaxis (активный слой)

| Роль | Где |
| --- | --- |
| Tutorial | `docs/03-guides/quick-start.md`, `getting-started.md`, README Quick Start |
| How-to | `docs-verification.md`, `.github/CONTRIBUTING.md`, `docs/05-operations/**` |
| Reference | RULES, REQUIREMENTS, pipeline-catalog, CLI, ADR |
| Explanation | `00-map.md`, architecture inventory/diagrams, github-workflow-diagrams |

## Remediation (без применения в этом MODE)

1. Развести extras в `quick-start.md` как в README (DOCS-001, S).
2. Убрать 3.11 из mermaid релиза (DOCS-002, S).
3. В README lint/docs-check сослаться на `make lint` и `docs-verification.md` (DOCS-003/005, S).
4. Перепройти recovery runbook и обновить `Last verified` (DOCS-004, M).

`MODE=propose-patches` не включался.

## Skips

- Полный пересчёт всех markdown в `docs/99-archive/` (не нормативный слой).
- MkDocs build / publish (`prompt.audit.docs-pipeline`).
- End-to-end прогон recovery runbook (только штамп свежести).
- GitHub issues (`REQUIRE_GH_TRACKING=false`).
- Правки docs (audit-only).

## Артефакты

- `reports/audit/docs-content/report.md`
- `reports/audit/docs-content/findings.json`
- `reports/audit/docs-content/docs-inventory.csv`
- `reports/audit/docs-content/broken-links.json`
- `reports/audit/docs-content/stale-docs.csv`
- `reports/audit/docs-content/docs-code-drift.csv`
- служебные: `check-links-report.json`, `check-drift-*.json`
