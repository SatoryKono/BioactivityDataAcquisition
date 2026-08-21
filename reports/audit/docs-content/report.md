# Docs content audit — `docs-content`

| Field | Value |
| --- | --- |
| domain_id | `docs-content` |
| prompt_id | `prompt.audit.docs-content` |
| MODE | `audit` / `AUDIT_MODE=full` |
| LANGUAGE | `ru` |
| SCOPE | `README.md`, `docs/` (content / IA / links / commands; not pipeline tooling) |
| BASE | `main` |
| REPO | `SatoryKono/BioactivityDataAcquisition` |
| Date | 2026-08-21 |
| surface_score | **2** (acceptable: main path correct; local non-critical + two P1 ops-runbook gaps) |
| Score mapping | Domain card 0–3 control maturity (not 0–5 dimension average) |
| blocked | false |
| ALLOW_ISSUE_WRITE | false (issues not created) |

## Executive summary

Published onboarding (README, Quick Start, Getting Started, TOOLS, docs-verification) describes a **reproducible local-only bootstrap**: Python 3.12 baseline, `uv sync --extra dev --extra tests --extra tracing`, `python -m scripts.ops setup-plugins`, mixed Windows `.venv-win` / WSL venv split, coverage gate 85%, **22** standard entity YAMLs. Sampled README relative links resolve. Docs quality is **gated** (`scripts.docs verify`, `.github/workflows/docs.yml`).

Material drift is concentrated in **operator recovery** and **env/security SSOT**, not in first-run install:

- P0 runbook `pipeline-failure-critical.md` still tells operators to `--resume-from` (flag does not exist in CLI).
- P0/P1 DR runbook `data-recovery.md` still uses Spark SQL `RESTORE TABLE` while runtime is `deltalake` (delta-rs) + rebuild CLI.
- Canonical env-var reference is incomplete and invents `BIOETL_CHEMBL_API_KEY`; SECURITY examples invent ChEMBL/PubChem keys.

**surface_score = 2**: critical user/eng bootstrap is described and mostly checked; ops recovery and env reference are not at score 3.

## Inventory (SCOPE)

| Surface | Status | Audience | Diátaxis | Notes |
| --- | --- | --- | --- | --- |
| `README.md` | active | public / eng | how-to + explanation | Purpose, bootstrap, env table, CLI samples. Version badge `6.1.0 (unreleased)` matches `pyproject.toml`. |
| `CONTRIBUTING.md` | pointer | contributors | how-to | Delegates to `.github/CONTRIBUTING.md`. |
| `.github/CONTRIBUTING.md` | active | contributors | how-to | Broken `\|\|` tables; Windows `.venv` fallback. |
| `.github/SECURITY.md` | active | security | reference | Phantom provider key examples. |
| `.github/CODE_OF_CONDUCT.md` | present | community | policy | Exists. |
| `SUPPORT.md` | absent | — | — | Not required by BioETL SSOT; no broken inbound link found. |
| `CHANGELOG.md` | active | public | reference | Keep-a-Changelog; `[Unreleased]`. |
| `LICENSE` | present | public | — | MIT (README badge). |
| `docs/00-project/` | active | gov / AI | explanation + index | `00-map.md`, `RULES.md` v6.1.10, `NORMATIVE_SOURCES.md`, `TOOLS.md`. |
| `docs/01-requirements/` | active | product | reference | `REQUIREMENTS.md`, `DASHBOARD_REQUIREMENTS.md`. |
| `docs/02-architecture/` | active | architecture | explanation | 57 ADRs (ADR-001..057); English overview vs Russian language policy. |
| `docs/03-guides/` | active | users / eng | tutorial + how-to | Quick Start / Getting Started / testing / runbooks-adjacent guides. |
| `docs/04-reference/` | active | users / eng | reference | CLI, contracts, catalogs, env vars. |
| `docs/05-operations/` | active | ops | how-to | Runbooks; several P0/P1 pages last-verified 2026-03/04. |
| `docs/05-engineering/` | stub | docs | — | DOC-GOV-08 stub; MkDocs excluded. |
| `docs/99-archive/` | archive | historical | — | Non-canonical; README points as repo path. |
| `docs/plans/`, `docs/reports/` | repo-only | planning / evidence | — | Non-normative. |
| `docs/DOCKER_*.md` | adjunct | ops | how-to | Explicitly not canonical bootstrap. |

Entity YAML count (standard, excluding `configs/entities/composite/`): **22** — matches README claim.

## Checklist

- [x] README states project purpose (bioactivity ETL → Delta Lake warehouse).
- [x] Bootstrap path confirmed against `Makefile` `install` / `setup-plugins` and `docs/00-project/TOOLS.md` (README Option A extras are a documented subset of `make install`).
- [x] Commands sampled vs manifests/CI (`uv sync`, `scripts.ops setup-plugins`, `scripts.engineering.dev run-tests`, mypy `--strict` in CI).
- [x] Required env vars documented without secret values; completeness of the “complete reference” failed.
- [x] Sampled README / `00-map` relative links resolve; full `scripts.docs check-links` **skipped** (no shell in this agent).
- [x] Runtime versions: Python `requires-python = ">=3.12"`; CI mypy `--strict --no-incremental`; coverage `--cov-fail-under=85`.
- [x] CLI reference vs `src/bioetl/interfaces/cli/` (run/workflow/quarantine/run-manifest present; `--resume-from` absent).
- [x] Dangerous/stale runbook steps found (P1).
- [x] TODO/FIXME in `docs/05-operations/**` are example Codex prompts, not unowned operational TODOs.

## Diátaxis (project style first)

D-01 (`docs/00-project/governance/01-documentation-governance-style-guide.md`) is the style SSOT. Mapping of published tree:

| Type | Primary homes |
| --- | --- |
| Tutorial | `docs/03-guides/tutorials/`, Getting Started |
| How-to | Quick Start, running-pipelines, `docs/05-operations/runbooks/` |
| Reference | `docs/04-reference/**`, CLI, contracts, env vars |
| Explanation | `docs/02-architecture/**`, RULES, ADRs, glossary |

Gap: env-var **reference** is not a complete SoT; P0 runbooks mix explanation leftovers (Loki, Spark SQL) into how-to.

## Commands vs manifests (sampled)

| Doc command | Manifest / code | Verdict |
| --- | --- | --- |
| `uv sync --extra dev --extra tests --extra tracing` | TOOLS.md + README Option A | Match (minimal local-dev). |
| `make install` → `uv sync --extra dev --extra tests --extra tests_full --extra export` | `Makefile:98-99` | Match; README already notes extra-set difference. |
| `uv run python -m scripts.ops setup-plugins` | `Makefile` `setup-plugins` | Match. |
| `uv run mypy --config-file pyproject.toml --strict --no-incremental src/bioetl` | `.github/workflows/type-checking.yml:94` | Match README/CI. |
| `make lint` → `mypy src/bioetl` | `Makefile:107-109` | **Weaker** than CI/README (no `--strict`). |
| `bioetl run --pipeline … --resume` | CLI `run` options | Match (recovery runbook §4). |
| `--resume-from <run_id>` | CLI grep: **no matches** | **Drift** (P1). |
| `RESTORE TABLE … TO VERSION AS OF` | only in `data-recovery.md`; storage uses `deltalake.DeltaTable` | **Drift** (P1). |
| `grep … logs/` | README default log `reports/logs/bioetl.log` | **Drift** (P2). |

## Links

Sampled README documentation table and `00-map.md` Quick Links (including `chembl_activity_v1.0.json`) **resolve**. Exhaustive link crawl not run in this agent (`scripts.docs check-links` skipped). No P0 secret leak in sampled docs.

## Findings

| ID | Pri | Status | Path | Observation |
| --- | --- | --- | --- | --- |
| DOCS-001 | P1 | PROVEN | `docs/05-operations/runbooks/pipeline-failure-critical.md:53` | P0 runbook resumes with non-existent `--resume-from`. |
| DOCS-002 | P1 | PROVEN | `docs/05-operations/runbooks/data-recovery.md:43-48` | DR uses Spark SQL `RESTORE TABLE`; runtime is delta-rs + `bioetl run --run-type rebuild`. |
| DOCS-003 | P2 | PROVEN | `docs/04-reference/environment-variables.md:15-18` | “Complete” env reference invents `BIOETL_CHEMBL_API_KEY` and omits UniProt + most README vars. |
| DOCS-004 | P2 | PROVEN | `.github/SECURITY.md:43-45` | Secret examples `BIOETL_CHEMBL_API_KEY` / `BIOETL_PUBCHEM_API_KEY` not in `configs/providers` or `.env.example`. |
| DOCS-005 | P2 | PROVEN | `.github/CONTRIBUTING.md:12-33` | Broken `\|\|` markdown tables; Windows fallback uses `.venv` not `.venv-win`. |
| DOCS-006 | P2 | PROVEN | `docs/05-operations/runbooks/pipeline-failure-recovery.md:54` | Evidence step greps `logs/` instead of `reports/logs/`. |
| DOCS-007 | P2 | PROVEN | `Makefile:107-109` vs README/CI | `make lint` mypy is not the strict CI gate that README documents. |
| DOCS-008 | P2 | PROVEN | `README.md:304` + `.env.example:35-37` | README defers to `.env.example`, which still recommends Quarantine Explorer `:8081`. |
| DOCS-009 | P3 | PROVEN | `docs/03-guides/testing.md:1-29` | Lane table prepended **above** the published header; last verified 2026-06-19. |
| DOCS-010 | P3 | PROVEN | `docs/03-guides/getting-started.md:128` | Windows fallback `py -3.13` vs documented 3.12 baseline. |
| DOCS-011 | P3 | PROVEN | `docs/00-project/00-map.md:107-108` | Language policy says architecture docs are Russian; `00-overview.md` is English. |
| DOCS-012 | P3 | PROVEN | `docs/00-project/00-map.md:64` | Navigator shorthand `run/status/resume/repair/force` ≠ actual `workflow run --resume-last/--repair-steps/--force-steps`. |
| DOCS-013 | P3 | PROVEN | `docs/02-architecture/00-overview.md:16` | “Synced with RULES.md v6.1.7”; RULES header is v6.1.10. |
| DOCS-014 | P3 | PROVEN | `docs/05-operations/runbooks/pipeline-failure-critical.md:12` | P0 runbook last verified 2026-04-03; still cites Loki after 2026-07-23 surface reduction. |

Empty-findings rule: **not** `NO_ACTIONABLE_FINDINGS` (14 PROVEN).

## Top remediations (do not apply in this run)

1. Replace `--resume-from` in `pipeline-failure-critical.md` with `--resume` / `--resume-run-id`; drop Loki precondition; re-verify.
2. Rewrite `data-recovery.md` time-travel to `deltalake` Python / rebuild CLI; remove Spark SQL.
3. Rebuild `docs/04-reference/environment-variables.md` from `configs/providers/*.yaml` + README table (no invented keys).
4. Fix `.github/SECURITY.md` examples to keys that exist (`BIOETL_UNIPROT_API_KEY`, `BIOETL_PUBMED_API_KEY`, …).
5. Repair `.github/CONTRIBUTING.md` tables; Windows path `.venv-win`; extras `dev,tests,tracing`.
6. Align `make lint` mypy flags with CI `--strict --no-incremental`, or document `make lint` as a weaker local alias.
7. Stop recommending Quarantine Explorer in the env template README points to (`.env.example` is secret-bearing: **do not edit without explicit user approval**).
8. Move testing-guide lane table below the YAML header; refresh last-verified on P0/P1 runbooks.

## Skipped checks

| Check | Reason |
| --- | --- |
| `python -m memory.tooling.workflow pre-task/post-task` | No shell tool in this agent; memory read from files only. |
| `python -m scripts.docs check-links --links --specs --configs` | No shell; sampled path existence instead. |
| `python -m scripts.docs verify` / MkDocs `--strict` | Docs **pipeline** domain; out of this card’s disjoint scope. |
| GitHub issues | `ALLOW_ISSUE_WRITE=false`. |
| `.env` edits | Guardrail; none performed. |

## Debt / secrets / root

- Debt budgets: **unchanged** (no config edits).
- Secrets in reports: **none**.
- Root clutter: **none** (artifacts under `reports/audit/docs-content/` and run copy).
