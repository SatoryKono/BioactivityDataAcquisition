# [governance] Rebaseline tech-debt planning metrics and Week 0 assumptions

**Status**: open
**Priority**: P2 (Medium)
**Labels**: `documentation`, `governance`, `technical-debt`
**Last audited**: 2026-05-31

## Problem

The 2026-05-31 blueprint refresh invalidated several old planning assumptions:

- Week 0 no longer needs to restore the previously missing evidence files;
  the required evidence surfaces are already present locally
- workflow baseline is now `35`, not `33`
- tracked twin-module ratchet families are now `3`, not `4`
- active program queue target is `29 -> 0`, not `39 -> 0`

If these baselines remain stale in local planning/governance docs, future debt
waves will start from the wrong metrics and may report false regressions or
false completion.

## Evidence

- `docs/99-archive/plans/tech-debt-eradication-blueprint-v4-2026-05-31.md`
- `reports/quality/compatibility-importer-census.md`
- `configs/quality/compatibility_twin_module_ratchet.yaml`
- `reports/quality/hotspot-duplication-baseline.md`
- `docs/config-discrepancies-report.md`
- `.github/workflows/`
- `docs/reports/evidence/project-test-health/metadata.yaml`
- `docs/reports/evidence/project-legacy-compatibility-remediation/06-status/recovered-cross-synthesis-provenance-2026-05-21.yaml`

## Execution Plan

1. Audit local planning docs for stale baseline values and stale Week 0 restore
   instructions.
2. Replace restore-missing-evidence language with reconciliation / rebaseline
   language where appropriate.
3. Update workflow counts, active queue counts, and twin-family counts to the
   current verified baselines.
4. Keep the plan versioned so older snapshots remain historical rather than
   silently overwritten.

## Suggested File Targets

- `docs/99-archive/plans/tech-debt-eradication-blueprint-v4-2026-05-31.md`
- `.github/ISSUES/TECH-DEBT-ZERO-BURNDOWN-EPIC.md`
- any supporting plan or governance doc that still encodes the stale baseline
  values above

## Acceptance Criteria

- No active local planning surface still claims:
  - missing Week 0 evidence files that already exist
  - `33` workflows
  - `4` tracked twin families
  - `39 -> 0` as the active program queue target
- Current baseline values are stated explicitly and tied to repo/GitHub
  verification.

## Validation

```bash
python3 - <<'PY'
from pathlib import Path
print("WORKFLOWS", len(list(Path(".github/workflows").glob("*.yml"))) + len(list(Path(".github/workflows").glob("*.yaml"))))
print("ADR", len(list(Path("docs/02-architecture/decisions").glob("ADR-*.md"))))
PY

rg -n "33 workflows|4 tracked twin|39 -> 0|missing evidence|restore evidence" docs/plans .github/ISSUES -S
python3 -m scripts.docs check-drift --runtime-mirrors --freshness
```
