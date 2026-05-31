______________________________________________________________________

Version: 4.0.0
Status: active
Class: plan
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-31'

______________________________________________________________________

# BioETL Tech Debt Eradication Blueprint v4

Дата snapshot: `2026-05-31`

Этот документ актуализирует внешний snapshot `v3 (2026-05-30)` по
первичным источникам текущего репозитория и GitHub REST API.

Источники верификации для `v4`:

- GitHub REST API `repos/SatoryKono/BioactivityDataAcquisition/issues/*`
- `git show 768cfdfe a39e1d7 e427464`
- `pyproject.toml`
- `docs/02-architecture/decisions/README.md`
- `reports/quality/compatibility-importer-census.md`
- `reports/quality/hotspot-duplication-baseline.md`
- `docs/config-discrepancies-report.md`
- `configs/quality/compatibility_twin_module_ratchet.yaml`
- `configs/quality/test_governance_audit.yaml`

## Executive Summary

`v3` больше нельзя использовать как current-state blueprint без поправок.
На `2026-05-31` подтверждены следующие изменения:

- active tech-debt program queue сократилась с `39` до `29` open GitHub issue;
- `Stream D` и `Stream E` больше не активны:
  `#4266`, `#4268`, `#4276`, `#4292`, `#4293`, `#4294`, `#4295`, `#4296`,
  `#4316`, `#4747` закрыты на GitHub `2026-05-30`;
- локальные Week 0 evidence-gap claims из `v3` устарели:
  `docs/reports/evidence/project-test-health/metadata.yaml`,
  `reports/quality/compatibility-importer-census.md`,
  `docs/reports/evidence/project-legacy-compatibility-remediation/06-status/recovered-cross-synthesis-provenance-2026-05-21.yaml`,
  `reports/quality/hotspot-duplication-baseline.md`,
  `reports/quality/dead-code-inventory.md` уже присутствуют в working tree;
- локальный `.github/ISSUES/TECH-DEBT-ZERO-BURNDOWN-EPIC.md` частично stale:
  он всё ещё показывает `#4814` как `closed`, но GitHub source of truth держит
  issue `open`;
- baseline changed:
  workflows `35`, а не `33`;
  tracked twin families `3`, а не `4`, потому что `_run_manifest_support`
  уже выведен из twin-ratchet после `e427464`.

Практический вывод: `v4` сводит активный план к потокам `A-C`; `D-E` переходят
в archival/watch mode и возвращаются в execution только если GitHub issue
reopen или repo evidence снова сломается.

## Snapshot Reconciliation: v3 -> v4

| Area | v3 claim | v4 verified state | Source |
| --- | --- | --- | --- |
| Active queue | `39` open issue across Streams A-E | `29` open issue across Streams A-C | GitHub REST API, 2026-05-31 |
| Stream D | `9` open divergence issues | `0` open; all 9 closed `2026-05-30` | GitHub REST API issues `#4266/#4268/#4276/#4292-#4296/#4316` |
| Stream E | `#4747` active | `#4747` closed `2026-05-30T11:36:50Z` | GitHub REST API issue `#4747` |
| Week 0 evidence restore | `3` required files absent | required evidence files already present locally | working tree verification |
| Workflow baseline | `33` workflows | `35` workflow files under `.github/workflows/` | repo scan |
| TDX-003 status | implicit closeout via local epic | `#4814` is still `open` on GitHub | GitHub REST API issue `#4814` |
| Twin-module ratchet | `4` tracked families incl. `run_manifest_support` | `3` tracked families; `run_manifest_support` family removed | `configs/quality/compatibility_twin_module_ratchet.yaml`, commit `e427464` |
| Stream D divergence premise | local closed vs GH open for `#4276/#4292/#4296` | divergence resolved; local mirror now matches GH `closed` | local issue mirrors + GitHub REST API |

## Verified Baseline (2026-05-31)

### Repository

- Python runtime target remains `>=3.12`; classifiers explicitly include
  `3.12` and `3.13`.
- Workflow count is `35`.
- ADR registry contains `48` ADR markdown files.
- `ADR-003` and `ADR-008` remain `Superseded`.

### Contract / control-plane deltas that stay binding

- ChEMBL target contract `v2.0` is live:
  `docs/04-reference/contracts/gold/chembl_target_v2.0.json`.
- Control-plane unify wave from `a39e1d7` is already on `main`; Stream C must
  assume post-unify public owner modules as baseline.
- `_run_manifest_support` was retired as a private twin in `e427464`; return of
  a private `run_manifest_support` surface is a ratchet regression, not a valid
  refactor option.

### Current debt/evidence baselines

- `reports/quality/compatibility-importer-census.md`
  - retained entrypoints: `14`
  - twin pairs: `14`
  - tracked twin families: `3`
  - config-root symbols: `3`
- `reports/quality/hotspot-duplication-baseline.md`
  - total duplicate clusters: `142`
  - composition clusters: `38`
  - application clusters: `104`
- `docs/config-discrepancies-report.md`
  - total configs: `26`
  - total unique parameters: `508`
- `configs/quality/test_governance_audit.yaml`
  - `compatibility_test_file_max: 56`
  - ratchet refreshed on `2026-05-31`

## Active GitHub Queue (program scope only)

Repo-wide open issues on `2026-05-31`: `100`.

`Blueprint v4` intentionally scopes only the active tech-debt eradication
program queue:

- `29` open issues total
- labels inside this scoped queue:
  - `architecture`: `20`
  - `technical-debt`: `17`
  - `tech-debt`: `12`
  - `compatibility`: `11`
  - `P1`: `8`
  - `P0`: `6`
  - `P2`: `4`
  - `config`: `4`

### Stream A — active (`12` open)

- epic: `#4811`
- P0:
  - `#4812` runtime_builders duplicate clusters
  - `#4813` application/core duplicate clusters
  - `#4814` bootstrap/runtime duplication
  - `#4815` control_plane helper duplicates
- P1:
  - `#4816` twin-module ratchet growth
  - `#4817` compatibility test-file debt
  - `#4818` config-contract drift
  - `#4825` pipeline-config-contract owner traces
  - `#4827` compatibility importer no-growth budgets
- P2:
  - `#4820` dead-code catalog ownership
  - `#4826` compatibility test-file debt ownership

Closed Stream A sub-tasks already off the active queue:

- `#4819` closed `2026-05-30`
- `#4821` closed `2026-05-30`
- `#4828` closed `2026-05-30`

### Stream B — active (`9` open)

- `#4764` umbrella program
- `#4765` YAML parse gate for `contracts/chembl/activity.yaml`
- `#4766` CLI health composition seam
- `#4767` contract coverage matrix + Gold parity
- `#4768` strict Gold validation + composite waiver policy
- `#4769` release-critical Bronze fixture gaps
- `#4770` compatibility usage graph + no-new-shim gate
- `#4771` low-risk shim removal batch
- `#4772` warnings-as-errors outside compatibility suites

### Stream C — active (`8` open)

- `#4610` AR-002 control-plane decomposition
- `#4700` collapse control-plane compatibility shims
- `#4701` narrow composition/config facades
- `#4702` workflow/run-manifest duplication
- `#4703` deterministic replay identity
- `#4704` test-governance drift + ratchet budgets
- `#4705` debt governance unification
- `#4706` retirement triage

### Stream D — archived unless reopened (`0` open)

GitHub closed on `2026-05-30`:

- `#4266`, `#4268`, `#4276`, `#4292`, `#4293`, `#4294`, `#4295`, `#4296`,
  `#4316`

Execution implication:

- remove Stream D from active critical path;
- keep only evidence-watch verification if these surfaces regress or GH issues
  reopen.

### Stream E — archived unless reopened (`0` open)

- `#4747` closed on `2026-05-30`
- local mirror `.github/ISSUES/SECURITY-4747-Env-Prefix-Policy-Exception.md`
  already matches current GitHub state

## Updated Roadmap

### Week 0 — rebaseline and stale-mirror cleanup

This is no longer an evidence-restore week. It is now a reconciliation week:

1. Sync stale local planning surfaces with GitHub state:
   - `.github/ISSUES/TECH-DEBT-ZERO-BURNDOWN-EPIC.md`
   - any local plan/report still claiming Stream D/E are active
2. Re-run baseline gates:
   - config matrix
   - root cleanliness
   - debt scorecard
   - targeted architecture/governance suite
3. Lock the active execution queue to Streams `A-C`.

Exit:

- no local plan still treats `#4814` as closed;
- no current plan still treats Stream D/E as active;
- active queue explicitly equals the `29` open issues above.

### Weeks 1-3 — Stream A core (P0)

Priority order:

1. `#4812`
2. `#4813`
3. `#4814`
4. `#4815`

Notes:

- `#4814` is back in the active path because GitHub still marks it open.
- `#4815` remains the key internal sequencing gate for Stream C.

### Weeks 3-5 — Stream B core

Priority order:

1. `#4765`
2. `#4766`
3. `#4767`
4. `#4768`
5. `#4769`

Notes:

- `#4767` remains the prerequisite for Stream A `#4818`.
- ChEMBL target `v2.0` must remain under ADR-036 migration discipline.

### Weeks 5-7 — Stream A residual

- `#4816`
- `#4817`
- `#4818`
- `#4820`
- `#4825`
- `#4826`
- `#4827`

Notes:

- twin-module ratchet now tracks `3` families, not `4`;
- `compatibility_test_file_max` remains pinned at `56` until real retirement
  lowers the live count.

### Weeks 6-8 — Stream C

- `#4700`
- `#4701`
- `#4702`
- `#4703`
- `#4704`
- `#4705`
- `#4706`
- `#4610`

Ordering rule:

- do not start `#4700` / `#4610` before Stream A `#4815` lands.

### Week 9 — Stream B residual

- `#4770`
- `#4771`
- `#4772`

This wave is no longer paired with Stream E because `#4747` is already closed.

### Week 10 — closeout

Closeout target is no longer “39 -> 0”; it is:

- active program queue `29 -> 0`;
- no reopened Stream D/E regressions;
- no stale local mirror contradicting GitHub state.

## Current Execution Queue

### Now

1. Refresh local plan/mirror surfaces that still encode stale issue state.
2. Run baseline governance checks for config matrix, debt scorecard, root
   cleanliness, and targeted architecture suites.
3. Start implementation backlog with:
   - Stream A `#4812`
   - Stream B `#4765`

### Next

1. Stream A `#4813` and `#4814`
2. Stream B `#4766` and `#4767`
3. Stream C prep only after `#4815`

### Blocked by internal sequencing

- `#4815` blocks `#4700` and `#4610`
- `#4767` blocks `#4818`
- Stream A residual ratchets block `#4770/#4771/#4772` from becoming stable
  enforcement

## Validation Commands (v4)

Use GitHub REST API in this workspace because `gh` is not installed locally.

```bash
# Active queue snapshot
python3 - <<'PY'
import json, urllib.request
url = "https://api.github.com/repos/SatoryKono/BioactivityDataAcquisition/issues?state=open&per_page=100"
with urllib.request.urlopen(url) as r:
    data = json.load(r)
print(len(data))
PY

# Targeted issue states
curl -fsSL https://api.github.com/repos/SatoryKono/BioactivityDataAcquisition/issues/4814
curl -fsSL https://api.github.com/repos/SatoryKono/BioactivityDataAcquisition/issues/4747
curl -fsSL https://api.github.com/repos/SatoryKono/BioactivityDataAcquisition/issues/4292

# Baseline governance
uv run python -m scripts.schema generate-config-matrix --check
uv run python docs/00-project/ai/agents/scripts/architecture-techdebt-automation.py
uv run python -m pytest tests/architecture/test_quality_debt_scorecard.py -q
uv run python -m pytest tests/architecture/test_regression_metrics.py -q
uv run python -m pytest \
  tests/architecture/test_compatibility_importer_census_governance.py \
  tests/architecture/test_compatibility_freeze_guards.py \
  tests/architecture/test_bootstrap_layer_boundaries.py \
  tests/architecture/test_pipeline_config_idempotency_contract.py -q

# Root hygiene
./.venv/bin/python scripts/engineering/repo/audit_root_cleanliness.py --strict-untracked
uv run python -m scripts.engineering.repo check-cleanliness --strict-untracked --check-local-forbidden-outputs
```

## Rules For This v4 Wave

- GitHub issue state is source of truth for execution status.
- Local `.github/ISSUES/*.md` mirrors may lag and must be synchronized when they
  contradict GitHub.
- Do not spend execution budget on Stream D/E unless a GitHub reopen happens.
- Do not treat `_run_manifest_support` as a valid private compatibility seam;
  any return would be a regression.
- Keep ADR-036, ADR-046, ADR-047, ADR-048 constraints unchanged.
- Keep Python baseline `>=3.12`; do not backport the plan to older runtimes.

## Definition Of Done For v4

`v4` is complete only when all of the following hold:

1. Active tech-debt eradication queue reaches `0` open issues across Streams
   `A-C`.
2. No Stream D/E issue has reopened without a documented new evidence pack.
3. Local planning mirrors no longer contradict GitHub on issue open/closed
   state.
4. Twin-module ratchet remains at `3` tracked families with no growth.
5. `compatibility_test_file_max` is reduced or kept flat with explicit owner
   rationale.
6. ChEMBL target `v2.0` remains green under contract/config/test validation.
