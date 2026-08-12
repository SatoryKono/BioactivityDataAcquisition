---
id: prompt.fragment.coderabbit-dual-pass
version: 1.0.0
status: active
class: fragment
owner: BioETL Team
summary: CodeRabbit then agent order for audit and PR review passes
---

## CodeRabbit dual-pass

### Order (default `CODERABBIT=required-then-agent`)

1. **CodeRabbit** (or repo CodeRabbit workflow / CLI as available) on the agreed SCOPE or PR diff.
2. **Agent** re-checks CR output against the tree: keep only items the agent can mark **PROVEN** with path/evidence.
3. Agent-only findings are allowed if CR is empty, but still need PROVEN evidence.

### Audit pass

- Store raw/summary under `…/01-audit/coderabbit/`.
- Map CR items into `findings.json` with `method` including `coderabbit` when sourced from CR.
- Do **not** open issues from CR text alone without agent PROVEN confirmation.

### Review pass (per task / PR)

- After implementation: CodeRabbit on the PR/diff first.
- Then **peer agent** review (the other dual-agent role).
- Do not close the GitHub issue if peer or CR leaves an open **P0** without explicit disposition (`fixed` | `wontfix+reason` | `deferred+issue`).

### Degraded mode

If CodeRabbit is unavailable (rate limit, auth, offline):

- Write `01-audit/coderabbit/DEGRADED.md` with reason and timestamp.
- If `CODERABBIT=required-then-agent`: **block mutations** (`ALLOW_*` writes); plan-only / read-only continues.
- If operator sets `CODERABBIT=agent-only` explicitly: proceed without CR, note in cycle summary.

### Must not

- Paste tokens or private CR payloads into issues/commits.
- Treat CR severity labels as SSOT over repo finding-schema / P0–P3.
- Skip peer review because CR was green.
