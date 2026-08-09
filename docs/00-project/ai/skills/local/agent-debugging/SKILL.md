> Mirror status: This file is a published/internal mirror under `docs/00-project/ai/**`. It is not a canonical runtime surface.
> Canonical runtime source: `.codex/skills/agent-debugging/SKILL.md`
> Governance: AI_RUNTIME_MIRROR_OWNERSHIP.md
> Edit the runtime source first, then refresh this mirror.
______________________________________________________________________

---
name: "agent-debugging"
description: "Diagnose a concrete AI-agent trajectory with BioETL's safe optional AgentDebugX adapter, and optionally collect ProofAgent advisory evidence. Use only when a reproducible trajectory or bounded change scope exists."
---

# Agent Debugging

## Source Of Truth

- Normative index: `../../../../NORMATIVE_SOURCES.md`
- Root runtime contract: `../../../../../../AGENTS.md`
- Project rules: `../../../../RULES.md`
- Requirements: `../../../../../01-requirements/REQUIREMENTS.md`
- Accepted ADRs in `../../../../../02-architecture/decisions/`
- Memory policy: `../../../agents/guides/MEMORY_USAGE.md`
- Post-change validation: `../../../agents/policy/POST_CHANGE_VALIDATION.md`

- Safe adapter: `../../../scripts/ai/agent_tools/README.md`
- Shared contract: [references/advisory-contract.md](references/advisory-contract.md)

## Trigger Scope

Use this skill when an AI-agent trajectory, tool-routing failure, repeated agent
error, or bounded change surface needs deterministic diagnostic evidence.

Do not trigger it for ordinary Python exceptions, failing product tests, or
general code review when no agent trajectory exists; use `py-debug-bot`,
`py-test-bot`, or the normal review workflow instead.

## Workflow

1. Read the root contract and memory context before execution.
1. Confirm availability with `python -m scripts.ai.agent_tools doctor`.
1. Place the reviewed input under `reports/ai/agent-tools/inputs/` or use a
   tracked fixture under `tests/fixtures/agent-tools/`.
1. Run deterministic diagnosis:

   ```bash
   python -m scripts.ai.agent_tools debug \
     --task-id <task-id> \
     --trajectory reports/ai/agent-tools/inputs/<trajectory>.json \
     --timeout 90
   ```

1. If advisory change-screening is useful, run ProofAgent with a normalized
   events file, or use `--from-git` with an explicit `--scope`.
1. Interpret the output as supporting evidence only. Reproduce the finding with
   repository-native tests or checks before proposing a lifecycle decision.

## Privacy And Safety

- The adapter strips secret-bearing environment variables, disables uploads and
  LLM assessment, and confines outputs below `reports/ai/agent-tools/`.
- Never pass `.env`, credentials, unrestricted transcripts, or symlinks.
- Keep the default timeout; raise it only for a documented bounded reason.
- Do not invoke vendor executables directly from this skill.

## Unavailable Or Failed Tool

`UNAVAILABLE`, timeout, malformed output, and vendor failure are advisory
conditions. Continue with manual trajectory inspection plus `py-debug-bot` and
repository-native checks. Do not install a package unless the task authorizes
the opt-in setup command.

## Lifecycle Boundary

AgentDebugX diagnoses; ProofAgent screens. Neither result advances a BioETL
lifecycle state, satisfies required Proof-or-Stop evidence, overrides a core
test, or closes an issue by itself.

## Validation

Record the adapter exit code, `summary.json` path, pinned tool version, and the
native check used to confirm or reject the vendor finding.
