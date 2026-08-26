# Docs content audit — `prompt.audit.docs-content`

| Field | Value |
| --- | --- |
| `domain_id` | `docs-content` |
| `prompt_id` | `prompt.audit.docs-content` |
| `prompt_version` | `1.2.0` |
| `SCOPE` | `README.md docs/` |
| `MODE` | `audit` |
| `LANGUAGE` | `ru` |
| `AUDIT_MODE` | `full` |
| `REQUIRE_GH_TRACKING` | `false` |
| Date | `2026-08-26` |
| `surface_score` | **2** (main path exists and is gated; material stale rate/auth tables and one bootstrap contradiction) |
| `blocked` | `false` |
| Debt outcome | `unchanged` (read-only; budgets not touched) |
| `.env` | not created/edited |

## Executive summary

Документация BioETL закрывает критические сценарии онбординга: назначение проекта в `README.md`, Local-Only (ADR-010), uv-first bootstrap, mixed Windows/WSL, CLI, docs-verification, runbooks. Команды проверки в README совпадают с CI type-check (`mypy --config-file pyproject.toml --strict --no-incremental src/bioetl`). Навигатор `docs/00-project/00-map.md` в целом резолвит ключевые относительные ссылки. Счётчик entity-конфигов «22» в README совпадает с `configs/entities/**` (без composite). Версия продукта `6.1.0` совпадает с `pyproject.toml`. Порог покрытия ≥85% совпадает с `--cov-fail-under=85` в CI/`run-tests cov`.

Оценка **не 3**, потому что канонические таблицы rate/auth (README, RULES Appendix A, pipeline specs, welcome page с `Last verified: 2026-08-21`) расходятся с `configs/providers/*.yaml`. Оценка **не 1**, потому что основной bootstrap-path воспроизводим, yaml назван SoT в RULES, а `docs/03-guides/pipeline-configuration.md` уже содержит корректную таблицу `0.1 req/sec` для ChEMBL.

P0 нет. Секретов в SCOPE не найдено (k8s-манифесты — placeholders). Tech-debt бюджеты не менялись. `.env` не трогался.

## Method

1. Inventory: `README.md`, community-health (`CONTRIBUTING.md`, `CHANGELOG.md`, `LICENSE`, `.github/SECURITY.md`, `.github/CODE_OF_CONDUCT.md`), `docs/00-05/**`, `docs/99-archive/**`, `docs/security/**`, `docs/03-data-model/**`.
2. Diátaxis: tutorial (`getting-started`, `quick-start`, tutorials), how-to (guides/runbooks), reference (CLI/contracts/providers), explanation (architecture/ADR/RULES).
3. Commands vs `Makefile`, `pyproject.toml`, `.github/workflows/tests.yml`, `.github/workflows/type-checking.yml`, `src/bioetl/interfaces/cli/**`.
4. Rate/auth/health claims vs `configs/providers/*.yaml` and adapter code.
5. Relative links on README / `00-map.md` / getting-started / quick-start sampled by file existence.
6. TODO/FIXME in `docs/05-operations/**` and `docs/security/**`: operational TODOs without owner not found (only example Codex prompts).

## Surface score rationale

| Dimension | 0–5 | Notes |
| --- | ---: | --- |
| Completeness | 4 | Purpose, bootstrap, CLI, runbooks, env (partial), security policy present |
| Freshness | 3 | Several `Last verified` 2026-03…2026-07; RULES 6.1.11 vs ops README 6.1.4 |
| Consistency | 2 | ChEMBL 3 vs 0.1 rps; OpenAlex email vs api_key; extras mismatch |
| Reproducibility | 4 | README/quick-start uv path matches scripts; getting-started extras claim is false |
| Mapping | `surface_score = 2` because dimension avg ≈ 3.25 (≥ 3.0 → 2 per `fragments/audit-scale.md`) |

## What is correct (sampled)

- README purpose, hexagonal/medallion overview, Local-Only, 22 entity YAMLs, Python 3.12 baseline / 3.12+3.13 classifiers.
- `make install` extras `dev,tests,tests_full,export` — README explicitly warns they differ from Option A `dev,tests,tracing`.
- CLI commands `run`, `quarantine inspect`, `checkpoint list`, `config list-pipelines`, `run-composite`, `workflow run/status` exist in `src/bioetl/interfaces/cli/`.
- `uv run python -m scripts.engineering.dev setup-mcp` is a router over `scripts.ai.codex.setup_mcp`.
- `docs/03-guides/docs-verification.md` documents `python -m scripts.docs verify` and `check-links`.
- `docs/05-engineering/` is an honest stub (DOC-GOV-08).
- k8s under `docs/05-operations/deployment/` is labeled unsupported experiment vs ADR-010.

## Findings (PROVEN preferred)

See `findings.json`. Top items:

1. **DOCS-001 (P2)** — ChEMBL rate `3 req/sec` in README/RULES/specs vs `0.1` in `configs/providers/chembl.yaml`.
2. **DOCS-002 (P1)** — `getting-started.md` falsely equates `uv sync --extra …` with `make install` and uses `py -3.13` on the Windows fallback.
3. **DOCS-003 (P2)** — RULES Appendix A OpenAlex auth `Email (polite pool)` vs `auth_type: api_key`.
4. **DOCS-004 (P2)** — RULES health URL `status.json` vs code `/status`.
5. **DOCS-005 (P2)** — `local-storage-layout.md` omits `data/output/control/` (ADR-044/047).
6. **DOCS-006 (P2)** — `testing.md` references non-existent `tests/infrastructure/**`; body precedes header.
7. **DOCS-007 (P2)** — `00-map.md` structure omits `03-data-model/`, `security/`, `filters/`, `05-engineering/`.
8. **DOCS-008 (P2)** — env-var defaults (`BIOETL_PUBMED_EMAIL`) contradict code/`.env.example`.
9. **DOCS-009 (P2)** — ops README still “synced with RULES.md v6.1.4”.
10. **DOCS-010 (P2)** — pipeline-configuration example YAML still has stale timeout/retries/CB vs live `chembl.yaml`.

## Top remediations

1. Align every ChEMBL rate table with `configs/providers/chembl.yaml` (`0.1` rps, burst `1`) or add an automated docs↔yaml check.
2. Fix `getting-started.md` extras to match `Makefile` `install` and keep Windows fallback on Python 3.12 baseline.
3. Correct RULES Appendix A OpenAlex auth and ChEMBL health URL to match adapters/config.
4. Add `data/output/control/` to `local-storage-layout.md`.
5. Repair `testing.md` header/topology; drop `tests/infrastructure/**`.
6. Extend `00-map.md` structure with `03-data-model/`, `docs/security/`, stub `05-engineering/`.
7. Sync `BIOETL_PUBMED_EMAIL` default across env reference, `.env.example`, and adapter code.
8. Bump ops README RULES pin from v6.1.4 to current header `6.1.11`.

## Inventory (high-level, not a file count)

| Surface | Audience | SoT | Status |
| --- | --- | --- | --- |
| `README.md` | public/eng | onboarding + pointers | active; rate table stale |
| `docs/00-project/RULES.md` v6.1.11 | governance | constitution | active; Appendix A drift |
| `docs/00-project/00-map.md` | all | navigator | active; tree incomplete |
| `docs/03-guides/getting-started.md` | new contributors | onboarding | extras/py version drift |
| `docs/03-guides/quick-start.md` | new contributors | shortest path | extras match README Option A |
| `docs/03-guides/docs-verification.md` | docs owners | quality gates | current |
| `docs/04-reference/cli.md` | operators | CLI | commands exist; last verified 2026-07-06 |
| `docs/04-reference/environment-variables.md` | operators | partial env list | pubmed default drift |
| `docs/05-operations/runbooks/` | ops | incidents | present; ops index pin stale |
| `docs/05-operations/deployment/` | experimental | not ADR-010 | correctly labeled |
| `docs/99-archive/` | historical | non-canonical | OK |
| `.github/SECURITY.md` | security | policy | present |
| `.github/CODE_OF_CONDUCT.md` | community | CoC | present |
| `SUPPORT.md` | community | — | **absent** (P3 completeness; not opened as GH issue) |

## Skipped / NOT_PROVEN

- Live `uv run python -m scripts.docs check-links --links --specs --configs` (no shell in this auditor session). Sampled key relative links by file existence instead.
- Memory `pre-task` / RAG retrieval (no `run_terminal_command`; `BIOETL_AI_MEMORY_MODE` not set).
- Full MkDocs build / generator drift → `prompt.audit.docs-pipeline`.
- Exhaustive link crawl of `docs/02-architecture/diagrams/**` and `docs/00-project/ai/**`.
- GitHub issue write (`REQUIRE_GH_TRACKING=false`).
- Secret values in `.env` (read not required; no leak observed in SCOPE).

## Guardrails

- Tech-debt budgets: not increased.
- `.env`: not created, edited, moved, or deleted.
- Product code: not edited.
- Findings without path-level evidence: marked `NOT_PROVEN` or omitted.
