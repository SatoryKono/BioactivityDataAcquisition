# RF-06 Domain Facade Hygiene Plan

**Date:** 2026-03-20
**Status:** Proposed
**Primary rationale:** improve `domain.ports` and `PipelineContext` architectural narrative without moving runtime ports out of `domain`
**Normative constraint:** no port migration across layers

## 0. Planning Contract

RF-06 is intentionally a **clarification and guardrail task**, not a structural migration.

The project policy is already clear enough in behavior:
- ports are defined in `domain/ports/`,
- consumers must import from the `bioetl.domain.ports` facade,
- `PipelineContext.started_at` is the normative time source under ADR-014.

What is still weak is the explanatory layer around that behavior. That gap makes it too easy for future plans and reviews to misread an allowed structure as a defect.

So RF-06 must:
- clarify architecture docs,
- tighten the narrative around `PipelineContext`,
- add one cheap self-check that makes the intended policy more explicit.

RF-06 must **not**:
- move runtime ports out of `domain/ports`,
- reclassify `PipelineContext` as an architectural error,
- trigger a migration wave across application / composition / infrastructure imports.

## 1. Current Baseline

### What is already true

1. `domain/ports/` is already the sanctioned facade import surface.
   This is documented in:
   - [`docs/02-architecture/01-domain-layer.md`](../02-architecture/01-domain-layer.md)
   - [`docs/00-project/RULES.md`](../00-project/RULES.md)
   - [`docs/01-requirements/REQUIREMENTS.md`](../01-requirements/REQUIREMENTS.md)

2. Runtime-oriented ports already live in `domain/ports/` by design.
   Current domain-layer docs explicitly list runtime/resilience contracts there:
   - `RunnerFactoryPort`
   - `RunnablePort`
   - `RateLimiterPort`
   - `CircuitBreakerPort`

3. `PipelineContext` is already normative under ADR-014.
   The deterministic-write narrative is explicit in:
   - [`ADR-014-deterministic-writes.md`](../02-architecture/decisions/ADR-014-deterministic-writes.md)
   - [`RULES.md`](../00-project/RULES.md)

### What is still ambiguous

1. The domain-layer docs do not say loudly enough that `domain` is not merely “business-only models”.
   In practice, this layer also owns:
   - cross-layer contracts,
   - value semantics,
   - deterministic runtime context primitives.

2. The `PipelineContext` narrative is correct but too narrow.
   It strongly documents `started_at` as the time source, but does not sufficiently explain why logger binding and contextual run metadata still belong with it.

3. Architecture guardrails currently enforce facade import usage, but they do not directly defend the *acceptability* of runtime ports inside `domain.ports`.

## 2. RF Breakdown

### RF-06A. Clarify Domain Layer Narrative

- **Type:** doc
- **Layer:** architecture docs
- **Risk:** low
- **Goal:** make it explicit that `domain` in BioETL includes cross-layer contracts and value semantics, not just business aggregates.

**Primary file scope**
- [`docs/02-architecture/01-domain-layer.md`](../02-architecture/01-domain-layer.md)
- optional targeted wording in [`docs/00-project/RULES.md`](../00-project/RULES.md)

**Required wording outcome**
- clearly state that `domain.ports` is the approved home for runtime-oriented cross-layer contracts;
- explicitly say that this does not violate the layering rules because the contracts remain pure abstractions;
- distinguish “no infrastructure in domain” from “no runtime contracts in domain”, because those are not the same rule.

### RF-06B. Improve `PipelineContext` Narrative Without Migration

- **Type:** doc
- **Layer:** architecture docs / rules
- **Risk:** low
- **Goal:** explain `PipelineContext` as a normative deterministic runtime context, not a misplaced infrastructure object.

**Primary file scope**
- [`docs/02-architecture/01-domain-layer.md`](../02-architecture/01-domain-layer.md)
- [`docs/00-project/RULES.md`](../00-project/RULES.md)
- optionally [`docs/02-architecture/decisions/ADR-014-deterministic-writes.md`](../02-architecture/decisions/ADR-014-deterministic-writes.md) if a cross-reference note is missing

**Required wording outcome**
- `PipelineContext` remains the single source of deterministic time;
- logger/bound logger role is described as part of execution context propagation, not as evidence that the type belongs elsewhere;
- no “future migration” language is introduced unless there is real evidence.

### RF-06C. Add One Cheap Architecture Self-Check

- **Type:** test or doc-check
- **Layer:** architecture / governance
- **Risk:** low
- **Goal:** make future false refactor plans less likely.

**Preferred shape**
- add a small architecture test or extension to an existing domain public API test that explicitly asserts the documented acceptability of facade-level runtime ports in `bioetl.domain.ports`

**Good targets**
- [`tests/architecture/test_domain_public_api.py`](../../tests/architecture/test_domain_public_api.py)
- [`tests/architecture/test_forbidden_imports.py`](../../tests/architecture/test_forbidden_imports.py)

**What this check should do**
- verify that selected runtime ports remain exported from the `domain.ports` facade;
- optionally verify that the docs mention facade import policy in the expected architecture file;
- avoid over-engineering or coupling the test to too many doc lines.

## 3. Execution Order

### Slice 0. Narrative Baseline

- read active wording in `01-domain-layer.md`, `RULES.md`, and ADR-014;
- identify where the current text implies the right behavior but does not state it strongly enough.

### Slice 1. RF-06A

- tighten domain-layer wording around `domain.ports`;
- add one explicit sentence that runtime ports remain in `domain.ports` by project policy.

### Slice 2. RF-06B

- clarify `PipelineContext` narrative and `bind_logger()` / contextual logging role;
- keep wording aligned with ADR-014 and existing deterministic-time rules.

### Slice 3. RF-06C

- add one cheap architecture self-check;
- prefer extending an existing test file over inventing a new large guard suite.

## 4. Verification Gates

### Docs / architecture sync

- `./.venv/Scripts/python.exe -m pytest -q tests/architecture/test_documentation_sync.py`
- `./.venv/Scripts/python.exe -m pytest -q tests/architecture/test_domain_public_api.py`
- `./.venv/Scripts/python.exe -m pytest -q tests/architecture/test_forbidden_imports.py`

### Optional targeted checks depending on touched files

- if `RULES.md` wording changes materially: any rules/docs drift checks already used in normal docs waves
- if ADR wording changes: architecture docs syntax / link checks as needed

## 5. Main Risks And Controls

### Risk 1. Accidentally reframing domain as “anything goes”

**Control**
- make the wording precise:
  - domain still forbids I/O and infrastructure dependencies;
  - cross-layer contracts are allowed because they are pure abstractions.

### Risk 2. Starting an unnecessary port migration debate

**Control**
- explicitly state in the plan and in the docs that RF-06 performs no port relocation;
- avoid “temporary” language unless there is an accepted ADR saying otherwise.

### Risk 3. Adding a noisy or brittle architecture test

**Control**
- prefer one small explicit check over a generalized policy engine;
- anchor the test to stable public exports or one stable doc file, not to fragile prose details.

## 6. Definition Of Done

RF-06 is complete only if:

1. Active architecture docs explicitly describe `domain.ports` as the sanctioned facade for cross-layer contracts, including runtime-oriented ports.
2. `PipelineContext` remains in its normative deterministic role and no longer reads like an architectural smell.
3. No port migration across layers is performed.
4. At least one cheap self-check is added or extended so the intended policy is harder to misread in future reviews.
5. The touched docs/tests pass their targeted verification gates.

## 7. Recommended Immediate Start

Start with **RF-06A + RF-06B** in one small docs slice, then add **RF-06C** as a minimal follow-up guard.

Why:
- the main problem is interpretive ambiguity, not code structure;
- the docs need to become unambiguous before a guard test can fairly assert the intended policy;
- this keeps RF-06 small, cheap, and clearly separated from any migration work.
