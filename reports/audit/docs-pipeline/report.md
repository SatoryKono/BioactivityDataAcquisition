# Docs pipeline audit

| Field | Value |
| --- | --- |
| domain_id | `docs-pipeline` |
| prompt_id | `prompt.audit.docs-pipeline` |
| MODE | `audit` / `AUDIT_MODE=full` |
| LANGUAGE | `ru` |
| BASE | `main` |
| REPO | `SatoryKono/BioactivityDataAcquisition` |
| surface_score | **2** (acceptable: pipeline воспроизводим; часть semantic checks и publish metadata ещё дырявые) |
| findings | 12 (все `PROVEN`; P0/P1 = 0) |
| generated_at_utc | 2026-08-21 |
| patches | не применялись (`ALLOW_ISSUE_WRITE=false`, default do-not-apply) |

## Executive summary

Цепочка **source → generator → validation → artifact** в BioETL существует и в целом собрана: единый CLI `python -m scripts.docs`, pinned toolchain (`uv.lock` + extra `docs`), CI `.github/workflows/docs.yml` (`docs-governance` + `validate-mkdocs` с `python -m scripts.docs verify`), passports `--check`, config parity, cleanup-inventory `--check`, weekly KPI.

Это не score 3: (1) file-level integrity для картинок не закрыта вопреки комментарию в `mkdocs.yml`; (2) `verify` сужает `check-drift` и выключает ERROR-проверки `--modules`/`--ai-surfaces`; (3) advertised `site_url` даёт GitHub Pages 404 при отсутствии deploy; (4) операторские карты CI/`--configs` расходятся с кодом.

Опасного publish/secret leak не найдено. Генераторный exit 0 не принимался как semantic proof.

## Surface score

| Score | Meaning (card) | Здесь |
| ---: | --- | --- |
| 3 | One-command clean build; pinned toolchain; deterministic; links/API in CI | нет: image gate дырявый, drift subset, API не autodoc |
| **2** | Pipeline reproducible; some semantic checks still manual | **выбрано** |
| 1 | Hidden preconditions, generated drift, or unpredictable publish | нет: local `docs/site/` и отсутствие Pages задокументированы |
| 0 | Build broken / secret leak / dangerous publish | нет |

Mapping: card 0–3 control maturity, не dimension 0–5.

## Pipeline map

| Step | Entrypoint | Inputs | Outputs | Caller | Failure |
| --- | --- | --- | --- | --- | --- |
| Unified CLI | `python -m scripts.docs` | `scripts/docs/__main__.py` COMMANDS | dispatch | local/CI | unknown command → non-zero |
| verify | `scripts.docs.checks.verify` | links+drift subset+docstrings+cleanup+strict mkdocs | stdout; temp site dir | `docs.yml` validate-mkdocs; tests.yml proof-or-stop `--skip-build` (rc captured, job `exit 0`) | first non-zero step |
| build-site | `scripts.docs.build.mkdocs_build` | `mkdocs.yml`, docs extra | `docs/site/` (gitignored) via tempfile staging | manual; `build_docs_site.sh` | mkdocs rc |
| check-links | `scripts.docs.checks.check_links` | `docs/`, `mkdocs.yml`, configs, workflows | optional JSON report (`timestamp` now()) | CI full; pre-commit partial; verify full | violations → 1 |
| check-drift | `scripts.docs.checks.check_drift` | architecture docs, runtime mirrors | JSON optional | verify subset; weekly `--runtime-mirrors --freshness`; README ложно указывает `architecture.yml` | `error_count>0` → 1; WARNING не валит |
| passports | `scripts.docs.passports.cli` | configs + src factories/workflow | `docs/04-reference/passports/**` | `docs.yml` `passports check`; nightly generate to `/tmp` | stale/orphan/blocking diagnostics → 1 |
| KPI | `scripts.docs.checks.report_docs_kpi` | not-in-nav baseline, targets 120/135 | `reports/docs-kpi/` artifact | `docs-kpi-weekly.yml` Monday 04:30 UTC | `--fail-on-breach` |
| Publish | **нет deploy job** | — | local `docs/site/` only | policy 2026-07-10 | site_url всё равно github.io → 404 |
| Diagrams | `docs.yml` render-* | `.mmd` / renderer inputs | svg/png artifacts | path-filtered | отдельный domain `diagrams` |

Toolchain pin: `mkdocs>=1.6,<2.0` (lock 1.6.1), `mkdocs-material>=9.5` (lock 9.7.7), `mkdocstrings[python]>=0.25`, `pymdown-extensions>=10.8`, extra `docs` в `validate-mkdocs`.

## Source-of-truth map (generated vs authored)

| Artifact | SoT | Tracked? | Check |
| --- | --- | --- | --- |
| `docs/00-05/**` markdown | authored | yes | check-links, mkdocs nav test |
| `mkdocs.yml` nav/not_in_nav | authored | yes | check-links skill classification; `not_in_nav_baseline.txt` |
| `docs/04-reference/api/**` | curated authored (не mkdocstrings dump) | yes | nav existence; **нет** public-API generator |
| `docs/04-reference/passports/**` | generator `scripts.docs.passports` | yes | `passports check` + jsonschema |
| `docs/02-architecture/generated/module-dependency-map.*` | `scripts/engineering/qa/generate_architecture_dependency_map.py` | yes | `--check` in docs.yml; PR git diff --exit-code |
| field/normalization matrices | `scripts.docs.matrix.*` | curated generated | `--check` in provider-contract-drift / tests.yml |
| cleanup inventory | `documentation_cleanup_inventory.py` | yes | verify `--check` |
| `docs/site/` | mkdocs build | gitignored | verify temp dir; build-site copies to docs/site |
| `docs/exports/**` | `generate_docs_export.py` | ignored local | manual |
| runtime mirrors `docs/00-project/ai/**` | `.codex/**` / `.junie/**` | yes | check-drift `--runtime-mirrors` **если сработал docs.yml** |

## Findings (P0–P3)

Полные поля: `findings.json`. Кратко:

| ID | Pri | Status | Path | Observation |
| --- | --- | --- | --- | --- |
| DOCPIPE-001 | P2 | PROVEN | `scripts/docs/checks/check_links.py:667` | skip `.png/.svg` + `not_found: info` при комментарии, что check-links закрывает file-level integrity |
| DOCPIPE-002 | P2 | PROVEN | `scripts/docs/checks/verify.py:53` | verify-drift subset выключает `--modules`/`--ai-surfaces` (ERROR) |
| DOCPIPE-003 | P2 | PROVEN | `.github/workflows/docs.yml:18` | нет path-filter `.codex/agents/**` / `.junie/**` для runtime-mirrors gate |
| DOCPIPE-004 | P2 | PROVEN | `scripts/docs/README.md:77` | check-drift/docstrings «CI gate architecture.yml» — ложь |
| DOCPIPE-005 | P2 | PROVEN | `scripts/ops/run-coderabbit-reviews.sh:144` | `check-drift --configs` не существует |
| DOCPIPE-006 | P2 | PROVEN | `mkdocs.yml:3` | `site_url` github.io → 404; deploy нет |
| DOCPIPE-007 | P3 | PROVEN | `scripts/docs/checks/verify.py:104` | dual mkdocs path vs helper-chain claim |
| DOCPIPE-008 | P3 | PROVEN | `pyproject.toml:175` | `mkdocs-mermaid2-plugin` не в `mkdocs.yml` |
| DOCPIPE-009 | P3 | PROVEN | `.pre-commit-config.yaml:294` | partial check-links vs verify «insufficient» |
| DOCPIPE-010 | P3 | PROVEN | `docs/03-guides/docs-parity-gate.md:16` | stale CI examples (py3.12/pip/GitLab) |
| DOCPIPE-011 | P3 | PROVEN | `mkdocs.yml:121` | mkdocstrings без `:::` autodoc |
| DOCPIPE-012 | P3 | PROVEN | `scripts/docs/build_docs_site.sh:34` | нет probe `.venv-win` |

Пустых findings нет: инвентарь SCOPE выполнен (CLI, workflows, mkdocs, generators, tests, publication policy).

## Top remediations (не применены)

1. Проверять relative `.png/.svg` в `check_broken_links` для published/nav docs **или** убрать ложный комментарий и ввести always-on image existence check.
2. В `verify` вызывать полный `check-drift` либо явно добавить `--modules --ai-surfaces`; зафиксировать argv тестом.
3. Добавить `.codex/agents/**` и `.junie/**` в path filters `docs.yml`.
4. Исправить Trigger-колонку `scripts/docs/README.md` на `docs.yml via verify`.
5. Удалить `--configs` из `run-coderabbit-reviews.sh` check-drift.
6. Убрать/не задавать `site_url`, пока нет Pages deploy (policy: один changeset).
7. `verify` strict build через `scripts.docs.build.mkdocs_build`.
8. Вычистить неиспользуемые extras/plugins (`mermaid2`, mkdocstrings) или реально подключить.

## What is working

- Один CLI `python -m scripts.docs` без top-level shims (#8043).
- `docs.yml`: governance pytest slice + passports check + check-links JSON artifact + entity-config parity + verify (включая strict mkdocs) + dependency-map `--check`.
- uv `--frozen --no-build`, extra `docs` на validate-mkdocs, pinned actions SHAs.
- Passports: jsonschema + stale/orphan check; `--require-clean-source` доступен.
- Publication policy честно говорит, что `docs.yml` не Pages deploy; `docs/site/**` helper/gitignored.
- PR preview официально отсутствует (`docs-verification.md`); hidden local publish state не найден.
- Secrets в `scripts/docs/**`: нет чтения `.env`/API keys; `SOURCE_DATE_EPOCH` только в sentence_audit; passports revision из git.
- KPI targets 120/135 совпадают с defaults в `report_docs_kpi.py` и тестом workflow.
- `tests/architecture/test_docs_governance_workflow.py` фиксирует набор governance tests и `.github/workflows/**` path filter.

## Anti-patterns (card) — как учтены

- Не дублировать docs-content IA: findings только про tooling/CI/publish metadata.
- Generator exit 0 ≠ correctness: отмечен subset drift и отсутствие API autodoc.
- Publishing with hidden local-only state: не доказано; local site dir задокументирован.

## Skipped / NOT_PROVEN runtime

В этом агенте нет `run_terminal_command`. Не запускались:

- `.\.venv-win\Scripts\python.exe -m scripts.docs verify`
- `check-links --report-json`
- `mkdocs build --strict`
- `python -m memory.tooling.workflow pre-task`
- чтение gitignored предыдущих `reports/audit/docs-pipeline/*` через read_file (каталог листится, содержимое ignore)

Поэтому **текущий green/red CI** и фактический count broken links — `NOT_PROVEN`. Все 12 findings опираются на file-level proof текущего checkout + HTTP 404 Pages.

## Checks run (static)

28 инспекций: mkdocs.yml, scripts/docs CLI/README/verify/build/check_links/check_drift/passports/kpi/export, pyproject+lock extras, docs.yml, docs-kpi-weekly, architecture.yml, architecture-docs-nightly, skills-consistency, tests.yml docs producer, pre-commit, publication policy, docs-verification, docs-parity-gate, generated_artifact_routing, API index, github.io fetch, coderabbit reviews script, catalog.yaml, architecture tests for docs workflow/router/kpi.

## Guardrails

- `.env` не менялся.
- Бюджеты техдолга не увеличивались.
- GitHub issues не создавались.
- Root clutter не создавался.
- Код не патчился.
