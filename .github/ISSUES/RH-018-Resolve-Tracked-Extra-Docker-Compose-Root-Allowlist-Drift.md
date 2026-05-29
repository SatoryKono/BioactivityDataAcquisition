# Resolve Tracked Extra `docker-compose.*` Root Allowlist Drift

**Status**: active
**Priority**: P2
**Labels**: `governance`, `infrastructure`, `cleanup`, `priority:medium`
**Last audited**: 2026-05-21

## Problem

The live repository root currently contains tracked compose files that are not
listed in the canonical root allowlist:

- `docker-compose.alertmanager.yml`
- `docker-compose.minio.yml`
- `docker-compose.redis.yml`
- `docker-compose.sonarqube.yml`

`python3 scripts/engineering/repo/audit_root_cleanliness.py --strict-untracked`
therefore fails on tracked root-file drift.

This is a governance defect, not a statement that the files are technically
invalid. If these compose surfaces are maintained, they need explicit policy
ratification and documentation alignment. If they are legacy or optional
leftovers, they should move or leave the tracked root.

## Evidence

- `python3 scripts/engineering/repo/audit_root_cleanliness.py --strict-untracked`
  reports unexpected tracked root files:
  - `docker-compose.alertmanager.yml`
  - `docker-compose.minio.yml`
  - `docker-compose.redis.yml`
  - `docker-compose.sonarqube.yml`
- `.github/root-allowlist.txt` currently allows:
  - `docker-compose.monitoring.yml`
  - `docker-compose.codex.yml`
  - `docker-compose.neo4j-audit.yml`
  - `docker-compose.neo4j.yml`
  - `docker-compose.yml`
- `docs/00-project/governance/03-file-policy.md`
- the tracked files themselves

## Why This Matters

- Root allowlist is the published source of truth for tracked root files.
- The project runtime baseline is local-only by default, so extra compose
  surfaces need explicit justification rather than silent accumulation.
- Allowlist drift keeps root-hygiene verification red even if the files still
  happen to work locally.

## Proposed Solution

For each of the four compose files, make an explicit owner decision:

1. retain as intentional tracked root surface and ratify it through
   `.github/root-allowlist.txt` plus any needed docs/policy sync; or
2. move it to a more appropriate maintained location if root placement is not
   justified; or
3. remove it from the tracked tree if it is obsolete.

Do not paper over the issue by ignoring root audit failures without classifying
the files.

## Scope

- inspect active callers/docs for each of the four compose files
- determine whether each file is actively maintained or legacy
- align allowlist and documentation only for files that are intentionally kept
- remove or relocate any file that lacks a justified canonical owner

## Non-Goals

- do not broaden root policy generically for arbitrary compose fragments
- do not introduce Docker as a required runtime baseline for BioETL
- do not touch unrelated root-hygiene topics in the same change

## Acceptance Criteria

- every retained compose root file is explicitly justified by policy and listed
  in `.github/root-allowlist.txt`
- any obsolete compose root file is removed or relocated
- `python3 scripts/engineering/repo/audit_root_cleanliness.py --strict-untracked`
  no longer fails because of these four files

## Validation

```bash
python3 scripts/engineering/repo/audit_root_cleanliness.py --strict-untracked
git ls-files | rg '^docker-compose\\..*\\.yml$'
rg -n "docker-compose\\.alertmanager|docker-compose\\.minio|docker-compose\\.redis|docker-compose\\.sonarqube" .github docs scripts tests configs README.md Makefile pyproject.toml
```

## Risks

- deleting a still-used compose surface without owner review can break a niche
  local ops workflow
- retaining the files without allowlist/doc sync preserves red governance checks

## Related

- independent of retention-sensitive cleanup lanes
- can be resolved in parallel with the `concepts/` root-surface issue
