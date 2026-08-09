# Proof-or-Stop evidence contract

## Purpose

Proof-or-Stop controls lifecycle transitions for agent work. Text emitted by an
agent is a **claim**; it is never sufficient by itself to mark work tested,
reviewed, done, or ready to merge. A lifecycle consumer may accept the claim
only after the offline verifier admits a source-bound evidence bundle.

The model follows the operational pattern described by
[Proof-or-Stop](https://arxiv.org/abs/2607.14890): actor output → claim →
evidence → gate → lifecycle transition. It proves that declared checks ran for
the declared repository state. It does not prove semantic correctness beyond
those checks.

## Claims and outcomes

Supported claims are `tested`, `reviewed`, `done`, and `ready_to_merge`.
Verification returns exactly one outcome:

- `ADMIT`: complete, authorized, integrity-checked evidence at a trust tier
  allowed to qualify the claim.
- `STOP`: missing, failed, stale, cross-scope, unauthorized, malformed, or
  tampered evidence. An unsupported or compromised producer also stops.
- `DEGRADED`: evidence was skipped or unavailable with an explicit reason and
  follow-up, or execution has digest-only local trust. Degraded is not pass and
  never qualifies a full-trust `ready_to_merge` claim.

Unavailable infrastructure is not success. Gate failure never creates a
waiver, override, or `DecisionRecord` automatically.

## Source binding and receipts

Every bundle binds the claim to repository, branch, worktree, task, actor,
runtime, and trust tier. The source identity contains:

- `head_sha`;
- a material tree hash excluding `reports/quality/proof-or-stop/`;
- the task diff hash, including non-ignored untracked files;
- the proof policy hash;
- the claim-specific command-set hash.

Each receipt records the producer, evidence kind, command and argv, cwd,
timestamps/duration, exit code, output digest, source identity, and one of
`pass`, `fail`, `skip`, or `unavailable`. A skip or unavailable receipt must
carry both `skip_reason` and `follow_up`. Fail-fast producers still publish a
partial `fail` receipt.

The JSON contract is
`configs/quality/proof_or_stop_bundle.schema.json`; the policy is
`configs/quality/proof_or_stop_policy.yaml`.

## Trust tiers

| Tier | Attestation | Maximum outcome |
| --- | --- | --- |
| `local_single_host` | Content digests only | `DEGRADED` |
| `ci` | CI run/job identity plus digests | `ADMIT` |
| `independent_evaluator` | Independent evaluator identity plus digests | `ADMIT` |
| `unsupported_or_compromised` | None | `STOP` |

No local signing key or secret is introduced. The model is intentionally
offline and vendor-neutral.

## Relationship to post-change validation

`POST_CHANGE_VALIDATION.md` remains the human and agent workflow contract. Its
existing tests, docs checks, runtime parity check, coverage inventory refresh,
and debt gates are evidence producers. Proof-or-Stop composes their receipts;
it does not duplicate their thresholds or replace any existing gate.

CI uploads bundles as ordinary workflow artifacts. Durable EvidenceStore
ingestion is a separate, explicitly authorized operation requiring
`BIOETL_AI_MEMORY_MODE=read-write` and an actor identity. Ingestion records gate
outcomes as immutable evidence events only; it cannot create decisions or
override a stop.

The explicit adapter re-verifies the live repository, task, worktree, policy,
schema, receipt digests, and the binding between `bundle.json` and
`verification.json` before the first durable write:

```bash
BIOETL_AI_MEMORY_MODE=read-write \
BIOETL_AI_RUNTIME=codex \
BIOETL_AI_AGENT=<authorized-agent> \
python -m scripts.engineering.qa proof-or-stop ingest \
  --repo-root . \
  --task-id <task-id> \
  --bundle reports/quality/proof-or-stop/<run-id>/bundle.json \
  --verification reports/quality/proof-or-stop/<run-id>/verification.json \
  --storage-root <authorized-memory-root> \
  --actor <authorized-agent> \
  --runtime codex
```

Valid `pass`, `fail`, `skip`, and `unavailable` receipt outcomes are preserved
as evidence. Corrupt, tampered, stale, unauthorized, or cross-scope material is
rejected before ingestion. Bundle producer provenance and source/output digests
are stored alongside the separate ingestion actor provenance.

## Staged enforcement and rollback

The `proof_or_stop_closeout` entry in
`configs/quality/staged_enforcement_policy_registry.yaml` uses the existing
`observe` → `soft_fail` → `hard_fail` vocabulary. `observe` publishes the
outcome, `soft_fail` adds a visible non-blocking warning, and `hard_fail` blocks
non-admitted closeout. Promotion requires a zero-false-ADMIT adversarial pilot
and two clean CI observation runs. Rollback returns the entry to `observe`;
existing evidence remains immutable. Branch-protection changes are outside
this mechanism and require separate authorization.
