# GitHub Issue Design Reference

## When To Use

Use this only after a completed reproducibility audit produced confirmed
findings backed by repository evidence.

## Working Mode

1. Use only confirmed problems from the audit.
2. Do not add new hypotheses.
3. Exclude:
   - duplicates
   - already fixed problems
   - vague umbrella refactors
   - architecture-breaking proposals
4. Create exactly one root cause per issue.
5. Decompose large findings into multiple issues.

## Output Order

### Step 1 — Plan

Start with a table:

| # | Title | Area | Priority | Size | Root cause | Key files |

### Step 2 — Issues

Then provide the full issue set using the structure below.

## Required Structure For Each Issue

### 1. Title

Format:

`[area] Imperative description`

### 2. Problem

Facts only. No solution language.

### 3. Evidence

Mandatory file-level evidence, for example:

- `path/to/file.py::ClassName`
- `configs/...yaml`
- `tests/...`

If there is no concrete evidence, do not create the issue.

### 4. Root Cause

State the architectural violation, design flaw, or drift briefly.

### 5. Architectural Impact

Assess only relevant impact on:

- layer boundaries
- dependency direction
- determinism / idempotency
- DQ / validation
- observability
- reproducibility

### 6. Required Outcome

Describe the post-fix state as explicit truths about the system.

### 7. File-level Implementation Plan

#### Changes

List concrete file edits:

- `src/.../file.py`
  - what to remove / move / rename / rewrite
- `configs/...`
  - what fields to add / change / remove
- `tests/...`
  - what tests to add / update / delete

#### Refactoring actions

Describe any movement of logic between layers, deduplication, or legacy removal.

#### Contracts impact

State impact on:

- ports
- schemas
- DQ rules
- config contracts

#### Migration

If needed, describe:

- backfill
- contract version bump
- data rewrite

### 8. Constraints

State explicitly that the fix must not:

- import infrastructure into domain
- add I/O into domain
- violate dependency direction
- mutate Quarantine payload
- weaken Gold strict validation
- create dependency cycles

### 9. Acceptance Criteria

Use verifiable conditions:

- unit / integration / architecture tests pass
- no RULES.md violations
- no new dependency cycles
- determinism preserved
- idempotency preserved

### 10. Priority

Use `P0` / `P1` / `P2` / `P3` with justification.

### 11. Size

Use `S` / `M` / `L` / `XL` with justification.

### 12. Labels

Choose only from:

- `architecture`
- `dq`
- `observability`
- `technical-debt`
- `refactor`
- `testing`
- `configs`
- `governance`

### 13. Dependencies

List issue dependencies when they exist.

## Guardrails

- No generic recommendations.
- No “could improve” language.
- Only actionable engineering work.
- Every issue must be implementable without guesswork.
- If the natural fix would violate BioETL architecture, say so and propose the
  architecture-safe alternative.
