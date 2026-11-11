# Effective MCP route audit: issue 13042

Observation date: 2026-11-11. This is a diagnostic snapshot, not continuous
monitoring or final acceptance of the remediation wave.

## Repository and session boundary

The ordinary active task session identifies its workspace as
`D:/github/BioactivityDataAcquisition`. The physical checkout is on
`docs/12583-main-integrity-final-report`, at
`7c067a9615722806847c506efb168b05980ab3f6`, with unrelated local modifications.
It is not currently checked out on main. The independently observed origin/main
was `4bf58bab1b14eb97273257015c7566d416f46f55`.

The sandbox shell account is CodexSandboxOffline; separately authorized host
metadata reads ran as Fedor. These identities must not be conflated.
With an explicit workdir, both login-default and no-profile shell launches
reported the BioETL directory for PowerShell PWD and process current directory.
The earlier shell-directory observation does not establish a PowerShell-profile
defect; it was not reproduced by this controlled comparison.

## Expected, configured and observed matrices

The expected stable set contains adr-analysis, ast-grep, code-analyzer,
context7, deja, fetch, filesystem, github, memory and ref. All ten are declared
in the ordinary user config. Other user integrations are present; no entries
were removed or enabled to force membership equality.

The project config has no mcp_servers table. The user config selects pc-agent
stdio clients for the nine local integrations and the remote ref service.
The project's generator inputs and the legacy doctor instead describe a
stable/shared localhost catalog. A generator overlay is not proof of the route
already loaded by an application session.

The ordinary-config `codex mcp list --json` command succeeded. Its configuration
enumeration is separate from the active session's observed tool exposure.
The active session exposed tools for eight stable integrations, but no memory
or ref tools were callable through its available tool interface. This does not
prove either server is universally unavailable. CLI auth_status was unsupported
for the local stdio entries and not_logged_in for ref; this alone does not prove
whether a separately provided API header can authenticate ref.

| MCP | Active-session control | Result and coverage |
| --- | --- | --- |
| adr-analysis | list_roots | PASS: BioETL and its ADR directory registered; no claim of full ADR analysis |
| ast-grep | identifier run_static, Python, scripts/ai/codex | PASS: definition in doctor.py and call site match local source |
| code-analyzer | count_code_tokens, scripts/ai/codex | PASS for this function: 10 processed files, zero errors; no paid analysis invoked |
| context7 | resolve_library_id for pytest | PASS: relevant pytest-dev source and pytest description; external results are mutable |
| fetch | example.org, bounded response | PASS: expected public example-domain content |
| filesystem | README.md, bounded head | PASS: returned header matches local file |
| github | exact repository search | PASS: SatoryKono/BioactivityDataAcquisition, repository ID 1107864078; token-scope matrix not established |
| deja | no agreed history record selected | NOT_TESTED for retrieval quality; source identifies per-export transcript history |
| memory | not exposed in active tool interface | NOT_TESTED for native graph read in this session; registration failure reproduced separately |
| ref | not exposed in active tool interface | NOT_TESTED; no direct request substituted for a native-session call |

## Reproduced differences and causes

### Memory: registered branch is not checked out

The existing memory registration binds the BioETL physical root to branch main
and policy read-write. A host-side read-only registry validation returned
`RuntimeError: Registered branch is not checked out`. The actual branch above
differs. The source in project-memory-scope.py compares the current symbolic
branch with the registered branch and fails closed.

This is an expected scope boundary, not evidence that a graph should be
recreated. No graph payload, write operation, profile replacement or branch
switch was performed. Historic native read_graph success at
2026-11-11T14:10:24.261495Z belongs to its earlier context.

Owner coordination records contain owner/gateway/backend PIDs, creation times
and generation. They are historical coordination evidence until checked against
live authenticated health and the current profile. Memory health did not pass
the branch-bound registration check; those records are not reported as current
backend readiness.

### Filesystem: narrower production policy

Reading scripts/ai/codex/doctor.py was refused through both relative and absolute
paths. Production BioetlFiles permits src, tests, docs and a small root-file
allowlist; scripts is intentionally outside that policy. README.md is allowed.
An allow README / deny scripts / allow README sequence succeeded. Source policy
and the selective successful reads explain the refusal; the generic refused
message by itself would not prove a policy denial.

No access expansion is necessary to establish filesystem's intended read
capability. Host health returned ready for its registered generation; identity
verification beyond this bounded health result is deferred to the acceptance
work rather than inferred from the tool text.

### AST control: initial pattern was not a valid positive control

Two function-shaped patterns returned provider errors with exit code 1.
A bounded identifier pattern then found the known run_static definition and
call in the expected file. The implementation wraps nonzero ast-grep exit
status as an error, including no-match results. This establishes that the
route and search operation work for the positive control; the earlier patterns
must not be used to claim a route failure.

### Doctor: different configuration authority

doctor._probe reads port/path from the project shared catalog, uses a socket and
/ping, and reports readiness_level=transport with protocol_ready/tool_ready
unset. The active user session routes through pc-agent adapters. Fixing doctor
requires the effective resolver contract and must not replace working user
routes with catalog localhost addresses just to obtain matching reports.

## Limits, effects and rollback preparation

Controls performed reads, public network requests and existing-adapter calls.
Existing services may maintain access logs or caches. No service owner was
restarted, no package was installed, no root or graph was registered, no .env
file was created or changed, and no memory mutation was requested.

The pre-task memory workflow used read-only, skip-session-note and
skip-refresh-if-missing. It reported missing RAG/timeline projections explicitly;
no temporary corpus or persistent memory note was created by that invocation.
Source RAG applicability to final MCP acceptance remains unresolved.

For future config mutations, first save precise originals with restrictive ACLs
and encrypted storage for secret-bearing files. Public receipts use sanitized
configuration projections only, never secret values or ordinary hashes of
secrets. Restore only when current fingerprints still match the expected input;
preserve later edits separately. Refuse rollback to a root now occupied by a
different branch. Stable route selection and volatile process identity must
have separate receipts.

## Disposition

This diagnostic does not authorize changing the occupied checkout, relaxing
memory branch isolation, expanding filesystem roots, or accepting a partial
matrix as full readiness. Follow-ups are resolver 13043, doctor 13044, memory
13045, retrieval applicability 13046 and normal-session acceptance 13047.
No task is closed merely because this draft exists; source and configuration
drift must be rechecked before its PR and merge.
