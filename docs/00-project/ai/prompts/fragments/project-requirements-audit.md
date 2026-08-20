---
id: prompt.fragment.project-requirements-audit
version: 1.0.0
status: active
class: fragment
owner: BioETL Team
summary: Bind project-domain audits to REQUIREMENTS.md — REQ-* IDs, gates, issue titles
---

## Project requirements audit contract

Normative catalog: `docs/01-requirements/REQUIREMENTS.md` (171 active rows).
Row-level SSOT: `docs/01-requirements/traceability/requirements-traceability-crosswalk.csv`.
Policy owner: `docs/00-project/RULES.md` + accepted ADRs.
Do **not** invent `REQ-*` IDs. Map a finding to an existing ID or `requirement_id: GAP`.
Dashboard presentation IDs stay `DASH-*` (`DASHBOARD_REQUIREMENTS.md`); `REQ-DASH-*` are the catalog projections of the same family.

### Finding binding

Every PROVEN finding MUST include `requirement_id` (`REQ-ARCH-001`, `REQ-TEST-…`,
`REQ-OBS-001`, …) or `GAP`. Issue title:

`[<domain>][<REQ-id>][P#] one checkable outcome`

Dedupe before create: open **and closed** issues + open PRs
(`uid/path+requirement_id+root_cause`). Do not open a third PR for the same
outcome. Close as DONE only vs `origin/main` (or operator-accepted PR-head).

### Host vs card params

| Surface | Rule |
| --- | --- |
| `prompt.audit.sequential-run` | Host. `N` = inner iterations of **this** domain card (Grok: start at 1; operator may set ≥5). `ALLOW_MERGE=false`. `MONITORING=false`. |
| Dedicated `prompt.audit.cycle.*` | Card table defaults apply only when **not** hosted. Do not run empty inner iterations. |
| `ALLOW_MERGE` | Fail-closed `false` unless the operator explicitly set `true`. |
| Method cards (`docs-content`, `tests-system`, …) | Method only — not a second full pass. |

### Domain → requirement family

| Cycle card | Primary `REQ-*` families | Executable surface (minimum) |
| --- | --- | --- |
| `cycle.docs` | documentation / DOC-GOV-09 | `python -m scripts.docs verify` / `check-drift` / `check-links` |
| `cycle.diagrams` | architecture docs; ADR-040 | `python -m scripts.diagrams lint` + `lint-budget` + `check-artifacts` |
| `cycle.agents-memory` | runtime mirrors; not Prompt Library | `bash scripts/ai/junie/check_junie_mirror.sh --check`; `python -m memory.tooling.workflow smoke` |
| `cycle.configs` | `REQ-CONTRACT-*`, ADR-057 | schema validate `configs/_schema`; compatibility registry; no `.env` edits |
| `cycle.tests` | `REQ-TEST-*`, `REQ-GOV-*` | `configs/quality/test_matrix.yaml`; focused LANE; no skip/xfail budget raise |
| `cycle.tech-debt` | `REQ-GOV-*` non-growth | `configs/quality/debt_scorecard.yaml`; residual snapshot; architecture residual tests |
| `cycle.architecture` | `REQ-ARCH-*` | `tests/architecture/`; `.importlinter`; scorecard refresh |
| `cycle.telemetry` | `REQ-OBS-*`, `REQ-HEALTH-*` | metric inventory; promtool / rule tests; **no** `run_id` labels |
| `cycle.dashboards` | `REQ-DASH-*` / `DASH-*` | `fragments/dashboard-requirements-audit.md` (do not duplicate here) |
| `cycle.coderabbit` | all families above | CR dual-pass; agent PROVEN + `requirement_id` |

### Critical architecture families (REQUIREMENTS.md)

| Family | Evidence |
| --- | --- |
| `REQ-ARCH-*` | `src/bioetl/domain/ports/`, `src/bioetl/composition/`, `tests/architecture/` |
| `REQ-DATA-*` / `REQ-DELTA-*` | Bronze append-only; Silver/Gold Delta; Pandera before persist |
| `REQ-DQ-*` | `configs/quality/`, bounded `bioetl_*` metric names |
| `REQ-BACKFILL-*` / `REQ-CLEAR-*` | replay/rebuild exclusive; incremental skips clear |
| `REQ-COMPOSITE-*` | `configs/composites/`; stable join keys |
| `REQ-OBS-*` / `REQ-HEALTH-*` | ports/adapters; catalog; no invented series |
| `REQ-TEST-*` / `REQ-GOV-*` | deterministic tests; change-set gates; **no debt-budget increase** |
| `REQ-CONTRACT-*` | `configs/base/contract_registry.yaml`; generated artifact drift |

CSV `executable_surface` / `verification_method` win over memory. If the cell
is a named test, run that test (or record `NOT_PROVEN` + blocker).

### Post-change (after a fix)

- `.codex/**` / `.junie/**` → `bash scripts/ai/junie/check_junie_mirror.sh --check`
- `src/bioetl/**/*.py` → refresh `reports/quality/module-coverage-inventory.json`
- Docs/prompts → `python -m scripts.ai.prompts check` when `docs/00-project/ai/prompts/**` changed
- Never raise tech-debt / skip / xfail / hotspot budgets
