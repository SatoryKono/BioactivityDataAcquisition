# Docs pipeline audit

| Field | Value |
| --- | --- |
| domain_id | `docs-pipeline` |
| prompt_id | `prompt.audit.docs-pipeline` v1.2.0 |
| MODE | `audit` |
| AUDIT_MODE | `full` |
| LANGUAGE | `ru` |
| REQUIRE_GH_TRACKING | `false` |
| SCOPE | `scripts/docs/` `mkdocs.yml` `docs/` |
| checkout | `refs/heads/master20260825-21` |
| date | 2026-08-26 |
| surface_score | **2** (acceptable: pipeline reproducible; some semantic checks still manual) |
| blocked | `false` |
| debt outcome | `unchanged` (read-only audit; budgets not touched) |

Легенда surface_score (домен docs-pipeline): **3** one-command clean build + pinned toolchain + deterministic + links/API in CI; **2** reproducible pipeline, часть semantic-проверок ручная; **1** hidden preconditions / generated drift / unpredictable publish; **0** build broken, secret leak, or dangerous publish.

## Summary

Цепочка **source-of-truth → generator → validation → artifact → publication** в репозитории существует и в основном воспроизводима:

- единый CLI `python -m scripts.docs <command>`;
- канонический verify `python -m scripts.docs verify`;
- CI `.github/workflows/docs.yml` (`docs-governance` + `validate-mkdocs`) на `uv run --frozen`;
- pin toolchain: `pyproject.toml` extra `docs` (`mkdocs>=1.6,<2.0`) + `uv.lock`;
- semantic-островки: passports `--check`, API curated-symbol tests, architecture docs drift, cleanup inventory.

Это не score 3: advertised GitHub Pages URL отдаёт 404; image-ссылки и MkDocs missing-file не валят gate; extra JS/CSS для Mermaid отсутствуют в дереве; `verify` уже каноническая one-command, но уже *уже*, чем полный CI (нет passports / `--ai-surfaces`); shell-транспорт выбирает «первый python с mkdocs».

P0/P1 не доказаны. Secret leak в generated output не найден (pymdownx.snippets включён, но `--8<--` в docs не используется). Живые `verify` / `check-links` / `mkdocs build` в этой сессии **не запускались** (нет shell-инструмента у auditor-агента) — статус live-green CI помечен `NOT_PROVEN`.

## Pipeline map

| Step | Entrypoint | Inputs | Outputs | Caller | Failure |
| --- | --- | --- | --- | --- | --- |
| Unified CLI | `python -m scripts.docs` | `scripts/docs/__main__.py` COMMANDS | dispatch | local / CI | unknown command → non-zero |
| Links / nav / specs | `python -m scripts.docs check-links` | `docs/`, `mkdocs.yml`, configs, workflows | stdout; optional JSON report | verify; docs.yml; pre-commit manual | exit 1 on violations |
| Drift | `python -m scripts.docs check-drift` | architecture docs, `.codex`/`.junie` mirrors | stdout / `--json` | verify (subset of flags); weekly KPI | exit 1 on ERROR only |
| Docstrings | `python -m scripts.docs check-docstrings` | `src/bioetl/` | coverage vs THRESHOLDS | verify | exit 1 under threshold |
| Cleanup inventory | `python -m scripts.docs generate-cleanup-inventory --check` | tracked docs + `configs/quality/generated_artifact_routing.yaml` | `docs/reports/generated/documentation-cleanup-inventory.*` | verify | exit 1 on drift |
| Passports | `python -m scripts.docs passports check\|generate` | configs + composition/workflow sources | `docs/04-reference/passports/**` | docs.yml docs-governance; nightly | exit 1 on stale/blocking diagnostics |
| Strict site | `python -m mkdocs build --strict` (via verify) or `python -m scripts.docs build-site` | `mkdocs.yml`, `docs/` | temp dir (verify) or `docs/site/` (build-site) | verify / local | mkdocs non-zero; missing files are **info** |
| Parity configs↔specs | `python -m scripts.data_quality check-entity-config-parity` | entity YAML + pipeline specs | stdout | docs.yml validate-mkdocs | fail-closed |
| Dataflows / class diagrams | `scripts.diagrams generate-dataflows --check`, `generate_package_family_class_diagrams.py --check` | schemas/code | `docs/02-architecture/generated/**`, diagram trees | docs.yml docs-governance | exit 1 on drift |
| Dependency map | `scripts/engineering/qa/generate_architecture_dependency_map.py --check` | import graph | `docs/02-architecture/generated/module-dependency-map.*` | docs.yml; tests.yml | exit 1 on drift |
| KPI | `python -m scripts.docs check-kpi --fail-on-breach` | docs tree | `reports/docs-kpi/` artifacts | docs-kpi-weekly.yml | scheduled, not PR |
| Publish | **none** | — | advertised `site_url` | — | live 404 |

Pinned packages (docs extra): `mkdocs>=1.6,<2.0`, `mkdocs-material>=9.5`, `backrefs>=6.2`, `mkdocs-mermaid2-plugin>=1.1` (unused in `mkdocs.yml`), `pymdown-extensions>=10.8`, `mkdocstrings[python]>=0.25` (plugin on, no `:::` pages).

Network: link-check is relative-only (`MD_LINK_RE` negative lookahead `https?://|mailto:`). Cache: uv action caches `~/.cache/uv` and `.venv`. Env: no `.env` reads in `scripts/docs/**` observed; env guardrail respected (`.env` not touched).

## Source-of-truth chain

See `source-of-truth-map.md`. Short form:

| Artifact | SoT | Generator | Gate |
| --- | --- | --- | --- |
| Published nav pages | hand-written `docs/00-05/**` | none | check-links + mkdocs nav test |
| API reference | curated markdown, **not** mkdocstrings dump | none | `test_api_reference_public_facades.py` |
| Passports | configs + composition/workflow code | `scripts.docs passports` | `passports check` + projector tests |
| Module dependency map | live packages | `generate_architecture_dependency_map.py` | `--check` + PR regenerate-and-diff |
| Pipeline dataflows | pipeline/schema code | `scripts.diagrams generate-dataflows` | `--check` |
| Cleanup inventory | tracked tree + routing YAML | `documentation_cleanup_inventory.py` | `--check` in verify |
| MkDocs site | `mkdocs.yml` + docs | mkdocs | `--strict` with `not_found: info` |
| GitHub Pages | n/a | **no deploy job** | live URL 404 |

Generated Markdown is not treated as correct merely because a generator exited 0: passports validate JSON Schema + completeness diagnostics; several `--check` diffs exist. Gaps: images, advertised Pages, unused mkdocstrings, verify subset.

## Findings (PROVEN)

Полные объекты — `findings.json`. Кратко:

| ID | Pri | Path | Observation |
| --- | --- | --- | --- |
| DOCS-PIPE-001 | P2 | `scripts/docs/checks/check_links.py:667` | `.png`/`.svg` цели пропускаются; mkdocs `not_found: info` |
| DOCS-PIPE-002 | P2 | `mkdocs.yml:3` | `site_url` github.io → live 404; нет Pages workflow |
| DOCS-PIPE-003 | P2 | `mkdocs.yml:147-152` | `docs/assets/**` для mermaid-init/css отсутствует |
| DOCS-PIPE-004 | P2 | `README.md:102` | README обещает mkdocstrings API; страницы curated, `:::` нет |
| DOCS-PIPE-005 | P2 | `.github/workflows/docs.yml:18` | path-filter без `.codex/agents` / `.junie` / `.devin/agents` |
| DOCS-PIPE-006 | P2 | `scripts/docs/checks/verify.py:53` | verify без passports и `--ai-surfaces` |
| DOCS-PIPE-007 | P2 | `scripts/docs/build_docs_site.sh:30` | первый PATH python с mkdocs; нет `.venv-win` |
| DOCS-PIPE-008 | P2 | `scripts/docs/checks/check_links.py:1214` | README.md/AGENTS.md вне link-scan |
| DOCS-PIPE-009 | P3 | `scripts/docs_parity_check.py:65` | dual entrypoint с порогом 85% |
| DOCS-PIPE-010 | P3 | `pyproject.toml:175` | `mkdocs-mermaid2-plugin` не подключён в plugins |
| DOCS-PIPE-011 | P3 | `.github/workflows/docs.yml:121` | governance 3.13 vs validate-mkdocs default 3.12 |
| DOCS-PIPE-012 | P3 | `scripts/docs/checks/verify.py:105` | verify зовёт `python -m mkdocs`, не `build-site` |
| DOCS-PIPE-013 | P3 | `.pre-commit-config.yaml:294` | docs hooks manual + урезанные флаги |
| DOCS-PIPE-014 | P3 | `scripts/generate_adr_registry.py:1` | ADR registry вне `python -m scripts.docs` |
| DOCS-PIPE-015 | P3 | `docs/03-guides/docs-parity-gate.md:16` | гайд описывает чужой CI (v4/pip/old shell) |
| DOCS-PIPE-016 | P3 | `scripts/docs/checks/check_drift.py:1945` | WARNING не меняет exit code |

P0/P1 count: **0**. PROVEN count: **16**.

## What is working

- `python -m scripts.docs verify` — реальная one-command цепочка (links + drift subset + docstrings + cleanup inventory + strict mkdocs в temp dir).
- CI `docs.yml` на `uv --frozen`, `persist-credentials: false`, passports check, dataflow/class-diagram `--check`, architecture pytest slice including API facades and mkdocs nav existence.
- Passports: byte-canonical JSON, source revision from fact-owner git log (not self-referential HEAD), schema validate, `--require-clean-source` available; unit tests for determinism.
- `docs/site/` and `site/` gitignored; build-site stages via tempfile then copies.
- Weekly KPI + nightly architecture-docs as delayed backstops.
- Publication policy explicitly records that `docs.yml` is not a Pages deploy (so 404 is a metadata/contract bug, not a silent prod publish of wrong material).

## Skipped / NOT_PROVEN

| Check | Reason |
| --- | --- |
| Live `python -m scripts.docs verify` / `check-links` / `build-site --strict` | no shell tool in this auditor runtime |
| Live passport `--check` and cleanup-inventory `--check` | same |
| Memory `pre-task` / `post-task` | same; `BIOETL_AI_MEMORY_MODE` not applied |
| Secret scan of built `site/` HTML | site not built |
| GitHub Pages settings API | REQUIRE_GH_TRACKING=false; judged via public 404 + missing workflow |
| Whether missing extra_js fails mkdocs `--strict` | not executed; files are absent regardless |

Residual risks (not separate findings): `pymdownx.snippets` without `base_path` restriction; `generate_docs_export.py` uses `date.today()` (artifact gitignored); `check-links --report-json` embeds wall-clock timestamp (CI artifact only).

## Top remediations

1. Включить проверку tracked `.svg` (и не-gitignore image) в `check_broken_links`; сузить mkdocs `not_found: info` или компенсировать отдельным runner (DOCS-PIPE-001).
2. Либо задеплоить Pages, либо убрать github.io `site_url` синхронно с publication policy (DOCS-PIPE-002).
3. Закоммитить `docs/assets/javascripts/mermaid-init.js` + CSS **или** включить/удалить `mkdocs-mermaid2-plugin` (DOCS-PIPE-003/010).
4. Починить README API row и либо убрать idle mkdocstrings, либо дать `:::` pages (DOCS-PIPE-004).
5. Добавить `.codex/agents/**`, `.junie/**`, `.devin/agents/**` в path filters `docs.yml` (DOCS-PIPE-005).
6. Включить `passports check` и `--ai-surfaces` в `verify.py` (DOCS-PIPE-006).
7. Заставить `build_docs_site.sh` / операторов идти через `run_project_python.py` / `uv run --frozen` и `.venv-win` (DOCS-PIPE-007).
8. Сканировать `README.md` и `AGENTS.md` в check-links (DOCS-PIPE-008).

## Guardrails

- `.env` не читался и не менялся.
- Tech-debt budgets не менялись и не предлагались к увеличению.
- Product code не редактировался; MODE=audit, патчи не предлагались к применению.
- GitHub issues/PR не создавались (`REQUIRE_GH_TRACKING=false`).

## Artifacts

- `reports/audit/docs-pipeline/report.md`
- `reports/audit/docs-pipeline/findings.json`
- `reports/audit/docs-pipeline/docs-pipeline.csv`
- `reports/audit/docs-pipeline/generated-files.csv`
- `reports/audit/docs-pipeline/source-of-truth-map.md`
- `reports/audit/docs-pipeline/link-report.json` (static analysis of the checker, not a live scan)
- `reports/audit/docs-pipeline/docs-build.log` (skipped live build)
