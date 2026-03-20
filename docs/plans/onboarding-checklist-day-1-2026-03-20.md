# Day-1 Onboarding Checklist For BioETL

*Date: 2026-03-20*
*Status: non-normative practical onboarding aid*

This checklist is a one-day, action-oriented onboarding route for a new
engineer or AI session entering BioETL. It is designed to produce real working
context in one day rather than only passive reading.

Use together with:
- `AGENTS.md`
- `docs/00-project/00-map.md`
- `docs/00-project/RULES.md`
- `docs/00-project/TOOLS.md`
- `docs/plans/project-briefing-capability-discovery-2026-03-20.md`

## Goal By End Of Day

By the end of the first day you should be able to:

- explain the five architecture layers from memory
- navigate provider, pipeline, config, and test locations without guessing
- run the canonical quality loop locally
- trace one concrete pipeline from config to transformer to storage to tests
- know which project-local skills and commands to use for your next task

## Success Criteria

The day is successful if all of the following are true:

- you know where the canonical rules live
- you know which docs are active and which are historical
- you can run at least one fast validation path locally
- you can point to the exact files to edit for a pipeline task
- you can describe the project workflow for audit, refactor, docs, and VCR work

## 0. Preflight (20-30 minutes)

Read:
- `README.md`
- `AGENTS.md`

Check local environment:

```bash
make install
make test-deps
make setup-plugins
```

If AI tooling is relevant for your session:

```bash
python -m scripts.dev setup-mcp
```

What you should verify:
- Python environment resolves
- dev tools exist
- pytest plugins are present
- repo-local MCP setup is not broken

If you cannot complete this phase, stop and fix environment issues before
trying to understand architecture. In BioETL, a broken local toolchain will
create false signals later.

## 1. Canonical Rules Pass (45 minutes)

Read in this exact order:

1. `docs/00-project/00-map.md`
2. `docs/00-project/RULES.md`
3. `docs/00-project/TOOLS.md`
4. `docs/02-architecture/00-overview.md`

Make notes for only these questions:

- What are the five layers?
- Which import directions are forbidden?
- What is the storage model for Bronze, Silver, Gold?
- What commands are canonical?
- Which docs are source of truth?

Do not branch into archive docs at this stage.
Do not read every ADR yet.
The goal is to lock in the project constitution, not all details.

At the end of this block you should be able to say:

- `domain` is pure and cannot do I/O
- `application` orchestrates use cases and transformers
- `infrastructure` owns concrete adapters and storage
- `composition` owns DI and factories
- `interfaces` owns CLI/HTTP/orchestration entry points

## 2. Architecture Map Pass (60 minutes)

Now move from docs into code:

```text
src/bioetl/domain/
src/bioetl/application/
src/bioetl/infrastructure/
src/bioetl/composition/
src/bioetl/interfaces/
```

Read in that order. Do not start from `interfaces` and read downward. Starting
at the top of the dependency graph is the fastest way to build the right mental
model.

In this block, answer these concrete questions:

- Where are the ports?
- Where are pipeline transformers?
- Where are provider adapters?
- Where are factory registrations?
- Where are CLI command entry points?

Keep one code example for each layer:

- a port in `domain/ports/`
- a service or transformer in `application/`
- an adapter in `infrastructure/adapters/`
- a registry or factory in `composition/`
- a command in `interfaces/cli/`

This gives you one anchor file per layer, which is much more valuable than
trying to skim the whole tree.

## 3. ADR Deep Dive (45-60 minutes)

Read only the ADRs that influence almost every task:

- `ADR-005-composition-layer-separation`
- `ADR-010-local-only-deployment`
- `ADR-014-deterministic-writes`
- `ADR-017-observability-architecture`
- `ADR-026-composite-pipeline-pattern`
- `ADR-032-unified-http-client`
- `ADR-042-testing-strategy-matrix`
- `ADR-043-documentation-knowledge-management`

Do not try to memorize all 43 ADRs on day 1.
Instead, write a short one-line summary for each:

- what decision was made
- where it affects code layout
- where it affects tests or operations

These ADRs cover the constraints that most often surprise new contributors:

- why local-first matters
- why Delta is mandatory in Silver
- why composition is a distinct layer
- why observability is port-driven
- why testing has a matrix rather than a single suite
- why docs governance is strict

## 4. Run The Canonical Quality Loop (45 minutes)

Run the minimum useful local validation path:

```bash
make lint
make test-architecture
make test-fast
```

If you have more time or a strong machine:

```bash
make test
```

Add high-signal repo checks:

```bash
python -m scripts.schema validate-configs
python -m scripts.docs check-drift
python scripts/qa/generate_architecture_dependency_map.py --check
```

The point of this block is not just to see green output. It is to learn:

- which checks are fast enough for local iteration
- which checks map to architecture rules
- which checks cover configs and docs, not only code

At the end of this block you should know the difference between:

- `make lint`
- `make test-architecture`
- `make test-fast`
- `make test`
- `python -m scripts.schema validate-configs`
- `python -m scripts.docs check-drift`

## 5. Trace One Pipeline End-To-End (90 minutes)

Pick one existing pipeline. Good starter choices:

- `chembl_activity`
- `pubmed_publication`
- `openalex_publication`

Follow this exact route:

1. pipeline config in `configs/entities/{provider}/{entity}.yaml`
2. provider config in `configs/providers/{provider}.yaml`
3. transformer in `src/bioetl/application/pipelines/{provider}/`
4. schema in `src/bioetl/domain/schemas/{provider}/`
5. contract in `src/bioetl/domain/contracts/gold/`
6. factory/registration in `src/bioetl/composition/factories/` and `src/bioetl/composition/providers/`
7. tests in `tests/unit/`, `tests/integration/`, `tests/e2e/`, and `tests/architecture/`

Write down the exact files you visited. The goal is to prove that you can map
one pipeline through the whole system, not to understand every provider.

If you can do this once, most other pipeline tasks become pattern matching
instead of blind exploration.

## 6. Pick Your Working Lane (60 minutes)

Choose one lane based on the type of work you expect next.

### Lane A: Audit / Review

Read:
- `docs/03-guides/testing.md`
- `docs/03-guides/coverage-configuration.md`
- `docs/02-architecture/generated/module-dependency-map.md`

Run:

```bash
make test-architecture
make lint
python -m scripts.schema validate-configs
python -m scripts.docs check-drift
```

Use:
- `py-audit-bot`
- `py-plan-bot`
- `verify-architecture`

### Lane B: Core Refactor

Read:
- `docs/02-architecture/05-composition-layer.md`
- relevant ADRs for your touched area
- `docs/03-guides/testing.md`

Run:

```bash
make test-fast
make test-architecture
```

Use:
- `py-plan-bot`
- `py-test-bot`
- `py-debug-bot`

### Lane C: New Pipeline / Provider

Read:
- `docs/03-guides/add-pipeline-existing-source.md`
- `docs/03-guides/add-new-source.md`
- `docs/04-reference/templates/`

Run:

```bash
python -m scripts.schema validate-configs --verbose
python -m pytest tests/architecture/test_registry_contracts.py -q
```

Use:
- `new-pipeline`
- `py-config-bot`
- `py-test-bot`

### Lane D: Docs / Knowledge Maintenance

Read:
- `docs/02-architecture/decisions/ADR-043-documentation-knowledge-management.md`
- `scripts/README.md`

Run:

```bash
python -m scripts.docs check-drift
python -m scripts.docs check-links --configs
python -m scripts.docs check-docstrings
```

Use:
- `py-doc-bot`
- `documentation-audit`

### Lane E: VCR / Integration Safety

Read:
- `docs/03-guides/testing.md`
- `configs/quality/test_matrix.yaml`

Run:

```bash
python -m scripts.data check-vcr-placement
python -m scripts.data check-vcr-naming
make test-integration
```

Use:
- `vcr-record`
- `py-test-bot`
- `py-test-swarm`

## 7. End-Of-Day Deliverable (20 minutes)

Before ending day 1, write a short personal handoff note containing:

- the pipeline you traced
- the exact commands you ran
- which checks were fast and useful
- which lane you are likely to work in next
- one confusing part of the repo that still needs clarification

If this is an AI session rather than a human onboarding, the equivalent output
is a short working summary in the conversation or in a non-normative report.

## 8. Anti-Patterns For Day 1

Avoid these common mistakes:

- reading `docs/99-archive/` before active docs
- starting from `interfaces/` instead of `domain`
- treating `README.md` as the only source of truth
- using ad-hoc shell commands when `make` or `python -m scripts.<group>` exists
- changing code before running at least one architecture check
- assuming every docs file is canonical just because it exists

## 9. Default One-Day Schedule

If you want a time-boxed route, use this:

- 09:00-09:30 — Preflight and install
- 09:30-10:15 — Rules pass
- 10:15-11:15 — Architecture map pass
- 11:15-12:00 — ADR deep dive
- 13:00-13:45 — Canonical quality loop
- 13:45-15:15 — Trace one pipeline end-to-end
- 15:15-16:15 — Pick working lane and run lane-specific checks
- 16:15-16:35 — Write end-of-day summary

## 10. Minimal Day-1 Outcome

If you only have a partial day, do these five things and stop:

1. Read `AGENTS.md`
2. Read `docs/00-project/00-map.md` and `docs/00-project/RULES.md`
3. Read `docs/02-architecture/00-overview.md`
4. Run `make test-architecture`
5. Trace one pipeline from config to tests

That is the shortest path to becoming useful in this repository without working
blind.
