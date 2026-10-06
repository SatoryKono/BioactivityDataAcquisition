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

Full-worktree Git diff operations use the bounded
`source_binding.git_diff_timeout_seconds` value from the proof policy. This
keeps source binding reliable on mounted worktrees without changing evidence
requirements or quality thresholds.

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

### CircleCI producer reuse

`configs/quality/proof_closeout_checks.yaml` owns the exact closeout command
set and branch activation list. The CircleCI adapter is
`scripts/engineering/ci/proof_closeout_runner.py`. Each producer executes once
and writes its command, source binding, workflow identity, job URL, exit code,
sanitized log, and artifact digests under
`reports/quality/proof-or-stop/shared/<check>/`. Log sanitization precedes
receipt creation; transferred evidence must not be rewritten afterward.

The shared `ci_run_id` is `circleci-workflow:<CIRCLE_WORKFLOW_ID>`, not an
individual job URL. Receipts from another workflow are rejected even when
both jobs used the same checkout path. Jobs currently share CircleCI's
checkout path; raw coverage paths and recorded argv are checked exactly.
Evidence reuse across arbitrary filesystem layouts is not supported by this
adapter. Producer job identities remain in their execution records.

On closeout branches, the existing architecture job executes the complete
architecture suite once. Ordinary PRs retain their fast selector. Docs link
and runtime checks emit receipts from the existing docs job. Coverage runs
the unchanged 17 canonical shards across four isolated groups, followed by a
combine job with the existing line and branch thresholds. The standalone
local coverage command still executes all shards sequentially.

Governance uses `pretest_guardrails.sh --reuse-ci-architecture` to validate the
full architecture execution before reusing it for its own targeted subset.
The flag is incompatible with architecture skips and dry runs. Local pretest
behavior without this explicit CI flag is unchanged. The quality gate reads
the verified architecture JUnit with `--architecture-owner junit`; actual
failure, error, and skip counters are retained without another pytest run. The coverage job also
exports a telemetry candidate artifact after persisting immutable measurement
evidence; candidate generation does not replace committed currentness checks.

The final `proof-closeout` job only validates transported evidence and
assembles/verifies the bundle. A missing check, changed command, foreign
workflow or SHA, damaged artifact, failed producer, duplicate/missing shard,
or incomplete coverage blocks admission. Failed upstream jobs block the
aggregator through workflow dependencies and retain their diagnostic logs;
they never become a successful closeout. Raw coverage databases travel only
through the workflow workspace and are not public artifacts.

Rollout verification must compare the complete test selection and successful
17-shard manifest before assessing latency. Parallel groups are initially
static; a claim of twofold speedup requires measured comparable CI runs and
sufficient executor concurrency. Local adapter tests do not prove CI latency
or qualify a CI-trust `ready_to_merge` claim.

## Staged enforcement and rollback

The `proof_or_stop_closeout` entry in
`configs/quality/staged_enforcement_policy_registry.yaml` uses the existing
`observe` → `soft_fail` → `hard_fail` vocabulary. `observe` publishes the
outcome, `soft_fail` adds a visible non-blocking warning, and `hard_fail` blocks
non-admitted closeout.

### Current rollout (#8415)

- **Current stage:** `soft_fail` (non-blocking warning on non-admitted closeout).
- **Rollback stage:** `observe` (return only the Proof-or-Stop aggregator/hook
  stage; do not disable existing quality, debt, architecture, or docs gates).
- **Next stage:** `hard_fail`, gated by soft-fail soak without false-ADMIT and
  independent review of false-reject rate.
- **Promotion prerequisites already required for soft_fail:** zero-false-ADMIT
  adversarial pilot, zero accepted stale/tampered bundles, and two clean CI
  observation runs while the gate was advisory.
- **Owners:** `@bioetl-architecture` (policy), `@bioetl-platform` (escalation).
- **Review cadence:** weekly while below `hard_fail`.
- **Supported surface:** Python `>=3.13`, policy id `bioetl-proof-or-stop-v1`.
- **CI credential posture:** first-party verifier remains offline and
  credential-free; optional vendor evaluators cannot override a mechanical STOP.

Rollback returns the entry to `observe`; existing evidence remains immutable.
Historical proof/evidence artifacts are retained per retention policy and must
not be rewritten or deleted during rollback. Branch-protection changes are
outside this mechanism and require separate authorization.
