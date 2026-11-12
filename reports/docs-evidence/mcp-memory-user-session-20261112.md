# Scoped memory acceptance: issue 13045

Observation date: 2026-11-12. This dated report qualifies memory in the current
ordinary local Codex task. It does not qualify a fresh Codex session or every MCP
in issue 13047. It supersedes only the memory-unavailable observation in
[the earlier route snapshot](../../docs/reports/evidence/mcp-route-snapshot-20261111.md); historical evidence
remains intact.

## Publication boundary

Only comparison outcomes are published. Machine-local paths, task identifiers,
profile/graph identifiers, route fingerprints, process IDs and creation-time
identifiers remain in the local non-published evidence. Graph content, credentials,
Windows account identifiers and private comparison digests are not included.
Before/after identity checks used exact creation identifiers without floating-point
truncation. This public summary is not an independent replay of private controls.

## Caller and route evidence

The app's own metadata identified the actual calling task as an ordinary local
Codex task in the intended physical BioETL checkout on branch main. Its positive
tool calls used that task's MCP interface, with no isolated Codex home, diagnostic
model task or SDK substitute. The private receipt retains the dated source context.

Native config/read selected the ordinary user's memory declaration, its scoped
adapter and the registered main graph. One memory declaration supplied the
command, arguments and limits; no memory override or disabled reason was present.
The portable project config supplied no memory server declaration.

The real doctor routes command used the same native resolver. Its complete memory
selection projection matched the ordinary call's selected route before and after.
The optional authorization-reference field was null; the registered account-bound
profile was verified separately, without inventing an authorization value.

The routes-only doctor intentionally does not claim tool/backend readiness.
Independent protected registration loading, authenticated health, live owner,
gateway/backend process identities and a known nonempty graph page established
the backend and scope used here. The selected profile, physical workspace,
source context, route choice and runtime generation/process identities matched
before and after. Equality of fingerprints alone was not counted as a pass.

## Initial failed request and explicit recovery

The first ordinary bounded read failed with HTTP 404, `No valid session`. The
completed-call event recorded a failed Streamable HTTP request; it did not prove
a missing or corrupt graph. That failure remains in the private original receipt.

The already installed adapter invalidates its protocol session on 404 and opens
a new session at the next explicit call on the same approved endpoint. It does
not replay failed tool work or start a fallback backend. After inspecting that
path and the definite failure outcome, one new explicit bounded call verified
recovery. No adapter source, profile, configuration or shared owner was changed.

The sandbox shell account and ordinary host account were kept distinct. A sandbox
native-config helper initially exited before initialize because its home was not
available; authorized metadata and the negative child used the host account.
HOME and CODEX_HOME were not redirected, and helper failure was not treated as
graph failure.

## Allow, policy denial, allow

Both positive calls requested `read_graph(offset=0, limit=1)`. The response and
local comparison limits were 65,536 bytes; each actual response was 619 bytes.
The control required a known nonempty entity page and a matching relation page,
at most one entry each. Processing was RAM-only; payloads were not saved in logs.
Native route limits were retained: startup 90 seconds, tool call 120 seconds.

| Phase | UTC observation | Result | Evidence |
| --- | --- | --- | --- |
| Explicit recovery / allow-before | 14:24:30 | PASS | Ordinary Codex MCP read; known graph page matched |
| Same-profile foreign workspace | 14:26:13 | DENIED_AS_EXPECTED | Exact workspace-policy rejection, exit 1, empty stdout |
| Allow-after | 14:26:37 | PASS | Ordinary Codex MCP read; the same known page matched |
| After-capture | 14:26:54 | PASS | Route, source context, runtime identities and graph comparison unchanged |

The allowed reads were at 17:24 and 17:26 Baghdad time (UTC+3). The negative child
used the same selected adapter/profile and host account from an existing foreign
workspace. Account/profile registration was independently valid, the owner stayed
ready, and allowed reads passed before and after. Timeout, server-down and auth
failure were not counted as isolation. No foreign root or graph was registered,
initialized or granted access. The graph's last write preceded the first capture;
the private before/after byte comparison across denial and final read matched.

## Write policy and service effects

The observed catalog contains `read_graph`, `create_entities` and `delete_entities`.
Only the bounded reads were called. Diagnostic call discipline was read-only;
the registered server policy is read-write, not technically read-only. No real
write test was performed or needed to distinguish these facts.

Service effects were local connections, native metadata reads, normal adapter
launch-gate/log activity and protocol-session recovery on an approved endpoint.
No memory write, new root, graph initialization, new service, shared-owner restart,
env-file edit, credential change or authorization change occurred. The required
pre-task remained DEGRADED in read-only mode with refresh/session notes disabled;
claims were checked against source and actual calls.

## Acceptance limit

This dated receipt qualifies only memory in the current ordinary task. Native
configuration membership, tool catalog exposure, current-task recovery and this
memory evidence do not establish fresh ordinary-session acceptance of the other
mandatory servers in issue 13047. Its untested criteria remain untested.
