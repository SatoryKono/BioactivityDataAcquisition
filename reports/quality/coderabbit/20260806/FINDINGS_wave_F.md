# CodeRabbit Wave F FINDINGS (C2 closeout)

- Parent issue: **#7695**
- Blocker issue: **#8032**
- Epic: **#7688**
- Closeout date: 2026-08-06
- Closeout branch: `fix/cr-c2-wave-f-test-honesty`

## Executive status

| Item | Result |
| --- | --- |
| Residual CLI leaves S12–S15 | **Blocked** by product: `Review failed: All files are ignored` |
| Actionable major+ from Wave F CLI | **0** (CLI never produced review findings) |
| Actionable groups published as new path-cluster issues | **0** |
| Test-honesty residual via architecture gates | **1 fixed** — application unit lane purity violation |
| De-dupe vs ARCH-CR2-09 / test governance | Honesty gates already on main; ARCH-CR2-09 closed |

## #8032 root cause (CLI “All files ignored”)

Wave F residual used orphan-scope leaves for test trees:

| Leaf id (scope matrix) | Path focus | Residual CLI status |
| --- | --- | --- |
| `S12-tests-architecture-1/2` | `tests/architecture/**` | All files are ignored |
| `S13-tests-unit-domain-1/2` | `tests/unit/domain/**` | All files are ignored |
| `S14-tests-unit-application-*` | `tests/unit/application/**` | All files are ignored |
| `S15-tests-integration` | `tests/integration/**` | All files are ignored |

Referenced campaign artifacts (operator host, 2026-08-05):

- `/tmp/bioetl-cr-artifacts/20260805/review_S12*`
- `/tmp/bioetl-cr-artifacts/20260805/review_S14*`
- `/tmp/bioetl-cr-artifacts/20260805/review_S15*`

Error pattern (matches Wave E #8031):

```json
{
  "type": "error",
  "errorType": "review",
  "message": "Review failed: All files are ignored\nPrevious local review has no stored findings.",
  "recoverable": false
}
```

### Why config override alone is insufficient

Repo `.coderabbit.yaml` already includes:

```yaml
reviews:
  path_filters:
    - "**"
```

and explicit `path_instructions` for `tests/**/*.py` (observable behavior, VCR, no live I/O).

Local residual still fails because the **local CLI review path is diff-oriented** and treats test-only orphan scopes as non-reviewable when no reviewable product surface is present — independent of `path_filters: ["**"]`.

2026-08-06 re-probe notes:

- CodeRabbit CLI present in WSL (`0.7.2`) with API-key auth available in host env.
- Host→WSL launch failed in this session (`Wsl/Service` connection error); product behavior for pure-test orphan leaves remains documented from 2026-08-05 campaign artifacts and Wave E parity.
- Orphan probe commit with only `tests/architecture/test_any_budget.py` + config was prepared; full CLI re-review was not completed due to WSL transport failure (not a path_filters misconfig).

### Accepted residual path for Wave F

Per #8032 acceptance:

1. ~~Re-run with config override / non-orphan technique for tests~~ — path_filters already open; pure-test orphan residual remains non-productive (same class as Wave E).
2. **Rely on architecture-test gates + targeted CR App PR reviews** — **chosen**.
3. Publish major+ findings if residual succeeds — CLI residual did **not** succeed; gate residual produced **1** honesty fix (below).

## #7695 scope residual (evidence-based)

### A. Scoped honesty gates (no whole `tests/` tree)

Commands (focused; architecture + hot unit placement):

```bash
pytest \
  tests/architecture/test_application_unit_lane_purity.py \
  tests/architecture/test_domain_unit_test_purity.py \
  tests/architecture/test_unit_assert_density_policy.py \
  tests/architecture/test_unit_fast_lane_fs_policy.py \
  tests/architecture/test_repo_backed_marker_hygiene.py \
  tests/architecture/test_integration_vcr_policy.py \
  tests/architecture/test_architecture_closeout_inventory.py \
  tests/architecture/test_closeout_ratchet_triage.py \
  -q
```

Result at closeout: purity gate failure isolated and fixed; remaining listed gates green.

### B. Findings table

| ID | Severity | Path | Claim | Why it matters | Fix class | Acceptance |
| --- | --- | --- | --- | --- | --- | --- |
| WF-01 | major | `tests/unit/application/core/test_stream2_critical_residuals.py` | Module-level imports of `bioetl.infrastructure.storage.*` violated application unit lane purity | Unit application lane must stay on ports/fakes; concrete infra collab belongs in infrastructure unit / integration | test | `tests/architecture/test_application_unit_lane_purity.py::test_application_unit_tests_do_not_wire_concrete_infrastructure` |

### C. Remediation (WF-01)

- Keep stream-2 application residuals in `tests/unit/application/core/test_stream2_critical_residuals.py` (coerce / streaming / vacuum only).
- Move PK sort residual to `tests/unit/infrastructure/storage/support/test_retention_dedup_primary_keys.py`.
- Drop redundant `build_and_validate_metadata` unit case already covered under `tests/unit/infrastructure/storage/metadata/test_metadata_helpers.py`.

### D. Out-of-scope notes (not Wave F product residual)

These gates were observed red on tip during inventory but are **product/budget** surfaces, not CR test-honesty findings for #7695:

| Gate | Observation |
| --- | --- |
| `test_any_budget_*` | 1 unjustified `Any` in `interfaces/cli/commands/cleanup.py` |
| `test_live_residual_snapshot_is_not_regressed_by_live_hotspot_metrics` | `application_core.files_ge_250_loc` live=5 baseline=0 |
| `test_closeout_program_mass_metrics_only_shrink` | closeout test loc mass +2 |

Do **not** raise tech-debt budgets to silence them; track under existing debt/closeout streams if still open.

### E. Continuous residual channel

PR App + `.coderabbit.yaml` `tests/**/*.py` path instructions remain the continuous honesty channel for future test diffs. Local CLI residual for static whole-tree test leaves is **not** a reliable SSOT (same conclusion as Wave E).

## Acceptance checklist (#7695 / #8032)

- [x] Scoped logs / scoped gate runs (no whole `tests/` tree in one CR CLI pass)
- [x] FINDINGS for test debt with acceptance tests named (this document, WF-01)
- [x] #8032: rely on architecture-test gates + CR App PR reviews
- [x] #8032: publish major+ only when residual succeeds — CLI 0; gate residual fixed in-tree
