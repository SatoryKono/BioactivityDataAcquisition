# Swarm plan — 20260930-sharded-fix-loop

Mode: fix_failures (phases 0-1), scope: full sharded suite (15 shards, waves 1-4).
Execution: single-agent L1 (self), waves sequential via
`bash scripts/engineering/dev/run_pytest_sharded.sh`. Delegation not used:
failure triage is sequential by wave, no parallel writes needed.

## Baseline (pre-run)

- Tree clean at 67e932214b56; preflight-dirt stash left untouched.
- `.pytest_cache` lastfailed listed ~30 stale failures (unit DQ helpers,
  grafana integration contracts, chembl enum parity, architecture closeouts).
- Prefail blocker (fixed before first run): `check-catalog` failed
  `active 344 > max 338` on HEAD; resync showed 346 active.
  Fix: 8 helper/wrapper scripts triaged to supporting in
  `configs/quality/scripts_lifecycle_registry.json` (2 ×
  mcp_compatibility_wrapper, 6 × shared_helper_module), manifest resynced:
  `scripts=635 active=338`. `check-catalog` and `check-inventory --check
  --check-lifecycle --forbid-evaluate-active` both pass. No budget raised
  (max stays 338, ratchet `max == active` holds).

## Waves

1. wave 1: S1-domain-core, S1-domain-services, S2-comp-iface,
   S7-crosscutting-architecture-a
2. wave 2: S7-a3, S3, S4, S7-b, guardrails-a, guardrails-b
3. wave 3: S5, S6, S7-c, S8
4. wave 4: S7-d

## Loop

Fix failures at root cause (tests first, then production code only for real
defects), rerun affected shards, then full suite. Done when full sharded run
is green including preflight.
