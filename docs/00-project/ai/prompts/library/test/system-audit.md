---
id: prompt.audit.tests-system
version: 1.2.0
status: active
class: operator-paste
owner: BioETL Team
runtimes:
- any
params:
- SCOPE
- MODE
- LANGUAGE
- AUDIT_MODE
- REQUIRE_GH_TRACKING
includes:
- fragments/git-safety.md
- fragments/debt-budget-ban.md
- fragments/env-guardrail.md
- fragments/evidence-contract-v3.md
- fragments/language-ru.md
- fragments/audit-scale.md
- fragments/finding-schema.md
related_ssot:
- AGENTS.md
- docs/00-project/NORMATIVE_SOURCES.md
- docs/00-project/ai/agents/guides/TEST_LANE_MENTAL_MODEL.md
- pyproject.toml
anti_patterns:
- Inventing coverage targets not defined by the project
- Treating retries as flaky fixes
- Full-suite runs outside SCOPE without operator approval
- Labeling flaky without repeat counts
tags:
- audit
- tests
- quality
- operator
summary: Audit test system as regression detection, not coverage vanity
max_body_lines: 140
---
# Tests system audit

**Kit:** prompt 2 of `prompt.audit.generic-nine.pack`.
Audit tests as a **regression-detection** system: which product/tech risks are
actually checked, isolation/reproducibility, flaky/disabled zones, and what CI
really blocks on merge/release. Do **not** invent a coverage target.
Retries are a diagnostic signal, not a flaky fix.


**Machine outputs:** always pair `report.md` + `findings.json` under `reports/audit/tests/`. For multi-iteration loops use `prompt.audit.orchestrator` and `reports/audit-runs/<run_id>/`.

## Params

| Param | Default |
| --- | --- |
| `SCOPE` | `tests/` (+ related config) |
| `MODE` | `audit` \| `propose-patches` |
| `LANGUAGE` | `ru` |
| `AUDIT_MODE` | `full` \| `differential` |
| `REQUIRE_GH_TRACKING` | `false` |

## BioETL facts (do not rediscover as unknown)

- Primary stack: Python / pytest (confirm in `pyproject.toml`)
- Use project test lanes / markers; see TEST_LANE mental model (link only)
- Windows: `.\.venv-win\Scripts\python.exe -m pytest …`

## Method

1. Inventory config: `pyproject.toml`, pytest.ini/tox, package manifests, CI
   workflows that run tests.
2. Classify levels present: unit, integration, contract, API, e2e, smoke,
   migration, security, performance — and absences.
3. Find skip/xfail/todo/quarantine/retries/`.only`/shared global state.
4. Confirm canonical command(s); clean-checkout feasibility; single-test run.
5. Map critical product paths → tests; note negative/auth/schema gaps.
6. Suspected flaky: re-run **N** times in controlled env; record N and outcomes.
7. CI gates: required checks, coverage fail-under only if project defines it.

## Checklist (sample)

- [ ] Tests from clean checkout path documented
- [ ] Unit tests not requiring external network by default
- [ ] Isolation of temp dirs/ports/time/random
- [ ] Quarantine has owner + expiry (or flag as debt)
- [ ] Focused tests (`.only`) blocked in CI if applicable

## Surface score (this domain)

| Score | Meaning |
| --- | --- |
| 3 | Critical paths covered; tests isolated/stable; CI actually blocks |
| 2 | Solid base; local gaps or limited observability |
| 1 | Material flaky/disabled zones, weak isolation, or optional CI |
| 0 | Tests broken/absent on critical path, or green CI is fiction |

P0: unsafe/invalid release possible. P1: critical business/security path
unchecked. P2: flaky/perf/diagnostic debt. P3: organization.

## Output

- `reports/audit/tests/report.md` + `findings.json`
- kit extras: `test-matrix.csv`, `coverage-evidence.json`, `flaky-tests.csv`,
  `disabled-tests.csv`, `critical-gap-map.md` (each gap → production risk)
- `surface_score` 0–3; remediations; `MODE=propose-patches` only with approval

## Stop

Do not run unbounded full suites without SCOPE/time budget. Secret/network
abuse risk → stop. `NO_ACTIONABLE_FINDINGS` if green and proven.
