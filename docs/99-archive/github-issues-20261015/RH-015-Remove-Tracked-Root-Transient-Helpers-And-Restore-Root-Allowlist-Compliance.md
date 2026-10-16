# Remove Tracked Root Transient Helpers And Restore Root Allowlist Compliance

**Status**: completed_in_repo
**GitHub Issue**: [#4348](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4348)
**Issue State**: closed
**Synced**: 2026-05-29
**Priority**: P1
**Labels**: `governance`, `cleanup`, `infrastructure`, `documentation`, `priority:high`
**Last audited**: 2026-05-19

## Problem

The live repository tree currently violates the published root allowlist and
approved-root policy. Local verification on 2026-05-19 shows:

- unexpected tracked root files:
  - `temp_analyze_conflicting.py`
  - `temp_get_hash.py`
  - `test_output.txt`
- unexpected tracked root directory:
  - `artifacts/`

`artifacts/` is handled separately in `RH-014`. The remaining root files still
need explicit ownership decisions. They look like transient diagnostics or
one-off helper outputs, not canonical repository entrypoints.

If any of them is actually maintained, it needs a proper owner and approved
placement under `scripts/`, `tests/`, `reports/`, or `docs/99-archive/`.
Otherwise it should leave the tracked root entirely.

## Evidence

- `scripts/engineering/repo/audit_root_cleanliness.py`
- `.github/root-allowlist.txt`
- `docs/00-project/governance/03-file-policy.md`
- root tracked files:
  - `temp_analyze_conflicting.py`
  - `temp_get_hash.py`
  - `test_output.txt`

## Proposed Solution

For each tracked root transient file:

1. classify it as one of:
   - maintained helper with canonical owner
   - historical status artifact
   - disposable transient output
2. relocate or delete it according to that classification
3. update any references if the file remains maintained elsewhere

The expected steady state is simple: no transient helpers or outputs remain as
tracked root files.

## Scope

- inspect the content and references of `temp_analyze_conflicting.py`
- inspect the content and references of `temp_get_hash.py`
- inspect the purpose of `test_output.txt`
- move maintained helpers into canonical surfaces such as `scripts/**` or
  `tests/**`
- move historical notes/outputs into `docs/99-archive/**` or `reports/**` only
  if they genuinely need retention
- delete pure transient leftovers from the tracked tree
- keep `.github/root-allowlist.txt` strict; do not paper over drift by adding
  these files unless a governance review explicitly ratifies them

## Non-Goals

- do not run broad cleanup against blocked surfaces
- do not add more root allowlist entries just to make the audit green
- do not reclassify one-off diagnostics as canonical entrypoints

## Acceptance Criteria

- `temp_analyze_conflicting.py` is either removed from tracked root or moved to
  a justified canonical owner path
- `temp_get_hash.py` is either removed from tracked root or moved to a
  justified canonical owner path
- `test_output.txt` is either removed from tracked root or moved to an
  approved archive/report surface with a retention reason
- `.github/root-allowlist.txt` remains limited to intentional root entrypoints
- root audit no longer fails on these transient files

## Validation

```bash
./.venv/bin/python scripts/engineering/repo/audit_root_cleanliness.py --strict-untracked
git ls-files | rg '^[^/]+\\.(py|txt)$'
```

## Risks

- moving a still-used helper without updating references can silently break a
  niche workflow
- archiving disposable outputs instead of deleting them can perpetuate root
  drift through a different surface

## Related

- depends on `RH-014` for full root-hygiene closeout
- follow-up hardening: `RH-016`
