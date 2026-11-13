______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-11-13'

______________________________________________________________________

# Explicit local AI closeout command

## Trigger

Use for an explicit source-bound closeout after a write-capable task when the
selected runtime has no qualified native lifecycle adapter and the canonical
validation receipts and bundle are available.

## Impact

The facade explicitly writes owned command metadata while reading evidence and
Git/source state. This is not a filesystem restriction on its interpreter or
dependencies. A non-qualified result does not itself establish a pipeline outage.
It prevents a local observation from being represented as admitted completion;
it does not rerun QA, deploy hooks or grant additional permissions.

## Preconditions

Use an existing complete checkout inside the allowed local placement and its
established Python/dependencies. The task must authorize the owned metadata
write. Preserve other writers and all `.env` restrictions. Keep the expected
task/runtime/claim explicit and provide a regular bundle within the checkout.
Do not install dependencies, runtimes or services implicitly.

Start the parent with `-B`, or set `PYTHONDONTWRITEBYTECODE=1` before starting
Python, to suppress interpreter bytecode-cache writes. The worker already uses
both. This does not prevent arbitrary dependency or startup-hook side effects;
the command is not an operating-system sandbox.

## Authority and supported surface

`AGENTS.md` and the active runtime map own the trigger and guardrails. This
runbook explains the explicit command implemented by
[`closeout_runtime.py`](../../../scripts/engineering/repo/closeout_runtime.py),
[`closeout_worker.py`](../../../scripts/engineering/repo/closeout_worker.py) and
[`closeout_state.py`](../../../scripts/engineering/repo/closeout_state.py).
It does not grant tool permissions or define a new precedence.

The command reuses the canonical [Proof-or-Stop contract](../../04-reference/contracts/proof-or-stop-evidence.md),
[ADR-056](../../02-architecture/decisions/ADR-056-proof-or-stop-lifecycle-control.md),
policy and schema. It verifies existing evidence; it does not run its producers.

| Surface                                       | Required support evidence                                                        | State                                                |
| --------------------------------------------- | -------------------------------------------------------------------------------- | ---------------------------------------------------- |
| Explicit repository command                   | Project Python >=3.12 and available owned-process facilities                     | Local command; qualify the actual platform           |
| Codex, Junie, Devin native lifecycle adapters | Version-specific official event contract plus actual invocation/refusal evidence | OFF / NOT_PROVEN; no minimum client version invented |
| OpenCode                                      | Separate subordinate surface and approved installer/workflow qualification       | Disabled write paths remain disabled                 |

The `--runtime` selector identifies the requested consumer; it does not prove
that its client loaded rules, registered hooks or executed this command.
See [hook compatibility](ai-hook-compatibility.md) and
[rules-loading evidence](ai-rules-loading.md) for the separate qualification.
No native config or event registration is installed by this command.

## Procedure

After the existing QA commands produce their canonical receipts and bundle:

```bash
<python> -B -m scripts.engineering.repo closeout \
  --runtime codex --task-id issue-13039 --claim done \
  --bundle reports/quality/proof-or-stop/<run-id>/bundle.json
```

Use the project Windows interpreter or the already qualified WSL/Linux
interpreter. Select `junie` or `devin` for that consumer. The facade resolves
the proof core from its own checkout, not a different editable installation.

Arguments:

- `--repo-root`: existing full checkout root; defaults to the current directory.
- `--bundle`: regular evidence file contained in that root, at most 8 MiB.
- `--task-id`: expected ASCII identifier, 1–128 letters/digits/dot/underscore/hyphen,
  starting with a letter or digit; its digest is retained, not its raw label.
- `--runtime`: exactly `codex`, `junie` or `devin`.
- `--claim`: `tested`, `reviewed`, `done` or `ready_to_merge`.
- `--event-id`: optional 32-character lowercase UUID hex. A new ID is generated
  by default. Reusing an event refuses execution; it is not a retry switch.
- `--timeout`: owned-worker deadline, greater than zero and at most 120 seconds.
  Parent/worker state bookends also perform bounded Git and local file reads.

There is no arbitrary command, policy override, source-check bypass, trust-tier
override or self-approval argument. Repository `.env` and worktree-location
guardrails still apply. The facade's explicit output is its owned command
metadata; it does not request a checkout, machine config or Git hook installation.
Interpreter and dependency effects remain subject to the preconditions above.

## Verification

The worker uses `memory.proof.verify_bundle(check_current_source=True)`. Its
canonical `core_outcome` is separate from the explicit command's effective local
outcome. A caller-supplied CI run label or `ci_identity` string is not authenticated
transport, even when a bundle's hashes and policy fields are valid.

| Effective outcome | Exit | Meaning                                                                         |
| ----------------- | ---- | ------------------------------------------------------------------------------- |
| `DEGRADED`        | 3    | Existing evidence verified at the local boundary; no admitted lifecycle claim   |
| `STOP`            | 2    | Core rejection or foreign task/runtime/claim/branch                             |
| `ERROR`           | 2    | Missing/corrupt state, metadata, dependency, process, cleanup proof or deadline |
| `USER_STOP`       | 130  | Actual parent `KeyboardInterrupt` after owned-runner cleanup                    |

`claim_qualified`, `runtime_admission`, `ci_acceptance` and
`native_event_observed` are always false. There is no successful local `ADMIT`
path. A worker return code 130 is an execution failure, not evidence that a human
stopped the parent. The worker's operational zero only says a result was written;
the facade still returns the effective nonzero outcome above.

Unavailable/failed/skipped receipts and `DEGRADED` never become `PASS` or a
qualified done/merge assertion. Actual CI checks and authenticated producer
identity remain separate evidence on the exact current PR head. The existing
`soft_fail` rollout is not promoted to `hard_fail` by this command.

## State and metadata

The expected task/runtime/claim and current branch are checked before expensive
measurement and independently in the worker. A request binds bundle bytes,
HEAD/base, semantic default and supplied indexes, shallow-history boundaries,
changed source/checker bytes, canonical core/policy/schema bytes and environment
identity. State and bundle bookends reject changes during execution.

Package inventory enumerates equivalent physical metadata search roots once
and retains entries from distinct roots even when names and versions repeat.
It does not attest installed package contents or the location of one replacement
installation with the same name and version.
Git evidence queries discard inherited `GIT_*` controls and retain only an
explicit supplied index as an additional view. The standalone budget guard
preserves this policy without requiring an importable repository package.
File-state fingerprints include content and permission mode; the POSIX
regression exercises an execute-bit change after the canonical verifier.

The canonical proof diff now includes the default staged tree. Old bundles must
be regenerated after this source-binding change, never relabelled. A supplied
alternate index must match the canonical default index semantically; a different
proposed staged tree is not represented by that canonical bundle and is refused.
Sparse/hidden/intent-to-add or unmerged indexes retain the existing refusals.

Owned metadata lives under the common Git directory:
`bioetl-closeout-commands/<event-id>/`. Exclusive event reservation and worker
lock prevent duplicate, recursive and concurrent reuse. Each request/result is
bounded, regular-file checked and written once. Crashes leave evidence for
inspection; no prior event, callback or unrelated state is overwritten or deleted.
The command does not automatically retry or reuse a static check cache.

Bundle bytes pass through the inherited regular-file stream, not a copied
request payload. Metadata stores digests, controlled verdicts and counts; raw
bundle content, environment values, child output and exception diagnostics are
not retained. Malformed worker fields are not echoed. Local hashes detect stale
or corrupt state; a same-user adversary able to forge all local metadata is not
authenticated by these hashes.

## Process and filesystem limits

The fixed literal worker entry uses the existing owned process runner. Windows
uses suspended children assigned to a kill-on-close job; qualified Linux/WSL
requires its subreaper/pidfd facilities. Missing cleanup evidence and forced
supervisor failures remain errors. This is not a filesystem or network sandbox.

Git object reads ignore replacement refs; fsmonitor and textconv execution are
disabled. Selected clean/process filters are rejected before diff measurement.
Because Git prints special attribute states and equally named driver strings
identically, ambiguous configured driver names may conservatively be refused.
Unused ordinary filter configuration is allowed. Preflight does not isolate a
hostile concurrent writer changing Git configuration or attributes.

Root dotenv bookends cover only top-level `.env*` files in the selected root.
They do not intercept arbitrary writes to another worktree's `.env`, ignored
nested files or other paths, and detection cannot undo an already performed
write. The broader instruction-level `.env` prohibition remains mandatory.
The worker has ordinary host-user permissions; CI cannot attest a different
machine's local secret files.

No agents, provider requests, external services, EvidenceStore ingestion or
native runtime activation are launched. No new wall-clock evidence TTL is
invented: freshness is canonical source binding, separate from any owning
producer's age policy and from the static-cache TTL in
[scoped post-change checks](scoped-post-change-checks.md).

## Rollback/Recovery

Stop invoking this explicit facade; there is no native adapter to uninstall.
Preserve its event metadata and original evidence. A reviewed follow-up can
remove the facade route and coupled helper/runtime/docs changes together.
Retain the separate proof-core Git callback and staged-tree hardening, their
regressions, and the requirement to regenerate old bundles. Do not blanket-revert
those protections with an adapter rollback.

The fallback remains canonical source-bound Proof-or-Stop verification with
honest local trust and non-qualified `DEGRADED`/`STOP` reporting. Keep the warning
that local CI labels do not authenticate transport. Keep native adapters and
OpenCode write paths off, the existing staged-enforcement policy, `.env`, tree
placement, debt, full-tree and runtime parity guardrails, and all existing
Git/CI checks. Git-hook installation/rollback is a separate explicit procedure;
this command never replaces foreign callbacks or grants host deployment approval.

## Post-incident

Retain the event ID, controlled verdict, source identities and digests; preserve
original bundles and command metadata. Inspect the owning evidence and exact
checkout before a new attempt. Missing dependencies, changing source and cleanup
failures require their own diagnosis; elapsed time is not a fix. Use a new event
only after the cause is addressed, and report checks not run without converting
them to success. Do not publish raw bundle content, config values or child logs.

## Compliance

The [root contract](../../../AGENTS.md),
[normative index](../../00-project/NORMATIVE_SOURCES.md) and
[post-change policy](../../00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md)
remain authoritative in their scopes. This runbook cannot waive `.env`, local
tree placement, debt, full-tree, source-first runtime parity or validation rules.
