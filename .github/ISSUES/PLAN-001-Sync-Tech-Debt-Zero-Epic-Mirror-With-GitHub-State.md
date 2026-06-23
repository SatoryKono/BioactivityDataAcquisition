# [governance] Sync TECH-DEBT-ZERO epic mirror with current GitHub state

**Status**: open
**Priority**: P1 (High)
**Labels**: `documentation`, `governance`, `tech-debt`
**Last audited**: 2026-05-31

## Problem

The local mirror `.github/ISSUES/TECH-DEBT-ZERO-BURNDOWN-EPIC.md` no longer
matches GitHub state for the active TECH-DEBT-ZERO queue.

Confirmed mismatch on 2026-05-31:

- local mirror still marks `#4814` as `closed`
- GitHub source of truth keeps `#4814` `open`

This breaks the execution protocol for the debt program:

- planners may skip `TDX-003` even though it is still active
- local roadmap ordering becomes inconsistent with the live queue
- closeout math for the epic becomes unreliable

## Evidence

- `.github/ISSUES/TECH-DEBT-ZERO-BURNDOWN-EPIC.md`
- `docs/plans/tech-debt-eradication-blueprint-v4-2026-05-31.md`
- GitHub REST API:
  - `https://api.github.com/repos/SatoryKono/BioactivityDataAcquisition/issues/4814`
  - `https://api.github.com/repos/SatoryKono/BioactivityDataAcquisition/issues/4819`
  - `https://api.github.com/repos/SatoryKono/BioactivityDataAcquisition/issues/4821`
  - `https://api.github.com/repos/SatoryKono/BioactivityDataAcquisition/issues/4828`

## Execution Plan

1. Re-read the current GitHub state for all TECH-DEBT-ZERO sub-issues.
2. Update the status table in `.github/ISSUES/TECH-DEBT-ZERO-BURNDOWN-EPIC.md`.
3. Reconcile the roadmap text so `#4814` remains on the active execution path.
4. Add an explicit note that GitHub state overrides local mirror state when
   they diverge.
5. Re-run doc verification after the mirror sync.

## Suggested File Targets

- `.github/ISSUES/TECH-DEBT-ZERO-BURNDOWN-EPIC.md`
- `docs/plans/tech-debt-eradication-blueprint-v4-2026-05-31.md`

## Acceptance Criteria

- `#4814` is no longer presented as `closed` in the local epic mirror.
- Local TECH-DEBT-ZERO mirror status lines match GitHub for all active and
  recently closed sub-issues.
- The epic roadmap no longer permits skipping `TDX-003` because of stale local
  state.

## Validation

```bash
python3 - <<'PY'
import json, urllib.request
for n in (4814, 4819, 4821, 4828):
    with urllib.request.urlopen(
        f"https://api.github.com/repos/SatoryKono/BioactivityDataAcquisition/issues/{n}"
    ) as r:
        data = json.load(r)
    print(n, data["state"], data["closed_at"])
PY

python3 -m scripts.docs check-links --links --specs --configs
python3 -m scripts.docs check-drift --runtime-mirrors --freshness
```
