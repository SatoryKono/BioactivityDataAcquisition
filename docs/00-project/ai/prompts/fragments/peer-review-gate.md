---
id: prompt.fragment.peer-review-gate
version: 1.0.0
status: active
class: fragment
owner: BioETL Team
summary: Peer agent review gate after task implementation and before issue close
---

## Peer review gate

After a stream owner finishes a task (code + docs + tests):

1. CodeRabbit dual-pass on the PR/diff (see `coderabbit-dual-pass`).
2. **Peer role** reviews: correctness, scope creep, tests/docs touch, debt budgets, ALLOW_* compliance.
3. Write `05-implement/stream-*/task-<id>/peer-review.json`:

```json
{
  "task_id": "T01",
  "reviewer_role": "A|B",
  "verdict": "approve|request_changes|block",
  "p0_open": false,
  "notes": ["…"],
  "coderabbit_status": "ok|degraded|skipped_explicit"
}
```

### Close rules

- Close GitHub issue only if: acceptance met, required CI green when mutations ran, peer `approve`, no open P0, and `ALLOW_CLOSE=true` (else emit closeout payload only).
- `request_changes` → implementer fixes; re-run peer gate (bounded, e.g. max 2 rounds).
- `block` → stop task mutation; escalate in cycle summary.

### Swap rule

Outer role swap (A↔B) only after every **accepted** task is `done` or `deferred` with reason in `06-cycle-summary.md`.
