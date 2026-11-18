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
Unchanged output does not replace the file. Back up only changed fields in
owner-private storage and compare current values before restoring them.

### Session boundaries

The existing operational CLI exposes `python -B -m scripts.ai.mcp codex-session
--executable <qualified-app-owned-codex.exe> --sha256 <qualified-digest>`.
Run from the actual intended checkout. `--check` validates bindings and prepares
child-only credential delivery without spawning Codex or sending a request.
The launcher requires a separately qualified native executable and does not
claim that a currently running ACP/editor client has reloaded its configuration.

The launcher compiles explicit Memory/AST and optional Markdownify bindings into
supported per-invocation `--config` transport tables. It preserves existing tool
approval policies. This path leaves the global user TOML unchanged; subsequent
generator synchronization cannot erase these invocation-scoped overrides.
The Markdownify binding must match the exact physical workspace and Git common
directory. Do not substitute an arbitrary stdio command or a mutable checkout
path for the reviewed installed selector.

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
recovery rules. No uncertain request is replayed.

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

Only installed, version-compatible format dependencies are qualified and copied
into a checked converter snapshot. Plugins and unavailable formats stay disabled.
Qualification includes an actual representative conversion, path-swap controls,
allow-deny-allow and reconnect tests. Retain originals and diagnostic evidence.

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
