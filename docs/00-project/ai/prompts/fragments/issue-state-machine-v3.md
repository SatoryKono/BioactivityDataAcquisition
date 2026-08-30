---
id: prompt.fragment.issue-state-machine-v3
version: 3.0.0
status: active
class: fragment
owner: BioETL Team
summary: Issue FSM v3 — states, transitions, dedupe by fingerprint/root cause, target-branch close gate
---

## Issue state machine v3

### States

| State | Meaning |
|-------|---------|
| `create` | New Issue to be opened (requires `PROVEN` + `ALLOW_ISSUE_WRITE=true`) |
| `reuse` | Existing open Issue/PR already tracks this root cause — append evidence, do not duplicate |
| `defer` | Actionable but below current wave/priority cap or blocked by `MAX_ISSUES_PER_ITERATION` / `MAX_WAVES_PER_ITERATION` — carry to next iteration |
| `blocked` | Cannot proceed (missing evidence, `NOT_PROVEN`, permission/cap, or hard-stop guard) — record exact cause |
| `no_issue` | No actionable finding for this fingerprint (informational or already resolved) |

### Transitions

```
                 ┌─────────────────────────────────────────┐
                 │           Normalize (fingerprint)        │
                 │  sha256(domain|requirement_id|           │
                 │         root_cause|canonical_paths)      │
                 └──────────────┬──────────────────────────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                 │
     no match & PROVEN   match open Issue/PR   NOT_PROVEN / cap hit / guard
              │                 │                 │
              ▼                 ▼                 ▼
     ALLOW_ISSUE_WRITE?      reuse           blocked | defer
        │      │               │
     true   false              │
        │      │               │
        ▼      ▼               │
     create  blocked           │
        │      │               │
        └──────┴───────┬───────┘
                       │
              ┌────────┴────────┐
              │  Implement (F)  │  only on WORK_BRANCH, accepted wave
              └────────┬────────┘
                       │
              ┌────────▼────────┐
              │  Validate (G)   │  same-scope recheck + domain gates
              └────────┬────────┘
                       │
              ┌────────▼────────┐
              │   Close (H)     │  see Target-branch close gate
              └─────────────────┘
```

- `create` is allowed only when finding `status=PROVEN` and `ALLOW_ISSUE_WRITE=true`. Otherwise -> `blocked`.
- `reuse` preferred over `create` whenever fingerprint or root cause matches an open Issue/PR — dedupe, do not duplicate.
- `defer` retains fingerprint for next iteration; does not reset evidence obligation.
- `blocked` MUST record blocking cause and MUST NOT be masked as `DONE`.
- `no_issue` is terminal for the iteration; re-evaluated next iteration via Normalize.

### Dedupe

- **Key:** `fingerprint = sha256(domain|requirement_id|root_cause|canonical_paths)` with sorted canonical repo-relative paths.
- **Scope:** dedupe findings against each other and against open **and** closed Issues/PRs by root cause.
- On collision with open Issue/PR -> `reuse`.
- On collision with closed Issue/PR -> reopen only if acceptance regressed and new `PROVEN` evidence exists; otherwise `no_issue`.
- Invented `REQ-*/DASH-*` IDs forbidden — dedupe key must use real SSOT IDs or literal `GAP`.

### Target-branch close gate (H)

An Issue transitions to closed **only if all hold**:

1. Acceptance criteria proven on `origin/BASE_BRANCH` (not just `WORK_BRANCH` or local checkout).
2. Required checks green on the target branch (no bypass, no admin merge bypass).
3. `ALLOW_CLOSE=true`.

If any condition is false -> remain open (`reuse` or `blocked`) and carry `open_cycle_issues > 0`. Final gate after `N` iterations: `open_cycle_issues > 0` => `BLOCK`.
