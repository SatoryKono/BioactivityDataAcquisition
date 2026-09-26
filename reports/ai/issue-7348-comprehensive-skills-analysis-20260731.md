# Issue #7348 — Comprehensive BioETL Skills Analysis

## Executive summary

- Date: 2026-07-31
- Checkout identity at evidence collection: `a9da0c5c35823adc30385bdf13b1efbef701e11d`.
- Scope: truthful evidence coverage for `py-config-bot`, documentation audit,
  architecture verification, `py-test-swarm`, and `py-review-orchestrator`.
- Overall status: **PARTIAL / ACTION REQUIRED**.
- Production/config/runtime edits: none. This report is the only authored
  analysis artifact; governed memory workflow notes may be generated separately.
- Technical-debt budgets: unchanged.

The config, focused documentation, and focused architecture lanes have current
passing evidence. A current full `py-test-swarm` and a current hierarchical
S1–S8 `py-review-orchestrator` campaign were **NOT_RUN**; their contracts do
not permit relabeling a focused local test run as a completed swarm/review.

## Evidence coverage matrix

| Lane | Status | Current evidence | Honest boundary |
| --- | --- | --- | --- |
| `py-config-bot` validate | PASS | 61 configs validated; 22 pipeline invariant checks; 27 config gap records with 0 findings | `check-config-paths` timed out after 180 s |
| Documentation audit | PASS with findings | #7340 link/spec/config and runtime drift gates passed | Focused ADR-002/017/026 audit, not whole-doc corpus review |
| Architecture verification | PASS with findings | #7340 executed 187 focused tests across architecture/runtime/docs groups | Full `tests/architecture` was not run |
| `py-test-swarm` | **NOT_RUN** | Historical 2026-07-30 artifacts inspected only | Historical flaky DB SHA `3910046d...` does not match current checkout |
| `py-review-orchestrator` | **NOT_RUN** | Historical 2026-07-16 reports inspected only | No current S1–S8 sector delegation/aggregation |

## Current executed checks

### Config validation (`py-config-bot`, mode `validate`)

1. `.venv/bin/python -m scripts.schema validate-configs`
   - PASS: all 61 configs validated.
   - Reported validator surface depths:
     `cross_file=6`, `documentation=1`, `governance_gate=2`,
     `schema_level=1`, `semantic=2`, `snapshot=1`.
1. `.venv/bin/python -m scripts.schema check-invariants --verbose`
   - PASS: `INV-CFG-000` through `INV-CFG-006`.
   - PASS: 22 pipeline configs checked.
1. `.venv/bin/python docs/00-project/ai/agents/scripts/py-config-bot-1.py -v`
   - PASS: 27 configs analyzed (22 standard, 5 composite).
   - Findings: 0 critical, 0 medium, 0 low.
1. `timeout 180s .venv/bin/python -m scripts.schema check-config-paths`
   - **TIMED_OUT**, exit 124, no output.
   - This gate is not claimed as passing. Retry outside the cloud-mounted
     checkout or profile its startup path.

### Reused #7340 documentation and architecture evidence

Source: `reports/ai/issue-7340-specialized-subsystem-analysis-20260731.md`.

- 187 focused tests passed:
  - composite/checkpoint architecture: 28;
  - observability architecture/integration: 40;
  - Medallion/quarantine/Gold: 26;
  - composite resume/storage/quarantine: 55;
  - ADR/docs governance: 38.
- `scripts.docs check-links --links --specs --configs`: PASS.
- `scripts.docs check-drift --runtime-mirrors --freshness`: PASS, 0 errors and
  0 warnings.
- Six documentation findings remain in #7340: two High, three Medium, one Low.

## NOT_RUN gates and blockers

### `py-test-swarm`: NOT_RUN

The skill requires discovery, workload scoring, L2/L3 execution, per-agent
reports/metrics/raw telemetry, aggregates, flaky DB, and a final report
(`.codex/skills/py-test-swarm/SKILL.md:52-60,107-119`). None may be omitted
while calling the result a completed swarm.

Why current historical evidence is insufficient:

- latest discovered swarm report: `reports/codex/review_py-test-swarm_20260730_1543_FINAL.md`;
- its flaky database records Git SHA `3910046d2716606019babc2a272bd64dc2d87982`;
- current checkout was `a9da0c5c35823adc30385bdf13b1efbef701e11d`;
- therefore it is useful historical context, not a current closure gate.

Exact follow-up entrypoint:

```bash
bash scripts/engineering/dev/run_pytest.sh tests/ --collect-only -q
# then execute the full py-test-swarm mode contract with L2 telemetry artifacts
```

### `py-review-orchestrator`: NOT_RUN

The profile requires eight delegated sectors, Wave 1 then dependent S5 Wave 2,
sector reports, and final aggregation. It explicitly forbids L1 from replacing
delegated review with its own spot review. The latest discovered completed
review artifacts are dated 2026-07-16, so they are not current checkout proof.

Exact follow-up: schedule a dedicated S1–S8 campaign with sufficient agent
capacity, then run S5 only after S1–S4 and aggregate every critical/high finding
into the canonical final report.

## Findings

### SKILL-7348-001 — High — review profile has an unsafe interfaces import rule

- Location: `.codex/agents/py-review-orchestrator.md:108-122`, especially line
  114.
- Evidence: S4 says “Interfaces → any layer OK”, while the current architecture
  matrix forbids direct `interfaces -> infrastructure` and requires concrete
  wiring through composition. The profile’s own S5 cross-cutting review is
  supposed to enforce the global import matrix.
- Risk: a sector reviewer can accept a prohibited direct infrastructure import
  before S5, producing contradictory sector evidence.
- Action: change S4 to the canonical matrix rule: interfaces may use domain,
  application, composition, and interfaces, but not infrastructure directly.
- Verification:
  `pytest tests/architecture/test_composite_cli_runtime_config_boundaries.py tests/architecture/test_architecture_dependency_docs_drift.py -q`.

### SKILL-7348-002 — Medium — config skill template uses a noncanonical enricher key

- Location: `.codex/agents/py-config-bot.md:187-205`.
- Evidence: the template uses `optional: false`; every live composite config
  uses `required: false` (`configs/composites/*.yaml`), and the current 61-config
  validator accepts the live form.
- Risk: following the skill literally can scaffold a schema-invalid or
  semantically inverted composite config.
- Action: replace `optional: false` with `required: true` for a required example,
  or `required: false` for an optional example, and align the role-memory
  template in the same runtime/mirror change.
- Verification: rerun `scripts.schema validate-configs` and the config gap tool.

### SKILL-7348-003 — Medium — Windows test-swarm wrapper path is stale

- Location: `.codex/skills/py-test-swarm/SKILL.md:46-50` and
  `.codex/skills/py-test-swarm/references/l1-playbook.md:3-7`.
- Evidence: Windows guidance uses `scripts/dev/run_pytest.ps1`, while the
  governed dev tree and WSL guidance use `scripts/engineering/dev/`. The legacy
  `scripts/dev/run_pytest.sh` path does not exist; the engineering wrapper does.
- Risk: Windows swarm startup can fail before discovery and produce no artifact
  contract.
- Action: verify the PowerShell wrapper’s actual tracked location and update the
  skill, playbook, task brief, and report template together. Run mandatory
  Codex–Junie mirror parity after the runtime change.

### SKILL-7348-004 — Medium — config-path validator is not bounded internally

- Evidence: `scripts.schema check-config-paths` emitted no result before the
  external 180-second timeout, while all other config validators completed.
- Risk: config-only audits can stall on a cloud-mounted checkout and obscure the
  otherwise clean config state.
- Action: profile the command off-mount, identify the slow scan, and add a
  bounded/read-only diagnostic mode if the behavior reproduces. Do not weaken
  or skip path validation in CI.

### SKILL-7348-005 — Low — focused green evidence must not be marketed as comprehensive

- Evidence: #7340 is strong category evidence but intentionally skipped full
  architecture and strict MkDocs; current full swarm/review evidence is absent.
- Action: retain the matrix terminology `PASS`, `PARTIAL`, and `NOT_RUN` in
  issue closeout. Do not state “all skills passed”.

## Prioritized actions

### P1

1. Correct the `interfaces -> infrastructure` rule in the canonical review
   runtime and synchronize mirrors.
1. Run a dedicated current-checkout `py-test-swarm` only when its complete
   telemetry/artifact contract can be satisfied.

### P2

1. Fix the `py-config-bot` composite template (`required`, not `optional`).
1. Re-run `check-config-paths` off-mount and diagnose the 180-second stall.
1. Schedule a real S1–S8 review campaign; do not reuse the July 16 result as
   current proof.
1. Apply the six ADR documentation remediations from #7340.

### P3

1. Normalize all test-swarm wrapper paths across skill references/templates.
1. Add a small architecture guard asserting the review profile’s interfaces
   rule matches the canonical import matrix.

## Skipped checks

- Full test swarm: NOT_RUN; requires complete L1/L2/L3 artifacts and telemetry.
- Full S1–S8 review: NOT_RUN; requires dedicated hierarchical delegation.
- Full `tests/architecture`: NOT_RUN; #7340 used bounded category suites.
- Strict MkDocs: NOT_RUN; #7340 link/nav/drift gates passed, but this is not a
  strict site build.
- `check-config-paths`: attempted, TIMED_OUT after 180 seconds.

## Closeout classification

- Config lane: PASS except one timed-out path check.
- Documentation/architecture lanes: bounded PASS with known documentation
  findings.
- Test swarm lane: NOT_RUN.
- Hierarchical review lane: NOT_RUN.
- Overall: PARTIAL / ACTION REQUIRED.
