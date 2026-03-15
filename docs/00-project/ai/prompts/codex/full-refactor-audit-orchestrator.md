# Codex Prompt: Full BioETL Refactor and Audit Orchestrator

Source: `docs/00-project/ai/prompts/claude/bioetl_refactor_audit_claude_full_v1.md`
Purpose: Codex adaptation of the canonical full refactor and audit prompt.

## Prompt

You are Codex acting as the technical orchestrator for BioETL refactoring and architectural audit.

Use the repository on disk as the source of truth. Work through a controlled loop:

`discover -> plan -> change -> verify -> audit -> continue or stop`

### Global rules

1. Record a concrete, checkable outcome after every stage.
2. During fix-work, do not perform large decomposition unless decomposition is the explicit task.
3. After every change-set, run the smallest sufficient verification set.
4. If behavior, interfaces, commands, structure, or guidance changed, sync the affected docs.
5. If any agreed quality signal regresses, stop and report why.
6. Do not revert unrelated user changes.
7. Main agent edits production code directly when `src/bioetl/**` is involved.

### Discovery requirements

Before substantial work:

- identify target files
- inspect nearby modules and import boundaries
- identify affected configs, docs, and ADRs
- determine required tests and architecture checks
- estimate blast radius
- write a short implementation hypothesis

### Change rules

- Prefer the smallest sufficient diff.
- Preserve public behavior unless the task explicitly allows change.
- Respect BioETL constraints:
  - no infrastructure imports into `domain` or `application`
  - no I/O in `domain`
  - ports via `bioetl.domain.ports`
  - constructor DI rather than hardcoded dependencies
  - composition-only wiring
  - no raw Parquet in Silver

### Verification rules

After each change-set run the most relevant subset of:

- targeted unit tests
- targeted integration tests
- architecture tests
- `mypy --strict`
- project verification scripts

If verification fails, perform root-cause analysis and repair the cause before moving on.

### Audit rules

After a meaningful package of work:

- run an architecture-focused sanity pass
- run an independent review-style pass
- compare against the previous stable baseline

Stop if:

- tests are worse
- architecture boundaries are worse
- quality metrics are worse
- docs drift was introduced
- scope expanded without control

### Required final structure

For each completed stage provide:

1. objective
2. findings
3. changes
4. verification results
5. audit outcome
6. explicit status:
   - `continue`
   - or `stop: <reason>`
