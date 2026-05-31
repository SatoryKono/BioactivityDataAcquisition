# [governance] Archive closed Streams D/E in local tech-debt planning surfaces

**Status**: open
**Priority**: P1 (High)
**Labels**: `documentation`, `governance`, `technical-debt`
**Last audited**: 2026-05-31

## Problem

The refreshed blueprint confirmed that Stream D and Stream E are no longer part
of the active execution queue:

- `#4266`, `#4268`, `#4276`, `#4292`, `#4293`, `#4294`, `#4295`, `#4296`,
  `#4316` are closed on GitHub
- `#4747` is closed on GitHub

But the local planning layer still needs a cleanup pass to ensure no active
execution surface continues to treat these streams as in-flight remediation
tracks.

Without this archive step:

- implementers can waste execution time on already-closed tails
- closeout metrics remain inflated (`39 -> 0` instead of `29 -> 0`)
- local planning can keep stale “reconcile Stream D/E first” instructions

## Evidence

- `docs/plans/tech-debt-eradication-blueprint-v4-2026-05-31.md`
- `.github/ISSUES/NONCHEMBL-001-*.md`
- `.github/ISSUES/NONCHEMBL-009-*.md`
- `.github/ISSUES/NONCHEMBL-013-*.md`
- `.github/ISSUES/SECURITY-4747-Env-Prefix-Policy-Exception.md`
- GitHub REST API issues:
  `#4266`, `#4268`, `#4276`, `#4292-#4296`, `#4316`, `#4747`

## Execution Plan

1. Search local planning surfaces for any still-active references to Streams D/E.
2. Convert those references to one of:
   - archived/watch mode
   - historical context only
   - reopen-only contingency
3. Update any queue target text that still assumes the old Stream D/E workload.
4. Preserve already-synced per-issue mirrors as closure evidence; do not reopen
   them locally without new code-level regression proof.

## Suggested File Targets

- `docs/plans/tech-debt-eradication-blueprint-v4-2026-05-31.md`
- `.github/ISSUES/TECH-DEBT-ZERO-BURNDOWN-EPIC.md`
- any `docs/plans/*` or local governance reports that still describe Stream D/E
  as active execution streams

## Acceptance Criteria

- No active local planning surface still presents Stream D or Stream E as
  open execution tracks.
- Stream D/E are represented only as archived, historical, or reopen-only
  surfaces.
- The active queue target is reduced to the live Streams A-C program scope.

## Validation

```bash
python3 - <<'PY'
import json, urllib.request
for n in (4266, 4268, 4276, 4292, 4293, 4294, 4295, 4296, 4316, 4747):
    with urllib.request.urlopen(
        f"https://api.github.com/repos/SatoryKono/BioactivityDataAcquisition/issues/{n}"
    ) as r:
        data = json.load(r)
    print(n, data["state"], data["closed_at"])
PY

rg -n "Stream D|Stream E|39 -> 0|4266|4276|4292|4747" docs/plans .github/ISSUES -S
python3 -m scripts.docs check-links --links --specs --configs
```
