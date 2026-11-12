______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-11-11'

______________________________________________________________________

# AI hook compatibility and local evidence

## Trigger

Use before deploying hooks or when runtime selection changes.

## Impact

Unqualified hooks may silently fail to protect operations.

## Preconditions

Use an existing complete checkout and the established local Python interpreter.
No credentials or running services are required.

## Procedure

Run the read-only inventory from the repository root:

```text
python scripts/ai/codex/doctor.py hooks --no-write --json
```

On Windows select the established `.venv-win/Scripts/python.exe`. In WSL
select the established WSL development interpreter. Run discovery in each
distribution and shell environment separately; Windows PATH is not WSL PATH.
The inventory executes bounded Git metadata queries only. It never evaluates
launcher scripts, runs hooks, starts an agent, installs packages, or contacts
a service. Exit code 2 means installed capability remains NOT_PROVEN, not PASS.
Its JSON separates present files, discoverable Git hooks, configured events,
and execution evidence. It reports paths and digests, not command/config values.
Inline and standalone event definitions retain their source paths. Alternate
OpenCode project configurations are fingerprinted too. JSONC is reported as
an unsupported parse format with incomplete discovery, never as proof that
plugins are absent. The diagnostic does not install a JSONC parser.

## Evidence captured on 2026-11-11

These are observations, not portable version requirements. Recheck before
deployment; package manifests and cached latest-version files are insufficient.

| Runtime | Windows observation | Ubuntu-24.04 non-login PATH | Native hook deployment |
| --- | --- | --- | --- |
| Codex | Direct app binary reported `0.167.0-alpha.3.2`; PATH shim selects app binary dynamically | command not found | NOT_PROVEN for this exact build |
| Junie | PATH shim exists; default current-version pointer absent | command not found | NOT_PROVEN; no runnable default established |
| Devin | Direct binary reported `3000.11.3 (9c803229faa4)` | command not found | NOT_PROVEN for this exact build |
| OpenCode | npm manifest reports `1.18.1`; selected binary version not attested | command not found | Disabled subordinate surface |

Explicit operator `--version` observations above are separate from static
inventory. The diagnostic deliberately does not run these commands: launchers
can update installations even during seemingly informational invocations.

## Vendor contracts versus installed support

The following official documentation was inspected on 2026-11-11. It describes
current vendor contracts, not minimum supported versions or local execution.
No project adapter may be enabled from these links alone.

| Runtime | Documented mechanism | Discovery / important limit | Version qualification |
| --- | --- | --- | --- |
| Codex | Lifecycle command hooks | Trusted project `.codex/hooks.json`; managed requirements and other layers can restrict hooks | Exact installed build needs schema and isolated execution evidence |
| Junie | Lifecycle command hooks including `PreToolUse` and `Stop` | EAP; project config requires explicit `--config-location`; synchronous `blockOnError` is needed to promote failures to blocks | No local version qualified |
| Devin | Lifecycle hooks including `PreToolUse` and `Stop` | `.devin/hooks.v1.json`; exit 2 blocks, other nonzero exits log errors without blocking | Exact installed build must be qualified |
| OpenCode | Plugin hooks | Major-version-specific API; current documentation is not evidence for installed 1.x | No adapter qualified; write paths remain disabled |

Sources:

- [Codex hooks](https://developers.openai.com/codex/hooks)
- [Junie CLI hooks](https://junie.jetbrains.com/docs/junie-cli-hooks.html)
- [Devin hooks](https://docs.devin.ai/cli/extensibility/hooks/overview)
- [OpenCode plugins](https://opencode.ai/docs/plugins/)

Qualification must bind binary digest/version, platform, config fingerprint,
vendor contract, trigger, refusal semantics, timeout and isolated fixture result.
Do not infer compatibility across versions or claim a minimum version without
vendor evidence. Missing dependencies, unknown versions and skipped execution
are not success. Runtime adapters are separate from Git hooks, command wrappers
and CI; none of those layers proves another layer ran.

## Shared command-wrapper guards

These are internal structured operations, not vendor lifecycle event names.
Run with `python -B -m scripts.engineering.repo guard-operation`, passing one
JSON object on stdin with `operation`, `path`, and (for move/rename) `destination`.
Supported operations are read, write, create, delete, move, rename and
worktree_create. Unknown operations, malformed input and self-granted approval
fields return ERROR. Exit codes are PASS=0, FAIL=1, ERROR=2, SKIP=3; callers
must block mutations for every result other than PASS. The guard never executes
the requested operation and accepts at most 64 KiB of input.

Environment mutations, including `.env.example`, are denied automatically.
Per-task user authorization must be established by the host outside the request;
there is no approval flag in the payload. Reads remain permitted. Lexical and
resolved path components are checked without printing values or raw errors.
Existing-directory mutations require host review because their descendants may
include environment files. The guard does not recursively scan an unbounded
tree. This does not sandbox arbitrary commands or their child processes.

Worktree admission fixes the root to `D:/github` on Windows and the corresponding
WSL mount of that same Windows directory. A task must resolve directly below
`BioactivityDataAcquisition-worktrees` within that root.
The in-process permit records ancestor identities and must be revalidated
immediately before the existing approved creation helper runs. Junction escapes
and replaced ancestors are rejected; unrelated sibling work is permitted.
The final check cannot eliminate a hostile filesystem race after validation.
Creation still requires the approved helper; this core creates no checkout.
The tracked deployment/bootstrap work remains owned by
[worktree guardrail issue #13032](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/13032).
Its host adapter must call `prepare_worktree`, retain the permit in process,
then call `revalidate_worktree` immediately before the approved creation helper.
This change neither replaces nor installs machine-local worktree hooks.

Use `python -B -m scripts.engineering.repo guard-budgets --base origin/main`
to compare staged Git objects against a trusted base, or supply `--tip SHA`
for committed evidence. The registry comes from the base, so staged files cannot
exclude themselves. Initial deployment requires the registry to exist in the
trusted base; absence returns ERROR. Git calls have a five-second timeout and
policy blobs are bounded to 2 MiB. Missing Git/YAML dependencies, malformed
schemas and unknown budget candidates fail closed without changing files.

Ceilings and exemption counts may decrease; floors may increase. New exemption
records, extended expiry dates, unknown structural policy changes and registry
changes require review and fail this automatic check. Telemetry observations
are separate from protected coverage/freshness limits. Textual architecture
criteria remain owned by architecture tests. This heuristic registry is not a
complete semantic proof of every policy: independent CI must use a trusted
baseline, check registry coverage and retain existing specialized budget and
architecture checks. Local hooks can be bypassed and cannot enforce remote
merge policy. No adapter or hook is installed by these commands.

Callers must apply their own bounded invocation timeout (recommended ten seconds
for operations and sixty seconds for budget comparison) and treat timeout,
missing interpreter and invalid output as ERROR. Removing a new invocation rolls
back integration; retain the existing guards and the unchanged debt limits.

## Verification

Check that the JSON identifies the current platform, effective Git directory,
and unknown capabilities explicitly. Run the unit fixtures for hook inventory.
An installed-version claim requires separate binary-bound evidence.

## Rollback

Inventory is observational and creates no deployment to undo. Remove its call
to roll back diagnostics; retain existing guards. Do not print `.env` contents,
tokens or arbitrary parser errors. A file digest proves identity, not safety.
Native hooks are not an OS boundary around child processes. Git hooks remain
bypassable locally and require independent CI. OpenCode must remain subordinate
and Codex, Junie and Devin retain their equal-peer runtime ownership.

## Compliance

Preserve root AGENTS.md guardrails. No `.env` mutation, budget increase,
runtime activation or network request is part of this diagnostic.

## Post-incident

Record the affected binary/config digests and missing evidence without secrets.
Repeat platform-specific qualification before re-enabling an adapter.
