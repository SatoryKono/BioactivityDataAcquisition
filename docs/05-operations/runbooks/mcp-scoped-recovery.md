______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Platform
Last verified: '2026-11-18'

______________________________________________________________________

# Scoped MCP recovery

This procedure implements RF-001–RF-007 (#13184–#13191). It is subordinate to
the root guardrails and the existing MCP configuration policy. Local process
controls, ordinary Codex tool calls, and CI evidence have separate verdicts.

## Trigger

Use for an unavailable scoped MCP, an unknown owner outcome, runtime source
drift, or configuration synchronization that loses an approved local route.

## Impact

Incorrect roots can expose another workspace. An unsafe retry can duplicate a
committed operation; editing shared runtime files can disable unrelated profiles.

## Preconditions

Follow [AGENTS.md](../../../AGENTS.md), use a complete governed checkout and
identify the actual client/version, account, cwd and target profile. Obtain
authorization for persistent machine configuration and service activation.
Keep field-scoped rollback evidence private. Preserve `.env` files without edits
or copies. Never switch an occupied checkout or enable an unqualified client adapter.

## Procedure

### Configuration ownership

| Surface | Owner and persistence rule |
| --- | --- |
| Tracked portable MCP manifests | `scripts/ai/codex/setup_mcp.py`; never include host paths or credentials |
| Managed user Codex TOML block | `setup_mcp.py`; preserve tool policies, timeouts and unmanaged servers |
| `~/.config/pc-agent/codex-routes.json` | Explicit native transport bindings consumed by the generator for the matching physical Git common directory |
| Workspace editor JSON transport projections | Machine-local route controller; this controller does not own the user TOML |
| `~/.config/pc-agent/markdownify-bioetl.json` | Exact project session binding for the separate Markdownify owner |
| Native session `--config` overrides | `scripts.ai.mcp codex-session`; lifetime limited to the selected invocation |
| Memory profile, graph claim and activation | Registered owner; migration and rollback affect one profile only |

The local native manifest has `schema`, `git_common` and `entries` fields.
Each entry contains only `command` and `args`. It cannot add credentials,
headers, a `cwd`, or a Ref override. An explicitly selected foreign binding is
an error. An implicit user binding does not own another repository's portable
configuration. A profile may omit optional servers without enabling them.

User TOML is validated before atomic publication. Detected concurrent edits
abort publication. Existing per-tool approval settings and enabled/disabled
tool lists are preserved; unsupported existing fields require explicit review.
When a profile omits a managed server, its policy remains in an inactive comment
inside the managed TOML block and is restored when that server returns. The
archive contains policies only; transport and credentials are never archived.
Generation and shell readiness checks use the same validated policy projection,
while canonical transport/authentication changes still fail readiness. Readiness
also rejects managed servers outside the selected profile, even if they appear
outside the generated block; unmanaged servers remain independent. Root inline
MCP tables are normalized when necessary to retain custom server values.
Unchanged output does not replace the file. Back up only changed fields in
owner-private storage and compare current values before restoring them.

The sibling lock coordinates BioETL writers; it does not serialize an external
editor saving between comparison and replacement. When such writers may be
active, use `python -B -m scripts.ai.codex.setup_mcp --codex-only
--stage-codex-config`. This mode prints the unique private candidate path,
preserves the original TOML, and skips validation of an unapplied candidate.
Review it against the latest original and apply it explicitly after coordinating
writers. Ordinary synchronized publication retains its detected-conflict guard.
Fractional startup/tool timeouts are preserved without integer truncation.

### Verify Windows editor projections after synchronization

On a Windows host with the approved route controller, verify two separate
outputs. Generate the selected profile and transport mode into a disposable
`--root`, using the actual checkout as `--workspace-root` and passing
`--skip-codex-config --skip-codex-validation --skip-gemini-settings`.
Run `setup_mcp --check-local` against that same output root, workspace root,
profile, and transport mode to verify the generator baseline.

For the live editor JSON, run the installed `project-route-owner.py plan`
with the approved Windows Python. A successful plan with no changes for the
target checkout confirms the controller would not rewrite its owned routes;
it does not validate the rest of each JSON file. For full parity, apply the
controller's verified renderer to the clean generator output in memory, then
compare the complete result to each live JSON file. Account for separately
approved local settings explicitly; do not blanket-ignore transport drift.
Keep plan details and raw configurations local. Do not overwrite approved
host routes merely to make the baseline check green on the live tree.

Neither comparison proves tool execution. Restart the intended client and
repeat the scoped MCP calls in the actual checkout and worktree.

### Session boundaries

The existing operational CLI exposes `python -B -m scripts.ai.mcp codex-session
--executable <qualified-app-owned-codex.exe> --sha256 <qualified-digest>`.
Run from the actual intended checkout. `--check` validates bindings and prepares
child-only credential delivery without spawning Codex or sending a request.
The selected physical `CODEX_HOME` supplies the validated user TOML and is passed
to the child unchanged. A CLI-scoped Ref entry binds the checked route against
project overlays and concurrent user-TOML edits; only the environment variable
name, never the credential value, appears in that override.
The launcher requires a separately qualified native executable and does not
claim that a currently running ACP/editor client has reloaded its configuration.

For independent RF-004 Ref authentication qualification, add `--ref-only` and
select `--auth api-key`. This invocation enables Ref and disables every other
configured MCP server without changing user TOML or reading Memory, AST or
Markdownify bindings. `--ref-only` cannot be combined with `--acceptance`.
Use `--check` first to inspect the requested Ref-only server set; it starts no
client and leaves native search/read `NOT_TESTED`. Then omit `--check` to open
the ordinary interactive native CLI. Preserve its actual tool-call evidence,
repeat search/read after a client restart and normal synchronization, and
record the qualified client/version/workspace. This does not qualify the
current editor/chat or an SDK probe; RF-007 must repeat Ref controls in its
full multi-server target session.

The launcher compiles explicit Memory/AST and optional Markdownify bindings into
supported per-invocation `--config` transport tables. It preserves existing tool
approval policies, including the separate policy of `memory-acceptance`. The
selector validates and selects routes from one manifest snapshot. This path
leaves the global user TOML unchanged; subsequent
generator synchronization cannot erase these invocation-scoped overrides.
The Markdownify binding must match the exact physical workspace and Git common
directory. A default binding for another workspace disables only Markdownify in
the current session. An explicitly requested foreign binding is refused. Do
not substitute an arbitrary stdio command or a mutable checkout path for the
reviewed installed selector.

The native session selector accepts a service name and inherits its real cwd.
There is no client `--root` override. The nearest Git marker must identify the
canonical checkout or a physically verified linked worktree. Nested unrelated
repositories are rejected. A foreign context cannot borrow an authorized root.

Memory additionally selects the actual registered branch, account and policy.
HEAD is dispatch context, not persistent graph identity. An absent identity
fails closed; selection never initializes a graph or falls back to another
branch. AST identity follows the physical workspace and its credential boundary,
and does not acquire Memory branch/policy semantics.

For the persistence acceptance cycle, provision a separate profile with project
`BioETL-Acceptance-Test` through the normal provider/registry/activation process.
`--acceptance` adds a session-only `memory-acceptance` server whose reviewed
selector derives the same actual workspace, branch and account. It cannot select
an arbitrary graph. Write, reconnect, verify and delete a unique temporary marker
there; retain the test graph and its journal. Do not perform this cycle in the
working `BioETL` graph or infer success from registration alone.

Versioned private clients connect only to an already ready owner. They never
start a persistent backend inside a per-connection Windows Job. Start or ensure
the owner explicitly through its administrative entrypoint before client use.

Verify the selected immutable bundle with `memory-runtime verify --bundle`, then
run its copied interpreter and administrative owner from the matching scope:

```powershell
$bundle = "<selected immutable bundle directory>"
$profile = "<exact registered profile ID>"
& "$bundle/runtime/python/python.exe" -I -S -B "$bundle/tools/shared-mcp/project-memory-owner.py" start --profile $profile
& "$bundle/runtime/python/python.exe" -I -S -B "$bundle/tools/shared-mcp/project-memory-owner.py" status --profile $profile
```

A successful start and a matching ready health/generation establish owner
readiness. They do not establish a successful MCP client connection. Confirm the
latter separately by initialize, tools/list and a substantive scoped operation.
Do not run these administrative commands for an unapproved permanent profile.

The selector owns its child tree in a Windows Job and forwards explicit stdio
handles. Installed selectors use content-addressed source versions and checked
host dependencies. Do not point permanent user configuration at a mutable
checkout script or force a global project cwd.

### Memory versions and recovery

Use the existing MCP operational entrypoint with the approved Windows Python:

```text
python -B -m scripts.ai.mcp memory-runtime audit-profile --profile <profile-id>
python -B -m scripts.ai.mcp memory-runtime build --profile <profile-id>
python -B -m scripts.ai.mcp memory-runtime verify --bundle <bundle>
python -B -m scripts.ai.mcp memory-runtime migrate --profile <profile-id> --bundle <bundle>
python -B -m scripts.ai.mcp memory-runtime reconcile-incident --profile <profile-id>
python -B -m scripts.ai.mcp memory-runtime reconcile-plan --profile <profile-id>
python -B -m scripts.ai.mcp memory-runtime reconcile-apply --profile <profile-id> --plan <private-plan>
python -B -m scripts.ai.mcp memory-runtime rollback --profile <profile-id>
```

`audit-profile` reads historical metadata without pretending its branch is
checked out. It verifies the descriptor and graph claim, validates the graph,
and reports process identity and scope limitations. It never authorizes a start.

Builds retain the legacy files and copy the complete checked service closure:
owner, gateway, broker, adapters, engine snapshot, Python, Node and resolved SDK
dependencies. The directory name binds the manifest bytes; missing, changed or
extra files are rejected. Preserve the exact content-addressed build recipe.

Migration holds registry, profile transition and graph locks. It verifies a
dormant profile and expected registry entry before publishing a profile-local
transaction. An interrupted migration closes the route. Rollback restores only
compatible target metadata and never rewinds a graph or committed operation.
Changed v2 coordination or legacy runtime drift disables the target until
compatible forward recovery. Neighboring profiles keep their original pins.
For that recovery, use `migrate` with a different verified bundle and the
disabled profile's exact retained `--from-version`. This administrative
migration checks the existing journal, profile entry and dormant graph under
the same transition locks. Client dispatch stays closed until the new
transaction commits. A compatible rollback of the recovery restores the
earlier disabled state.

An upgrade of an already versioned profile requires its exact `--from-version`.
The current descriptor, binding and committed (or rolled-back) transaction must
agree. The previous transaction is archived inside that profile before a new
pending record is published. Partial or mismatched predecessors stay closed.
Compatible rollback restores the previous binding, including a previous bundle;
it does not implicitly select legacy. Historical transactions and graphs remain.

The versioned HTTP bridge verifies the complete runtime before sending a
request. Health GETs therefore have a bounded 120-second verification budget;
the legacy five-second budget can expire before network IO starts on a cold
host. This changes only idempotent health checks. Tool requests are never
automatically replayed, and the caller's overall timeout still applies.
Administrative owner startup has a 300-second readiness budget, with 180 seconds
for gateway/backend initialization. These bounds cover the same cold verification
before serving. Shutdown and unknown-process rejection rules remain unchanged;
per-connection clients still connect only to an explicitly started ready owner.

Recovery transitions wait up to five seconds to acquire the control-plane lock.
Only acquisition is retried. An exception inside the critical section propagates
without repeating its body; a lock deadline does not consume a recovery grant.
This prevents the supervisor from exiting merely because `ensure` briefly holds
the same transition lock during startup or observation.

`reconcile-plan` is read-only. Its complete output contains private graph and
coordination fingerprints: keep it in the target profile's private
`reconcile-plans` directory rather than a public report. `reconcile-apply`
rechecks the snapshot under locks and rejects stale, repeated or concurrent
reuse. It publishes one generation-bound grant.

The same decision function governs `ensure`, `start` and `supervise`:

```text
BLOCKED(B1,G1) -> RESOLVED(R1,B1,G1,G2) -> LAUNCHING(G2) -> RUNNING(G2) -> IDLE(G2)
```

The launch consumes R1 before a backend is created. An interrupted successor
needs a new review, and a new incident gets a new block identity. Historical
`blocked.json` remains intact without reblocking an already resolved incident.
Repeated `ensure` reuses the live owner; normal idle restart follows ordinary
recovery rules. A terminated LAUNCHING generation can produce its own incident
only when its status and complete zero-request startup receipt match that
successor and the retained graph stamp. It requires a new plan/grant; the previous
grant remains consumed. An idle receipt requires an explicit `mutating=false`.
New runtimes persist `LAUNCHING/PREPARED` with the owner birth before spawning a
gateway. A dead prepared owner can support a new reviewed plan only when the
original records and graph still match; absence of a receipt alone is insufficient.
Before releasing the gateway nonce, the owner durably publishes its generation's
zero-request startup receipt and `AUTHORIZED` stage. This covers interruption
between grant consumption and successor publication. PREPARED-only proof blocks
migration even for a dead owner: reconcile in that same immutable runtime first.
Only a separately qualified successor zero-request receipt can permit the bounded
upgrade below; migration must not invalidate the hashes needed by PREPARED proof.
A pending RESOLVED grant blocks runtime migration until its reviewed launch is
handled. A LAUNCHING generation also blocks migration unless the dormant-process,
zero-request startup and matching-graph checks in Rollback/Recovery prove the
bounded forward-upgrade exception. That upgrade preserves the consumed grant and
requires a new reconciliation before launch. No uncertain request is replayed.

For an older v2 reconciler that reports BLOCK_NOT_BLOCKED after an interrupted
LAUNCHING generation, the current administrative `reconcile-incident` command
can publish an incident into the existing coordination record. It requires
known dormant processes and the complete matching zero-request startup receipt;
it preserves profile, runtime binding, graph and grant history. It neither grants
a restart nor migrates the runtime. Use the selected old runtime's normal
reconcile-plan/apply flow next, perform the reviewed start, verify it, drain to
IDLE and prove dormancy before migration. Missing/unknown evidence keeps the
profile blocked and requires the documented escalation.

A v2 startup receipt with zero accepted requests, or a complete idle receipt,
can support a reviewed transition. Legacy `starting` without an accepted-request
counter does not prove a safe retry. Unknown/reused PID identity, surviving
processes, graph mismatch and uncorrelated writes remain blocking conditions.
Do not delete a block, rewrite `phase=idle`, reinitialize a graph or switch an
occupied checkout to bypass them.

### Independent safe Markdownify

Administrative commands use `python -B -m scripts.ai.mcp markdownify` with
`prepare`, `start`, `status` or `stop` and the exact administrative root. Native
configuration invokes private isolated `client` mode, which derives its root
from cwd and rejects an explicit root argument.

Each physical root/account has a separate endpoint, DPAPI credential, owner
lock and state directory. The existing server for the workstation's agent
directory remains a separate service. Do not broaden that server's allowed root.

All exposed local-file tools reject traversal, prefix-similar siblings, hard
links, unsupported reparse points and alternate data streams. Directory handles
deny rename while the final file is checked and read through the same handle.
Converters receive a bounded private snapshot, never the original path. Worker
processes run in owned Jobs with isolated Python and no service credential.
Each worker registers only the converter for its qualified snapshot extension;
built-in sniffing and plugins are disabled. ZIP content in an HTML snapshot is
refused. A worker records `PREPARED` before writing input, then `SPAWNING` before process
creation and `RUNNING` after Job attachment and PID/birth publication. The pinned
worker cannot access input before receiving its private stdin nonce; publication
of `RUNNING` precedes nonce release. `CLEANUP` preserves deferred process evidence.
Worker execution has one 70-second budget and cleanup waits at most five seconds,
leaving time within the client's 100-second IO budget for the bounded tool error.
The original operation error survives cleanup failure.
Preparation of an existing profile does not scan a live conversion. On restart
or the next conversion, only proved completed work is reclaimed. A dead owner
before nonce authorization proves the snapshot cannot be used; after authorization,
worker termination and Job closure/owner exit are required. Unknown/live identities
and unowned files remain refusals without signalling another process. Metadata-only
interrupted publication and known atomic-record temporary files are handled inside
the validated private job namespace. Cleanup deletes its canonical journal last,
after snapshots, output and atomic-record temporary files. An interruption after
journal deletion leaves an empty job directory that recovery can safely remove.
Retain unresolved documents for the profile
operator; do not fabricate identity records.

Responses retain the 2 MiB transport limit and encode ordinary Unicode as UTF-8.
An oversized JSON envelope returns a bounded tool error rather than closing a
successful conversion's connection. At most 64 sessions are admitted together.
Sessions expire after 15 minutes without a request; active requests renew that
lease. A session-scoped 404 makes the stdio bridge complete a fresh internal
initialize/initialized handshake. It returns an explicit interruption error for
the original call and continues with the new session; it never replays that call.
HTTP admission is bounded before authentication, with a five-second absolute
header/body read deadline. A conversion acquires its execution slot without
waiting; a busy owner returns a tool error before doing conversion work.
Generation transitions and stop publication share one lock. A stale stop marker
keeps the watcher waiting for the current generation's marker.
The owner publishes its bound loopback port with its generation. The
OS-assigned port is selected only during the actual exclusive bind, rather than
reserved in the prepared profile. Clients use only the published generation's
endpoint. Validation and startup health checks share one 32-second monotonic
budget, including connection and response IO. Stop validates the profile and owner identity
even if the converter snapshot has drifted.
An administrative restart archives a stopped generation before retiring its
status. A known different birth for a reused PID proves the former owner is gone;
that foreign process is left untouched. Unknown birth and a still-live matching
owner remain refusals. Retirement is resumable after a publication interruption.
Explicit `start` can also archive a crashed generation without a stop marker when
its original process is proved gone or its PID has a known different birth. The
replacement process is left untouched; an unknown live PID remains a refusal.

Installed, version-compatible dependencies define candidate formats in the
checked converter snapshot. Before publishing a new schema-2 profile, `prepare`
runs a synthetic representative document for every candidate format, including
HTML, through the same isolated owned worker used by tool calls. The expected
text must survive conversion. The profile binds PASS/FAIL/UNAVAILABLE results to
the exact converter version and advertises only PASS formats. Plugins stay off.
An import error, timeout, wrong content or Windows DLL path-length failure leaves
the format disabled. Existing profiles without this evidence are rejected and
preserved for reviewed activation; do not manufacture PASS flags or overwrite
credentials. Operator path-swap, allow-deny-allow and ordinary-client reconnect
acceptance remain separate. Retain originals and diagnostic evidence.

## Verification

### Ref and ordinary client acceptance

The API-key route uses a key-free `https://api.ref.tools/mcp` URL and
`env_http_headers = { "x-ref-api-key" = "REF_TOOL_API_KEY" }`. Read the existing
root `.env`; do not copy or modify it. Confirm credential delivery to the chosen
client without logging the key or its hash. An OAuth choice is a separate route
without the API-key header/query. Transport failure is not proof of bad auth.

Before closing RF-007, require substantive calls in the chosen ordinary Codex
session after its supported reload boundary and normal configuration sync:

- Memory bounded read and write/reconnect/read/delete in a dedicated test graph;
- file-backed AST search in the actual checkout and authorized worktree;
- Markdownify read/conversion and physical-path/TOCTOU denials;
- authenticated Ref search and read, plus applicable negative controls;
- foreign workspace, nested repository, branch, SID, policy and session-binding
  controls with their actual authority recorded.

SDK/fixture controls and a real second-account process control are useful
evidence, but do not become ordinary Codex-session evidence. Missing mandatory
controls stay `NOT_TESTED` or `BLOCKED`. Phase A (current branch) is independent
of old-main recovery. Phase B requires the versioning/reconciliation tests and
a separate main verdict of `VERIFIED_RECOVERED` or evidence-backed `BLOCKED`.

RAG, timeline and pre-task retrieval remain separate surfaces. Record local
tests, exact HEAD and CI independently. Local receipts do not create CI trust or
permit a `ready_to_merge` claim.

## Rollback/Recovery

Drain only the new Markdownify profile and stop using its session override.
Preserve the original workstation service. Restore configuration fields only
when their current values still match this deployment's expected values.
Use profile-local Memory rollback after the compatibility and dormant-process
checks. Preserve graphs, claims, block history, migration journals and recipes.
An incompatible rollback or incomplete migration leaves the target closed.
A predecessor stopped in `LAUNCHING` may be upgraded with its explicit
`--from-version` only when all processes are proven dormant, its original v2
startup receipt proves zero accepted requests and no mutation, and its graph
stamp still matches the launch snapshot. Migration preserves the unresolved
coordination record; it issues no grant and replays no request. Use the new
runtime's explicit reconcile-plan/reconcile-apply procedure before launching.
Missing, idle, changed-generation or nonzero-request receipts remain blocked.
For an interrupted `PREPARING` or `ROLLING_BACK`, use the explicit owner command:

```text
python -B -m scripts.ai.mcp memory-runtime recover-transition --profile <profile-id> --transaction <preserved-transaction-id>
```

It completes that exact journal's direction, with no new migration or request
replay. Current account, branch, policy, physical graph claim, dormant processes,
unchanged graph and coordination must be proved. Under registry, profile and graph
locks, each record must equal the approved before/after snapshot. Completion changes
only that profile's descriptor, activation, binding and registry entry, then commits
the existing journal. Other registry entries and graph bytes are preserved. Repeating
completed recovery verifies coherent records without writes; an interruption remains
closed and can be retried with the same ID. Older journals without an after snapshot
are reconstructed only from the exact verified immutable target and checked against
their preserved after-entry. Each new `ROLLING_BACK` journal records its own graph
and coordination snapshot at rollback start, allowing legitimate graph changes
since migration while rejecting changes during rollback. A legacy rollback journal
without that snapshot can use only its unchanged preserved migration snapshot;
recovery never guesses a later graph state. Management imports, including lazy
runtime imports, suppress bytecode and restore the caller's previous mode.

Unknown state, source drift, unqualified predecessor, changed coordination or graph
remain refusals. Do not edit records or restore the shared registry to bypass them.
Escalate to repository/runtime owner `@SatoryKono` and the bound account operator.
Preserve, unchanged, that profile's
`migration-v2.json`, referenced `migration-history` entries, `runtime-binding.json`,
`profile.json`, `active.json`, `recovery-v2.json`, `blocked.json`, `status.json`,
`owner-launch.json`, `work.json`, graph and ownership claims. Retain the matching
entry of `profiles.json`, referenced immutable bundles/manifests and process
identity evidence. Keep credentials private. The owner must review a dedicated
profile-local completion or cancellation against these records before writes;
restoring the entire shared registry is not a recovery procedure.

## Post-incident

Attach sanitized command results, UTC, profile/version references and source
identity to the issue. Keep mandatory unexecuted controls open and distinguish
local receipts from exact-head CI. Review the procedure when owner or transport
contracts change; retire it only with a replacement covering the same controls.

## Compliance

Never publish credentials, their hashes, raw user configuration or full graphs.
Do not bypass an automatic approval rejection or weaken workspace/account/policy
boundaries. Retain the existing technical-debt limits. Internal implementation
modules belong to the existing MCP operational entrypoint and remain classified
through the scripts lifecycle registry.
