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
