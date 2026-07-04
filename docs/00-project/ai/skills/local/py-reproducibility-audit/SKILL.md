---
name: py-reproducibility-audit
description: Audit BioETL pipeline reproducibility, determinism, idempotency, checkpoint safety, lineage completeness, and replay readiness against current code, configs, docs, and control-plane artifacts, then turn confirmed findings into actionable BioETL GitHub issues. Use when asked to assess exact replay/debug readiness, audit run manifests or execution fingerprints, verify checkpoint/run identity consistency, or prepare issue backlogs from a completed reproducibility audit.
---

> Mirror status: This file is a published/internal mirror under `docs/00-project/ai/**`. It is not a canonical runtime surface.
> Canonical runtime source:
> - Codex: `.codex/skills/py-reproducibility-audit/SKILL.md`
> Governance: [AI Runtime Mirror Ownership](../../../agents/policy/AI_RUNTIME_MIRROR_OWNERSHIP.md), [Memory Usage](../../../agents/guides/MEMORY_USAGE.md), [Post-Change Validation](../../../agents/policy/POST_CHANGE_VALIDATION.md).
> Edit the runtime source first, then refresh this mirror.

# py-reproducibility-audit

## Objective

Run a source-first BioETL reproducibility audit and, only after confirmed
findings exist, prepare root-cause GitHub issues with file-level implementation
plans.

## Required Inputs

- `target_type`: `pipeline` | `workflow`
  Default: `pipeline`
- `target_name`: canonical target name
  Default: `chembl_assay`
- `execution_mode`: `fresh_run` | `existing_run_ids`
  Default: `fresh_run`
- `run_count`: number of independent audit runs to compare
  Default: `2`
- `limit`: bounded-run limit when `execution_mode=fresh_run`
  Default: `1000`

When the user does not override these values, audit the `chembl_assay`
pipeline via two fresh bounded runs.

## Source Of Truth
- Normative index: `../../../../NORMATIVE_SOURCES.md`
- Root runtime contract: `../../../../../../AGENTS.md`
- Project rules: `../../../../RULES.md`
- Requirements: `../../../../../01-requirements/REQUIREMENTS.md`
- Accepted ADRs: `../../../../../02-architecture/decisions`
- Runtime map: `../../agents/CODEX-RUNTIME.md`
- Memory policy: `../../../docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- Shared project memory: `../../../docs/00-project/ai/memory/agent-memory.md`
- Daily loop: `../../../src/memory/DAILY_WORKFLOW.md`

## Workflow

1. Start with the canonical memory loop from
   `../../../src/memory/DAILY_WORKFLOW.md` and run
   `python -m memory.tooling.workflow pre-task ...`.
1. Read `MEMORY_USAGE.md`, `agent-memory.md`, and the matching
   `memory-py-*.md` sheet when a role-specific memory page is relevant.
1. Read [references/reproducibility-audit.md](references/reproducibility-audit.md)
   before making any architectural claims about reproducibility.
1. Resolve the audit target before any run:
   - if `target_type=pipeline`, audit the named pipeline directly
   - if `target_type=workflow`, audit the named workflow and the pipeline steps
     it actually executes
   - if the target is not provided, use the defaults from `Required Inputs`
   - if the canonical command for the target is ambiguous, stop and report the
     ambiguity instead of guessing
1. Resolve the execution lane before collecting evidence:
   - `fresh_run`: perform `run_count` sequential bounded executions using the
     canonical CLI for the resolved target
   - `existing_run_ids`: audit existing manifests / ledgers / sidecars / output
     artifacts without starting a new run
1. Audit only against confirmed repository evidence:
   - code
   - configs
   - tests
   - runtime/control-plane artifacts
   - accepted docs/ADRs
1. Treat reproducibility as distinct from generic observability:
   - keep determinism, idempotency, replay, resume, rebuild, and incremental
     semantics separate
   - evaluate `run_id`, `manifest_id`, `execution_fingerprint`,
     `config_hash`, `effective_config_hash`, `git_commit`, `contract_ref`,
     `contract_version`, `content_hash`, checkpoint identity, and lineage
     metadata as current architectural baseline, not optional ideas
1. For `workflow` targets, report both:
   - workflow-level reproducibility findings
   - per-pipeline findings for every executed pipeline step
1. For `pipeline` targets, prefer the direct pipeline CLI surface when the
   project exposes one; use a workflow wrapper only when the pipeline is
   workflow-managed by design and no direct supported CLI exists.
1. Produce the audit in the mandatory section order defined in
   `references/reproducibility-audit.md`.
1. Create issues only if the audit produced confirmed problems with concrete
   evidence. Then read
   [references/github-issue-design.md](references/github-issue-design.md) and
   generate one issue per root cause.
1. Keep every issue architecture-safe:
   - no infrastructure imports into domain
   - no I/O in domain
   - no weakened Gold strict validation
   - no dependency-direction violations
   - no cyclic dependencies
1. Finish with `python -m memory.tooling.workflow post-task ...` and promote
   only durable lessons or decisions.

## References

- `references/reproducibility-audit.md`
  Read when running the audit itself. It contains the mandatory audit scope,
  scoring, section order, critical-defect definition, and final key question.
- `references/github-issue-design.md`
  Read when converting confirmed findings into GitHub issues. It contains the
  strict issue template, decomposition rules, and file-level planning
  requirements.
