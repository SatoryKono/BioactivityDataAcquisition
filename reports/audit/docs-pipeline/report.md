# Аудит docs-pipeline

| Поле | Значение |
| --- | --- |
| domain_id | `docs-pipeline` |
| prompt_id | `prompt.audit.docs-pipeline` v1.2.0 |
| HEAD | `5af9180c354e4406da4bfdf17d94d6c8efee6aaa` |
| Branch | `fix/stream-a-quality-9717` |
| MODE / AUDIT_MODE | `audit` / `full` |
| SCOPE | `scripts/docs/`, `mkdocs.yml`, `docs/` (tooling only) |
| surface_score | **2** / 3 |
| Дата | 2026-08-27 |
| Язык | ru |

Содержание/IA (Diátaxis, stale prose) — вне scope; см. `prompt.audit.docs-content`.

## Executive summary

Пайплайн документации **воспроизводим и закрыт в CI**: единый CLI `python -m scripts.docs`, `docs.yml` гоняет полный `check-links`, `verify`, `passports check` и architecture-тесты (включая API facades и `check_ai_surfaces`). GitHub Pages **намеренно unpublished** (`site_url` опущен; `docs.yml` — validation/build, не deploy). Рост вне nav закрыт unflagged `check-links --not-in-nav-growth` (baseline `scripts/engineering/baselines/not_in_nav_baseline.txt`, 276 путей).

Не score 3: каноническая one-command `verify` **не эквивалентна** unflagged `check-drift` и не зовёт packaged `build-site`; часть семантических проверок WARNING-only (exit 0); operator-guide отстаёт от флагов `verify`. Секретов в generators не найдено. P0/P1 нет.

## Карта пайплайна

| Шаг | Entrypoint | Inputs | Outputs | Caller | Failure |
| --- | --- | --- | --- | --- | --- |
| CLI router | `python -m scripts.docs` | argv | dispatch | local/CI | unknown command → help |
| Links / nav / growth | `scripts.docs.checks.check_links` | `docs/`, `mkdocs.yml`, baseline | stdout + optional JSON | `verify`, `docs.yml` validate-mkdocs, pre-commit (partial, manual) | exit 1 при violations |
| Drift | `scripts.docs.checks.check_drift` | src + docs | stdout / `--json` | `verify` (subset flags), weekly KPI, pre-commit (partial) | exit 1 только при ERROR |
| Docstrings | `check_docstrings --summary` | `src/` | stdout | `verify` | exit 1 |
| Cleanup inventory | `generate-cleanup-inventory --check` | tracked docs | generated inventory | `verify` | exit 1 при drift |
| Passports | `passports check` / `generate` | configs + src facts | `docs/04-reference/passports/` | `docs.yml` / nightly / release `--require-clean-source` | exit 1 stale/blocking |
| MkDocs | `python -m mkdocs` **или** `scripts.docs build-site` | `mkdocs.yml` | temp / `site/` / `docs/site/` | `verify` vs operator `build-site` | `--strict` |
| KPI / nav backlog | `check-kpi --fail-on-breach` | nav + baseline | `reports/docs-kpi/` | weekly only | hard limit 135 |
| Export | `generate-docs-export` | manifest | `docs/exports/*.merged.md` | **не в CI** | `--check` только unresolved |
| Publish | нет | — | — | GitHub Pages unpublished | n/a |

Цепочка SoT → generator → validation → artifact:

- Passports: configs/src → `passports generate` → tracked JSON/MD → `passports check` в PR.
- Matrix/dataflows: отдельные `--check` в `tests.yml` / `docs.yml` / `provider-contract-drift.yml`.
- MkDocs HTML: не публикуется; `docs/site/**` — local helper (policy), `mkdocs.yml site_dir: site` — другой путь.

## Controls, которые держат

1. Unflagged `check-links` включает links, specs, configs, contracts, workflow inventory, provider overview, governance, **not_in_nav_growth**, legacy-paths, local skill nav classification.
2. `docs.yml` `validate-mkdocs` ставит `uv-extras: docs` и `python -m scripts.docs verify` (в т.ч. strict mkdocs в temp dir).
3. `test_mkdocs_nav_references_existing_markdown_files`, `test_api_reference_public_facades`, `test_ai_runtime_governance_links` в job `docs-governance`.
4. Retired top-level shims удалены (#8043); router покрыт `test_docs_build_site_router.py`.
5. `validation.links.not_found: info` + skip `.png`/`.svg` в `check_links` — **задокументировано** в publication policy (диаграммы отдельно).

## Findings (PROVEN)

Полные поля — `findings.json`. Кратко:

| ID | Pri | Суть |
| --- | --- | --- |
| DOCS-PIPE-001 | P2 | `verify` зовёт `check-drift` без `--ai-surfaces`; не включает `check_providers`/`check_glossary` (только `run_all`) |
| DOCS-PIPE-002 | P2 | `verify` strict-build = `python -m mkdocs`, не `build-site`; `site_dir` в yaml = `site`, packaged default = `docs/site` |
| DOCS-PIPE-003 | P2 | `docs-verification.md` / `scripts/docs/README.md` описывают `verify` без `--modules` и как «in-repo helper chain» |
| DOCS-PIPE-004 | P2 | `check_providers` / `check_glossary` — WARNING; `main()` fail только по ERROR → exit 0 при семантическом drift |
| DOCS-PIPE-005 | P2 | `--modules` сканирует `02-architecture/*.md` (не nested), README, `03-guides`, `05-operations`; не `00-project`/`04-reference` |
| DOCS-PIPE-006 | P3 | `docs.yml` гоняет полный `check-links`, затем `verify` повторяет его |
| DOCS-PIPE-007 | P3 | `--report-json` пишет wall-clock timestamp и non-atomic `write_text` |
| DOCS-PIPE-008 | P3 | `generate-docs-export` использует `date.today()` (не UTC) и отсутствует в CI |
| DOCS-PIPE-009 | P3 | pre-commit docs hooks `stages: [manual]` и subset flags |
| DOCS-PIPE-010 | P3 | `passports` нет в `verify`; nightly `generate` без `--require-clean-source` (в `/tmp`, ок) vs release check |

## Top remediations

1. В `verify` передавать полный drift-набор (`--ai-surfaces`) либо unflagged `check-drift`; WARNING providers/glossary повысить до ERROR или явно исключить из «canonical chain» в README.
2. Strict-build в `verify` гнать через `python -m scripts.docs build-site --strict --site-dir <temp>`; согласовать `mkdocs.yml site_dir` и `03-file-policy.md`.
3. Синхронизировать `docs/03-guides/docs-verification.md` и `scripts/docs/README.md` с фактическими флагами `verify.py`.
4. Либо расширить `_module_docs_to_scan`, либо задокументировать bounded scope (и закрыть #9670 как README-already-in-scope).
5. Убрать дубль `check-links` в `docs.yml` (оставить `--report-json` **или** шаг внутри `verify`).
6. JSON-артефакты: фиксированный timestamp / omit + atomic replace.

Не предлагается: включать GitHub Pages; повышать KPI hard-limit 135; править mkdocs nav IA.

## Skipped checks

| Check | Причина |
| --- | --- |
| `python -m scripts.docs --help` / `check-links --not-in-nav-growth` live | Shell EPERM в этой сессии; CLI прочитан из `__main__.py` |
| Полный `mkdocs build --strict` | По условию аудита, если не quick; код пути inspect |
| Live GitHub Actions run | Не запрашивался; сверка workflow YAML |
| Secret scan сгенерированного HTML | Нет build output |
| Memory pre/post-task write | Read-only кроме report artifacts |

## Residual risk

- Operator, который гоняет только `verify`, не получит `--ai-surfaces` (CI pytest это ловит).
- Новый провайдер без упоминания в `providers/README.md` не завалит `check-drift`.
- Локальный `mkdocs build` без router оставит root `site/`, а `build-site` — `docs/site/`.
- Weekly KPI и PR growth используют **разные** exclusion prefixes — путаница backlog vs gate.

Debt budgets не менялись. `mkdocs.yml` не редактировался.
