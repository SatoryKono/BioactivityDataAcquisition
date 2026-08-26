# Docs pipeline audit

| Field | Value |
| --- | --- |
| domain_id | `docs-pipeline` |
| prompt_id | `prompt.audit.docs-pipeline` v1.2.0 |
| MODE | `audit` |
| AUDIT_MODE | `full` |
| LANGUAGE | `ru` |
| REQUIRE_GH_TRACKING | `false` |
| SCOPE | `scripts/docs/` · `mkdocs.yml` · `docs/` |
| surface_score | **2** / 3 (acceptable: core chain reproducible; semantic gaps remain) |
| blocked | `false` |
| debt_outcome | `unchanged` (read-only; budgets not touched) |
| findings | 18 PROVEN (P1: 1, P2: 10, P3: 7) |

## Executive summary

Каноническая цепочка **есть и подключена к CI**: `python -m scripts.docs verify` гоняет links, sliced drift, docstrings, cleanup-inventory `--check` и `mkdocs build --strict` во временный каталог. Workflow `.github/workflows/docs.yml` дополнительно гоняет passports `--check`, architecture docs tests, xwalk/dashboard inventory и (на PR) dependency-map `--check`. Toolchain в CI заморожен (`uv run --frozen --no-build`, `uv.lock` pin `mkdocs==1.6.1`, action pin `uv==0.11.26`).

Это **не** score 3:

- generator/verify exit 0 **не** равен семантической корректности API reference;
- image/external links не валятся в strict build;
- часть generated SoT объявлена tracked, но gitignore/CI `--check` её не держат;
- `site_url` указывает на GitHub Pages, которого нет (404).

Секретов в generated pages/logs **не доказано**. `.env` не читался на предмет значений и не изменялся.

## Surface score

| Score | Meaning (kit) | Why this audit |
| --- | --- | --- |
| 3 | One-command clean build; pinned toolchain; deterministic; links/API in CI | API vs public surface **not** in CI; image/external links weak |
| **2** | Pipeline reproducible; some semantic checks still manual | **Selected**: verify+docs.yml exist and are frozen |
| 1 | Hidden preconditions / generated drift / unpredictable publish | Matrix workbook is local-only, but core docs chain is not |
| 0 | Build broken / secret leak / dangerous publish | Not observed |

Mapping: kit domain table in `prompt.audit.docs-pipeline` (one-command + pins present; semantic API/image/publish gaps keep the score at 2).

## Method

1. Read AGENTS.md precedence, `docs/00-project/NORMATIVE_SOURCES.md`, MEMORY_USAGE, agent-memory, audit card + fragments (evidence-contract, finding-schema, debt-budget-ban, env-guardrail, audit-scale, reports-output).
2. Inventory `scripts/docs/**`, `mkdocs.yml`, `docs/03-guides/docs-verification.md`, publication/nav policy, `.github/workflows/docs.yml`, `docs-kpi-weekly.yml`, `architecture-docs-nightly.yml`.
3. Trace SoT → generator → validation → artifact → publication for MkDocs, passports, cleanup inventory, matrices, dependency map.
4. HTTP GET advertised `site_url`.
5. **Not run** (no shell tool in this runtime): live `verify`, `check-links`, `check-drift --modules`, `build-site --strict`, matrix `--check`, memory `pre-task`. Marked skipped, not invented as PASS.

Disjoint scope: narrative/IA/stale prose belongs to `prompt.audit.docs-content`. Here only generators, gates, publish, and operator pipeline contracts.

## Pipeline map

| Step | Entrypoint | Inputs | Outputs | Env / network | Failure | Local vs CI |
| --- | --- | --- | --- | --- | --- | --- |
| Unified CLI | `python -m scripts.docs <cmd>` (`scripts/docs/__main__.py`) | argv | stdout + files per command | no network required for checks | rc 1 on violations | both |
| Verify chain | `scripts/docs/checks/verify.py` | repo docs + src | temp MkDocs site | needs docs extra for last step | fail-fast per step | CI `docs.yml` validate-mkdocs; local `uv run python -m scripts.docs verify` |
| Links | `scripts/docs/checks/check_links.py` | `docs/`, `mkdocs.yml`, configs, workflows | optional JSON report | local FS only; **no http(s)** | rc 1 | CI full unflagged; published guide often `--links --specs --configs` |
| Drift | `scripts/docs/checks/check_drift.py` | architecture docs, `.codex` mirrors | stdout/JSON | local | rc 1 on ERROR | verify uses **subset** of flags |
| Docstrings | `scripts/docs/checks/check_docstrings.py` | `src/bioetl` | summary | local | rc 1 under thresholds | in verify |
| Cleanup inventory | `generate-cleanup-inventory --check` | git + routing yaml | `docs/reports/generated/documentation-cleanup-inventory.{json,md}` | local, deterministic (no wall clock) | rc 1 on drift | in verify |
| Passports | `python -m scripts.docs passports check` | configs + src factories | `docs/04-reference/passports/**` | git status optional | rc 1 stale/orphan | docs.yml docs-governance |
| MkDocs build | verify: `python -m mkdocs build --strict --clean --site-dir <tmp>`; preview: `scripts.docs build-site` | `mkdocs.yml`, `docs/` | tmp or `docs/site/` | docs extra (`mkdocs==1.6.1`) | strict on **anchors**, not missing files | CI after docs extra install |
| KPI | `check-kpi --fail-on-breach` | nav + baseline | `reports/docs-kpi/*` | schedule | hard limit 135 / orphans 0 | weekly only |
| Diagrams | `docs.yml` mermaid jobs | `.mmd` / theme | svg/png artifacts | Node mermaid CLI | separate from docs verify | skipped unless diagram paths change |
| Matrix | `scripts/docs/matrix/* --check` | code + **gitignored xlsx** | generated JSON/MD/xlsx dicts | local | --check exists, **not in docs.yml** | unit tests on tmp_path |
| Publish | **none** | — | advertised Pages URL 404 | — | n/a | policy: validation-only |

### Toolchain pins

| Package | Declared | Locked |
| --- | --- | --- |
| mkdocs | `>=1.6,<2.0` | `1.6.1` (`uv.lock`) |
| mkdocs-material | `>=9.5` | lock |
| mkdocstrings[python] | `>=0.25` | lock |
| mkdocs-mermaid2-plugin | `>=1.1` | `1.2.3` — **unused by mkdocs.yml** |
| uv (CI action) | `0.11.26` | `.github/actions/setup-python-uv/action.yml` |
| Python | docs-governance **3.13**; validate-mkdocs **default 3.12** | split |

## Source of truth vs generated

See `source-of-truth-map.md` and `generated-files.csv`.

Tracked generated that **are** gated:

- passports under `docs/04-reference/passports/` (`passports check` in docs.yml);
- cleanup inventory JSON/MD (`verify`);
- `docs/02-architecture/generated/module-dependency-map.*` (PR `--check` + commit assert);
- `docs/reports/generated/chembl_matrix_structural_contract_v1.json` (file tracked; **`--check` not in CI**);
- `docs/reports/generated/pipeline_normalization_field_matrix/*.md` (tracked; **`--check` not in CI**).

Declared tracked but **not** in git allowlist / tree:

- `docs/reports/generated/chembl_activity_field_matrix/` (`generated_artifact_routing.yaml` vs `.gitignore`).

Hidden local:

- `docs/reports/chembl_pipeline_silver_matrices_v12.xlsx` and `docs/reports/dictionaries/` under `/docs/reports/*`.

MkDocs HTML is gitignored (`site/`, `docs/site/`). verify does not publish it.

## Findings (PROVEN)

| ID | Pri | Path | Observation |
| --- | --- | --- | --- |
| DOCS-PIPE-001 | P1 | `docs/04-reference/api/application.md:16` | API pages claim autogen; mkdocstrings unused (`:::` absent); no API-vs-public-API gate |
| DOCS-PIPE-002 | P2 | `scripts/docs/checks/verify.py:53` | verify omits `--modules` / providers / glossary |
| DOCS-PIPE-003 | P2 | `scripts/docs/checks/check_links.py:667` | `.png`/`.svg` skipped; mkdocs `not_found: info` |
| DOCS-PIPE-004 | P2 | `mkdocs.yml:3` | `site_url` GitHub Pages **404**; no deploy workflow |
| DOCS-PIPE-005 | P2 | `configs/quality/generated_artifact_routing.yaml:106` | field-matrix routing vs gitignore; dir missing |
| DOCS-PIPE-006 | P2 | `.gitignore:549` | canonical xlsx + dictionaries gitignored |
| DOCS-PIPE-007 | P2 | `.github/workflows/docs.yml:18` | path filters miss `.codex/agents/**` / `.junie/**` |
| DOCS-PIPE-008 | P2 | `.github/workflows/architecture-docs-nightly.yml:41` | nightly `--update` does not fail on diff |
| DOCS-PIPE-009 | P2 | `scripts/docs/common/markdown.py:9` | no http(s) linkcheck |
| DOCS-PIPE-010 | P2 | `.github/workflows/docs.yml:218` | matrix `--check` not in docs.yml |
| DOCS-PIPE-011 | P3 | `pyproject.toml:175` | unused `mkdocs-mermaid2-plugin` |
| DOCS-PIPE-012 | P3 | `mkdocs.yml:7` | `site/` vs `docs/site/` |
| DOCS-PIPE-013 | P3 | `.github/workflows/docs.yml:121` | Python 3.13 vs 3.12 in one workflow |
| DOCS-PIPE-014 | P3 | `.github/workflows/docs-kpi-weekly.yml:20` | missing `persist-credentials: false` |
| DOCS-PIPE-015 | P3 | `.github/workflows/docs.yml:203` | check-links then verify (duplicate links) |
| DOCS-PIPE-016 | P3 | `.pre-commit-config.yaml:38` | check-yaml excludes `mkdocs.yml` |
| DOCS-PIPE-017 | P3 | `scripts/docs/build_docs_site.sh:30` | PATH python-with-mkdocs before `.venv` |
| DOCS-PIPE-018 | P2 | `tests/unit/scripts/test_generate_chembl_activity_field_matrix.py:91` | `--check` tests never hit DEFAULT_OUT_DIR |

Full records: `findings.json`.

## What is working (not findings)

- One-command local/CI path: `uv run python -m scripts.docs verify` (docs extra required for strict build — documented in `docs/00-project/TOOLS.md` and `docs/03-guides/docs-verification.md`).
- Unflagged `check-links` is a real semantic suite (specs, configs, contracts index, workflow inventory, provider overview, governance sections, not-in-nav growth, legacy tokens), not merely “file exists”.
- Passports `--check` + jsonschema in docs-governance with `fetch-depth: 0`.
- Runtime mirror/freshness ERROR path exists (`check_drift` + `test_runtime_agent_docs_drift.py` + weekly KPI).
- `uv --frozen`, pinned uv, mkdocs `<2.0` lock.
- Publication policy honestly says docs.yml is not a Pages deploy (but `site_url` still pretends otherwise — DOCS-PIPE-004).
- Root `site/` and `docs/site/` gitignored; verify uses tempfile (no accidental commit of HTML).
- No P0 secret leak observed in scripts/docs generators (timestamps in KPI/link JSON artifacts only; those paths are working output).

## Skipped / NOT_PROVEN

| Check | Why |
| --- | --- |
| Live `python -m scripts.docs verify` / `build-site --strict` | No `run_terminal_command` in this agent runtime |
| Live link-check JSON | same |
| Live `check-drift --modules` on current tree | same — **code path proven omitted from verify**, live violation count unknown |
| Live matrix `--check` | same — missing DEFAULT_OUT_DIR proven via listing |
| Memory `pre-task` | no shell; catalog not refreshed |
| GitHub workflow run history | `REQUIRE_GH_TRACKING=false`; not required |
| Secret values in `.env` | env-guardrail: do not copy secrets into reports |

Do not treat skipped live builds as green.

## Top remediations

1. **API gate (P1):** убрать баннер «Autogenerated» или подключить mkdocstrings/`--check` к public facades и гонять в `docs.yml`.
2. **verify completeness:** добавить `--modules` (и providers/glossary) в `scripts/docs/checks/verify.py`.
3. **Image integrity:** проверять `.png`/`.svg` для nav-published pages или сузить `not_found: info` до gitignored `**/png/**`.
4. **Publication metadata:** убрать/пометить `site_url` или добавить реальный Pages deploy одним changeset с policy.
5. **Generated matrices:** allowlist field-matrix в `.gitignore`, закоммитить артефакты, добавить `--check` в `docs.yml`; решить судьбу gitignored xlsx (tracked SoT vs local-only README).
6. **Path filters:** `.codex/agents/**` и `.junie/agents/**` в `docs.yml`.
7. **Nightly fail-closed:** `architecture-docs-nightly.yml` rc≠0 при `git diff` по `docs/02-architecture/generated`.
8. **Toolchain hygiene:** удалить unused mermaid2; выровнять `site_dir` и Python 3.12/3.13; `verify --skip-links` после JSON check-links; `persist-credentials: false` на weekly/nightly.

Не повышать tech-debt budgets. MODE=audit — патчи не предлагались к применению.

## Kit extras

| File | Role |
| --- | --- |
| `findings.json` | machine findings (schema) |
| `docs-pipeline.csv` | step inventory |
| `generated-files.csv` | generated SoT routing |
| `source-of-truth-map.md` | SoT → generator → gate |
| `docs-build.log` | skipped live build note |
| `link-report.json` | skipped live linkcheck note |

## Guardrails

- Debt budgets: not modified.
- `.env`: not created/edited/moved.
- Product code: not edited.
- GitHub issues: not opened (`REQUIRE_GH_TRACKING=false`).
