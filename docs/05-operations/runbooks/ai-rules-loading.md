______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-11-11'

______________________________________________________________________

# AI rule loading evidence

## Trigger

Use after a runtime upgrade, changing an entrypoint, or diagnosing ignored rules.
The repository precedence remains in [AGENTS.md](../../../AGENTS.md).

## Impact

An existing file, a valid descriptor, and a passing mirror check do not establish
which client loaded it. Native discovery, prompt inclusion, and obeying an
instruction are different observations.

## Preconditions

Use an existing complete checkout and the established platform Python. Complete
the version/capability baseline from issue #13034 before enabling an adapter.
Do not install runtimes, alter trust settings, or activate services implicitly.

## Procedure

### Static inventory

```text
python scripts/ai/codex/doctor.py rules --no-write --json
```

On Windows use the established `.venv-win/Scripts/python.exe`; WSL needs its own
development interpreter. `--repo-root` selects the inspected checkout explicitly,
including when launched outside its root. This mode reads bounded declared
sources, emits relative paths/digests, and starts no processes or network probes.
It never reads `.env`, emits configuration values, or refreshes overlays.

Exit 2 / NOT_PROVEN is always intentional even when every candidate exists.
Native observations are separate evidence, not stored claims promoted by
inventory. The report
does not inspect global layers, choose a binary, or assert a client used a file.
`static` remains a separate structural contract check; `all` does not implicitly
start loader probes. Invalid, external, or oversized sources are reported without
raw parser errors. No new native rules directory is deployed by this procedure.

### Explicit native observations

Inspect the selected direct binary's help/schema before using a command. Bind an
observation to binary digest/version, platform, cwd, source digests, method and
result. A manifest or cached latest-version value is insufficient. Recheck each
Windows shell, WSL distribution, installation and IDE separately.

For the observed Codex build, `debug prompt-input` renders the input without a
model turn. Capture JSON in memory, compare complete normalized source bodies,
and retain only booleans/digests. Never save or publish the raw prompt or merged
configuration. A source name mentioned in another document is not its body.

The same build supports `app-server generate-json-schema --out <diagnostic-dir>`.
This explicitly writes schemas, unlike static inventory. Its stdio metadata
protocol supports `initialize`, `config/read` and `skills/list`. An explicitly
started, bounded metadata-only process can confirm effective project layers and
enabled skill paths without creating a thread or model turn; close that process
after inspection. Retain no raw configuration values. Do not assume these
experimental methods exist on another version or enable a daemon/MCP plane.
Compare the selected schema with the [App Server contract](https://developers.openai.com/codex/app-server/).

For Devin, inspect `rules list`, `rules show AGENTS` and `skills list --json`.
Compare the resolved root body and restrict exported metadata to project paths.
These commands establish resolver/discovery results, not child permissions or
model obedience. `make devin-check` materializes a local MCP overlay and is not
a no-write substitute. A launcher may update even on informational invocations;
do not execute an unresolved shim as part of static discovery.

### Source connections

| Surface | Connection | What remains to prove |
| --- | --- | --- |
| Root `AGENTS.md` | Native candidate; inspect overrides and truncation | Actual prompt inclusion on the selected client |
| Matching runtime map | Root Runtime Bootstrap requires reading it | The agent actually read it before actions |
| Profile Markdown | Selected responsibility guide | Native registration, profile selection, and body inclusion |
| Codex TOML descriptor | Declared route to profile/skill | Selected client's native role registration |
| Skill metadata | Native discovery when supported | Task selection and injection of the skill body |
| Junie guidelines | Governed mirror and legacy native candidate | Effective IDE path or version-qualified CLI selection |
| OpenCode | Subordinate, disabled automation | Any activation requires its separate existing gate |

### Observed Windows baseline, 2026-11-11

These are bounded observations, not minimum-version guarantees. The commands
ran on the dedicated rules worktree; neither another agent nor a model turn was
started. Local detailed evidence is not committed with user/global context.

| Runtime | Observed method and result | Deliberately unqualified |
| --- | --- | --- |
| Codex `0.167.0-alpha.3.2` | Direct binary; `config/read` reported the project layer; `skills/list` returned 14 enabled repo skills under `.codex/skills`; `debug prompt-input` contained the complete root body | Runtime/profile/skill bodies were absent from that initial rendering; task-driven reading and model execution NOT_PROVEN |
| Devin `3000.11.3 (9c803229faa4)` | Direct binary; `rules show AGENTS` resolved the complete current root body; project skills were returned by `skills list --json` | Session prompt injection, native profile registration and permission enforcement NOT_PROVEN |
| Junie | PATH shim exists, but its default current-version pointer was absent and no version override was set | Default runnable CLI and IDE configuration NOT_PROVEN; do not claim Junie is absent from every surface |
| OpenCode | Remains subordinate; npm manifest is not a binary attestation | Native loading/execution NOT_PROVEN; disabled workflows/write paths not activated |

The Codex binary digest was
`4f91ae86895ff124760d70ed1630e2354ca874765c9bb61ae524b600327efc17`.
Repeat observations after any binary or source change. No WSL or model-execution
acceptance is inferred from this Windows baseline.

Controlled prompt-rendering checks with root digest
`7035783ba203b62e8ea6d51564d71f82c6caf8ffd15c7e40cca153c429691dd2`
included the complete root body from the project root and a nested fixture.
In that fixture, the override marker appeared and its same-directory normal
marker did not. Outside this repository the complete root body was absent.
Only booleans/digests were retained; no raw prompt or model execution was used.

### Repeat control after context-tier integration, 2026-11-12

The same attested Codex binary rendered the complete updated root body with
source digest `50ef55e8539fc1c6127cb07404ae36d0e2037b6d9aa8735f28310fa04d36e8f2`
from the root and nested fixture. Outside the checkout that body was absent.
Only comparison booleans and digests were retained; no model turn ran.

This closes the root prompt-render observation for that source/build only.
Untrusted-session tool permissions, arbitrary user-rule precedence, Junie IDE
configuration, WSL execution and model obedience remain NOT_PROVEN. Do not
activate an adapter or treat a profile as isolated on the basis of this probe.
For unavailable clients, the accepted diagnostic result is explicitly negative;
instruction-driven parent reading preserves the contract without claiming native
registration. Future native activation still requires a separate qualified
capability baseline and a bounded acceptance for the affected installation.

### Vendor contracts and repository ownership

Current [Codex instruction discovery](https://developers.openai.com/codex/guides/agents-md/)
uses global/project chains, override candidates and a bounded document budget.
The [skills documentation](https://developers.openai.com/codex/skills/) describes
`.agents/skills` discovery. The observed build also returned this repository's
canonical `.codex/skills` paths. Preserve that source; do not deploy duplicates
or generalize compatibility from a documentation page alone.

Current [Junie guideline discovery](https://junie.jetbrains.com/docs/guidelines-and-memory.html)
prefers `.junie/AGENTS.md`, then root `AGENTS.md` with optional companion rules,
then legacy guidelines. [Junie skills](https://junie.jetbrains.com/docs/agent-skills.html)
are task-specific. [Custom subagent documentation](https://junie.jetbrains.com/docs/junie-cli-subagents.html)
requires metadata. The mirrored py-* guides contain no vendor frontmatter;
their native registration remains unqualified. Keep these mandatory mirrors and
use instruction-driven parent routing until a supported adapter is tested.

[Devin rules](https://docs.devin.ai/cli/extensibility/rules) and
[skills](https://docs.devin.ai/cli/extensibility/skills/overview) describe separate
always-on and task-selected mechanisms. Check effective
[configuration layers](https://docs.devin.ai/cli/reference/configuration/global-vs-local)
rather than treating a project file as the complete session configuration.
Repository precedence is an instruction contract, not an invented native
priority setting that overrides a vendor's loader.

## Verification

Test present/missing/invalid/oversized sources and the no-process/no-write static
mode. Validate bootstrap links, mandatory runtime parity and docs inventories.
For native observations verify complete content, selected source paths, binary
identity and cwd; distinguish discovery, prompt rendering, execution and refusal.
Never turn an unavailable client, skipped probe or unknown version into PASS.

## Rollback

Remove the inventory invocation or revert bootstrap changes with their mirrors.
No adapter is enabled by inventory, and no protected rule should be removed.
Retain existing entrypoints and disclose the evidence gap after rollback.

## Compliance

Keep `.env`, worktree location, debt budgets, full Git tree, runtime parity and
post-change rules. Do not use prompt captures to store secrets, conversations or
unrelated global skills. Native lookup is not an OS boundary for subprocesses.

## Post-incident

Record the affected version/source identities and repeat the bounded probe after
repair. Report local checks, current head and remote CI separately.
