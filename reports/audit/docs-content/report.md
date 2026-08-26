# Docs content audit — BioETL

| Field | Value |
| --- | --- |
| domain_id | `docs-content` |
| prompt_id | `prompt.audit.docs-content` |
| version | 1.2.0 |
| MODE | `audit` |
| AUDIT_MODE | `full` |
| LANGUAGE | `ru` |
| SCOPE | `README.md docs/` |
| REQUIRE_GH_TRACKING | `false` |
| date | 2026-08-26 |
| surface_score | **2** (main path documented; material local drift) |
| blocked | `false` |
| debt_outcome | `unchanged` (read-only; budgets not touched) |
| proven_findings | 18 |
| P0 | 0 |
| P1 | 2 |
| P2 | 8 |
| P3 | 8 |

## Executive summary

Документация как интерфейс между кодом и операторами **в целом работоспособна**: README формулирует назначение, Local-Only (ADR-010), Python 3.12 baseline, 22 entity-пайплайна, coverage gate 85%, и есть опубликованный путь верификации (`docs/03-guides/docs-verification.md`, `python -m scripts.docs verify`). Каталог пайплайнов совпадает с `configs/entities/`. Опасные `rm -rf` в retention runbook помечены как **Disallowed**.

Главный разрыв — **несогласованность first-run процедуры** с default `required_persistence_profile=replay_ready` и **Windows bootstrap в CONTRIBUTING**. Это P1: чистый checkout может не воспроизвести «первый пайплайн» и смешанный Windows-путь из CONTRIBUTING расходится с `.venv-win`.

Остальное — drift CLI/API (нет `bioetl report` в cli.md; нет `application.ports` в API table), противоречие requiredness OpenAlex, неполный threat model в SECURITY.md, stale Last verified.

## Checklist (sample)

| Item | Result |
| --- | --- |
| README states project purpose | PASS — BioETL / Medallion / Delta Lake / Local-First |
| Bootstrap path from clean checkout | PARTIAL — uv/make paths exist; extras and first-run flags disagree |
| Commands match manifests/CI | PARTIAL — Python 3.12 CI default matches; `make lint` weaker than CI mypy `--strict` |
| Required env vars documented (no secret values) | PARTIAL — tables exist; OpenAlex requiredness contradicts; no live secrets in sampled docs |
| Links resolve; runtime versions vs CI | PARTIAL — sampled README/00-map links exist; full `check-links` skipped (no shell). CI Python 3.12 matches docs baseline. CLI doc version 6.1.4 ≠ package 6.1.0 |
| API reference vs schema/code | FAIL — `application.ports` (ADR-058) missing from API table; source map still points at `execution_api.py` |
| No dangerous/stale deploy/runbook steps | PASS for sampled destructive commands (`rm -rf` explicitly disallowed). K8s guide is experimental but stale (P3) |
| TODO/FIXME/TBD in ops/security without owner | PASS — no unowned TODO/FIXME/TBD in `docs/05-operations/**` or `docs/security/**` (archive TBD is historical) |
| Contradictory instructions across two docs | FAIL — first-run flags, OpenAlex requiredness, bootstrap extras, Windows venv |

## Surface score

**2 / 3** — основной путь описан и частично сверен с манифестами; есть автоматизация docs gates, но first-run/Windows contributor path и API/CLI drift — материальные пробелы.

Mapping: domain table «Main path correct; some stale or missing sections». Не 1, потому что SoT-навигатор, pipeline catalog, docs-verification и ADR-010 согласованы; не 3, потому что first-run и contributor Windows path не воспроизводимы по букве онбординга.

## Inventory (SCOPE)

Опубликованная поверхность `docs/00-05` + README + inventory extras (CONTRIBUTING, SECURITY, CHANGELOG). Полный file-count не использовался как метрика.

| Surface | Audience | SoT / related | Last verified (header) | Status |
| --- | --- | --- | --- | --- |
| `README.md` | public / eng | purpose, bootstrap, env table | n/a (no header) | current narrative; first-run/lint extras drift |
| `docs/00-project/00-map.md` | all | navigator | 2026-08-14 (body 2026-08-25) | header stale vs subtitle |
| `docs/00-project/RULES.md` | governance | constitution v6.1.11 | 2026-08-25 | current |
| `docs/00-project/TOOLS.md` | eng | uv extra-sets | 2026-08-20 | current |
| `docs/03-guides/getting-started.md` | onboarding | tutorial | 2026-07-30 | P1 first-run |
| `docs/03-guides/quick-start.md` | onboarding | how-to | 2026-06-19 | extras + flags |
| `docs/03-guides/docs-verification.md` | docs | how-to | 2026-08-20 | current |
| `docs/03-guides/testing.md` | eng | how-to | 2026-06-19 | header after body |
| `docs/03-guides/running-pipelines.md` | ops | how-to | 2026-04-28 | Быстрый старт vs later replay_ready |
| `docs/03-guides/cheatsheets/cli-commands.md` | ops | how-to | 2026-07-28 | first-live-run correct; missing `report` |
| `docs/04-reference/cli.md` | ops | reference | 2026-07-06 | missing `report`; version 6.1.4 |
| `docs/04-reference/pipeline-catalog.md` | eng | reference | 2026-07-23 | counts match 22+5 |
| `docs/04-reference/api/*` | eng | reference | 2026-03-29 | ports/entrypoints drift |
| `docs/04-reference/environment-variables.md` | eng | reference | n/a | OpenAlex Required=No |
| `docs/05-operations/runbooks/` | ops | runbooks | mostly 2026-03/04 | index stale |
| `.github/CONTRIBUTING.md` | contributors | how-to | n/a | Windows `.venv` |
| `.github/SECURITY.md` | security | policy | n/a | providers incomplete |
| `docs/05-engineering/` | n/a | stub | 2026-08-04 | correctly stubbed |

Diátaxis (ориентир): tutorials = getting-started/quick-start; how-to = running-pipelines/docs-verification/runbooks; reference = cli/api/pipeline-catalog/env; explanation = RULES/ADRs/architecture.

## Verified claims (PASS)

- Purpose, Medallion, Local-Only ADR-010, hexagonal layers — README согласован с архитектурой.
- **22** provider/entity YAML + **5** composite entity YAML + **5** `configs/composites/*.yaml` + **7** providers — совпадает с `docs/04-reference/pipeline-catalog.md` и деревом `configs/entities/`.
- Python: `pyproject.toml` `requires-python = ">=3.12"`, classifiers 3.12/3.13; `.github/actions/setup-python-uv` default **3.12**; `tests.yml` pins 3.12. README 3.12 baseline / 3.12+3.13 supported — OK.
- Coverage badge ≥85% совпадает с `Makefile` `test` `--cov-fail-under=85` и CI comments in `pyproject.toml`.
- Package version `6.1.0` совпадает с README badge (unreleased) и CHANGELOG `[Unreleased]`.
- `python -m scripts.engineering.dev setup-mcp` — публичный роутер на `scripts.ai.codex.setup_mcp` (не два разных инструмента).
- `python -m scripts.engineering.dev run-tests` существует в `scripts/engineering/dev/__main__.py`.
- Quarantine Explorer / Loki / Tempo сняты с shipping — README, dashboards, runbook 2026-07-23 согласованы.
- Retention `rm -rf data/` и т.п. — секция **Disallowed pattern**, не инструкция.
- `docs/05-engineering/` — явный stub, не новый SSOT.

## Findings (PROVEN, max 18 listed)

См. `findings.json`. Кратко:

| ID | Pri | Path | Observation |
| --- | --- | --- | --- |
| AUD-DOCS-001 | P1 | `docs/03-guides/getting-started.md:217` | First-run без `degraded_observable` при default `replay_ready` |
| AUD-DOCS-002 | P1 | `.github/CONTRIBUTING.md:12` | Windows fallback `.venv` + extras `[dev,tests]` |
| AUD-DOCS-003 | P2 | `docs/03-guides/quick-start.md:45` | Два «canonical» extra-set vs `make install` |
| AUD-DOCS-004 | P2 | `Makefile:107` | `make lint` слабее CI `mypy --strict` |
| AUD-DOCS-005 | P2 | `docs/04-reference/cli.md:52` | Нет `bioetl report` в CLI reference |
| AUD-DOCS-006 | P2 | `docs/04-reference/api/application.md:33` | Нет `application.ports` (ADR-058) |
| AUD-DOCS-007 | P2 | `docs/04-reference/environment-variables.md:26` | OpenAlex key Required=No vs provider spec Да |
| AUD-DOCS-008 | P2 | `.github/SECURITY.md:7` | Threat model без OpenAlex/CrossRef/S2 |
| AUD-DOCS-009 | P2 | `docs/03-guides/testing.md:1` | Контент до header; Last verified 2026-06-19 |
| AUD-DOCS-010 | P2 | `src/bioetl/README.md:14` | Bootstrap → `execution_api.py` вместо `entrypoints.py` |
| AUD-DOCS-011 | P3 | `docs/04-reference/cli.md:3` | CLI Version 6.1.4 vs package 6.1.0 |
| AUD-DOCS-012 | P3 | `README.md:264` | `BIOETL_DATA_DIR` default `data` vs `./data` |
| AUD-DOCS-013 | P3 | `docs/00-project/00-map.md:107` | Language policy: `AGENT.md` (нет такого sibling) |
| AUD-DOCS-014 | P3 | `docs/04-reference/api/index.md:10` | API Last verified 2026-03-29 |
| AUD-DOCS-015 | P3 | `docs/05-operations/runbooks/index.md:12` | Runbook index Last verified 2026-04-01 |
| AUD-DOCS-016 | P3 | `docs/03-guides/quick-start.md:108` | `--no-cached-bronze` только в quick-start |
| AUD-DOCS-017 | P3 | `docs/00-project/00-map.md:10` | Last verified 2026-08-14 vs updated 2026-08-25 |
| AUD-DOCS-018 | P3 | `docs/05-operations/deployment/deployment-guide.md:10` | Experimental K8s guide Last verified 2026-03-29 |

Live fail-closed первого пайплайна **не исполнялся** (нет shell). Код default + validator + cheatsheet достаточны для PROVEN противоречия инструкций; фактический RuntimeError на чистом checkout — высокий confidence, не live-proof.

## Top remediations

1. Унифицировать first-run: `--required-persistence-profile degraded_observable` в getting-started, quick-start, README, running-pipelines «Быстрый старт».
2. Исправить CONTRIBUTING Windows fallback на `.venv-win` и extras `dev,tests,tracing`.
3. Развести extra-sets в quick-start: tracing bootstrap vs `make install` (`tests_full,export`).
4. Выровнять `make lint` с CI `mypy --strict --no-incremental` или явно пометить subset.
5. Добавить `bioetl report` в `docs/04-reference/cli.md` и cheatsheet.
6. Добавить `application.ports` в API application.md; поправить `src/bioetl/README.md` на `entrypoints.py`.
7. Согласовать OpenAlex requiredness; дополнить SECURITY.md провайдерами.
8. Починить testing.md header; bump Last verified на API/runbooks/00-map/cli.

## Skipped checks

- Memory `pre-task` / `post-task` — в этой runtime-сессии нет shell.
- `uv run python -m scripts.docs check-links|check-drift|verify` — нет shell; broken links ниже — только sampled inspection.
- Live `bioetl run --pipeline chembl_activity --limit 100`.
- `git log` last_change.
- GitHub issues (`REQUIRE_GH_TRACKING=false`).
- `.env` не изменялся; секреты в отчёт не копировались.
- Tech-debt budgets не менялись.

## Kit extras

- `docs-inventory.csv`
- `broken-links.json`
- `stale-docs.csv`
- `docs-code-drift.csv`

## Guardrails

- Product code not edited.
- `.env` not touched.
- Tech-debt budgets not raised.
- Docs-pipeline (MkDocs build) not in scope.
