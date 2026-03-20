# Project Briefing After Capability Discovery

*Date: 2026-03-20*
*Status: non-normative working briefing*

This file summarizes the practical project map discovered from the repository
itself: active rules, capability surface, quality commands, and recommended
reading/working order for common task types.

Related follow-up:
- `docs/plans/onboarding-checklist-day-1-2026-03-20.md`

Authoritative guidance remains in:
- `docs/00-project/`
- `docs/02-architecture/`
- `docs/03-guides/`
- `docs/04-reference/`
- `docs/05-operations/`

Historical material under `docs/99-archive/` remains non-canonical.

## 1. What This Project Is

BioETL is a Python ETL platform for bioactivity and scientific-publication data.
It ingests data from public providers such as ChEMBL, PubChem, UniProt,
PubMed, CrossRef, OpenAlex, and Semantic Scholar into a local medallion-style
warehouse:

- Bronze: raw JSONL + compression
- Silver: Delta Lake
- Gold: analytics-oriented outputs and contracts

Core architectural shape:
- Hexagonal Architecture
- DDD-style domain layer
- Composition root for DI
- Local-Only runtime model

Primary code root:
- `src/bioetl/`

Top-level layer layout:
- `src/bioetl/domain/`
- `src/bioetl/application/`
- `src/bioetl/infrastructure/`
- `src/bioetl/composition/`
- `src/bioetl/interfaces/`

## 2. Active Sources Of Truth

When entering this repository, read these files in order:

1. `AGENTS.md`
2. `docs/00-project/00-map.md`
3. `docs/00-project/RULES.md`
4. `docs/00-project/TOOLS.md`
5. `docs/02-architecture/00-overview.md`
6. `README.md`

For architecture-heavy work, continue with these ADRs:
- `docs/02-architecture/decisions/ADR-005-composition-layer-separation.md`
- `docs/02-architecture/decisions/ADR-010-local-only-deployment.md`
- `docs/02-architecture/decisions/ADR-014-deterministic-writes.md`
- `docs/02-architecture/decisions/ADR-017-observability-architecture.md`
- `docs/02-architecture/decisions/ADR-026-composite-pipeline-pattern.md`
- `docs/02-architecture/decisions/ADR-032-unified-http-client.md`
- `docs/02-architecture/decisions/ADR-042-testing-strategy-matrix.md`
- `docs/02-architecture/decisions/ADR-043-documentation-knowledge-management.md`

## 3. Capability Surface Discovered

### 3.1 Project Agents

The repository has a mature project-local agent layer in `.claude/agents/`.
Important project-specific agents include:

- `py-audit-bot`
- `py-plan-bot`
- `py-test-bot`
- `py-test-swarm`
- `py-debug-bot`
- `py-doc-bot`
- `py-doc-swarm`
- `py-review-orchestrator`

There are also broader generic agents such as:

- `architect-reviewer`
- `code-reviewer`
- `data-engineer`
- `debugger`
- `refactoring-specialist`
- `test-automator`

### 3.2 Project Codex Skills

The active skill layer is `.codex/skills/`.
Most useful skills for day-to-day repo work:

- `capability-discovery`
- `agent-orchestration`
- `verify-architecture`
- `new-pipeline`
- `vcr-record`
- `documentation-audit`
- `documentation-cascade-audit`
- `py-audit-bot`
- `py-plan-bot`
- `py-test-bot`
- `py-test-swarm`
- `py-doc-bot`

Legacy `.claude/skills/` also exists, but it is smaller and not the primary
surface anymore.

### 3.3 Project Commands

The repository also exposes project-specific command docs in
`.claude/commands/`. Notable commands:

- `architecture-guardian`
- `config-validate`
- `documentation-audit`
- `new-pipeline`
- `provider-health`
- `review-orchestrator`
- `schema-parity`
- `test-swarm`
- `vcr-record`
- `verify-architecture`

### 3.4 Codex Runtime

Repo-local Codex settings from `.codex/config.toml`:

- model: `gpt-5.4`
- reasoning effort: `high`
- approval policy: `on-request`
- sandbox: `workspace-write`
- network: enabled

Repo-local MCP config from `.codex/settings.json`:

- `memory`
- `filesystem`
- `sequential-thinking`
- `github`

## 4. Canonical Working Commands

This repository strongly prefers `make`, `uv run`, and unified script entry
points.

### 4.1 Core Quality Loop

```bash
make lint
make test
make test-architecture
```

### 4.2 CI-Like Or Heavier Test Flows

```bash
make test-ci
make test-fast
make test-unit
make test-integration
make test-e2e
```

### 4.3 Direct Canonical Python Commands

```bash
uv run python -m pytest tests/ -x -q
uv run python -m pytest tests/architecture/ -v
uv run python -m mypy --strict src/bioetl/
```

### 4.4 Unified Script Entry Points

```bash
python -m scripts.repo all
python -m scripts.schema validate-configs
python -m scripts.docs check-drift
python -m scripts.docs check-links --configs
python -m scripts.data check-vcr-placement
python -m scripts.data check-vcr-naming
python -m scripts.ci quality-gate
python -m scripts.qa check-c901 --target src/bioetl
```

### 4.5 High-Signal Drift/Architecture Checks

```bash
python scripts/qa/generate_architecture_dependency_map.py --check
python scripts/qa/generate_architecture_dependency_map.py --update
python -m scripts.docs check-drift
python -m scripts.docs check-links --configs
python -m scripts.schema validate-configs --verbose
```

## 5. How To Read The Codebase

Use this order when building context:

1. `src/bioetl/domain/`
2. `src/bioetl/application/`
3. `src/bioetl/infrastructure/`
4. `src/bioetl/composition/`
5. `src/bioetl/interfaces/`

Why this order:
- `domain` defines the language and contracts
- `application` explains orchestration and transformations
- `infrastructure` shows adapters and concrete implementations
- `composition` wires dependencies
- `interfaces` shows user-facing entry points and runtime flow

The matching non-code folders to keep nearby:
- `configs/`
- `tests/`
- `docs/02-architecture/`
- `docs/03-guides/`
- `docs/04-reference/`
- `scripts/`

## 6. Practical Workflow By Task Type

### 6.1 Audit / Review Work

Read first:
- `docs/00-project/RULES.md`
- `docs/02-architecture/00-overview.md`
- `docs/03-guides/testing.md`
- `docs/03-guides/coverage-configuration.md`
- `docs/02-architecture/generated/module-dependency-map.md`

Then run:

```bash
make test-architecture
make lint
python -m scripts.schema validate-configs
python -m scripts.docs check-drift
python scripts/qa/generate_architecture_dependency_map.py --check
```

Recommended skill/agent chain:
- `capability-discovery`
- `py-audit-bot`
- `py-plan-bot`
- `verify-architecture`

### 6.2 Core Refactoring

Read first:
- `docs/02-architecture/00-overview.md`
- `docs/02-architecture/05-composition-layer.md`
- relevant ADRs for touched area
- `docs/03-guides/testing.md`

Before changing code:

```bash
make test-fast
make test-architecture
```

After changes:

```bash
make lint
make test
python scripts/qa/generate_architecture_dependency_map.py --check
python -m scripts.docs check-drift
```

If configs or docs move with the refactor:

```bash
python -m scripts.schema validate-configs
python -m scripts.docs check-links --configs
```

Recommended skill/agent chain:
- `py-audit-bot`
- `py-plan-bot`
- `verify-architecture`
- `py-test-bot`
- `py-doc-bot`

### 6.3 Add A New Pipeline For An Existing Provider

Read first:
- `docs/03-guides/add-pipeline-existing-source.md`
- `docs/03-guides/pipeline-configuration.md`
- `docs/04-reference/templates/`
- `docs/04-reference/templates/pipeline-review-checklist.md`

Expected change zones:
- `configs/entities/{provider}/{entity}.yaml`
- `src/bioetl/application/pipelines/{provider}/...`
- `src/bioetl/domain/schemas/{provider}/{entity}.py`
- `src/bioetl/domain/contracts/gold/...`
- `src/bioetl/composition/factories/...`
- `tests/unit/...`

Canonical checks:

```bash
python -m scripts.schema validate-configs --verbose
python -m pytest tests/architecture/test_registry_contracts.py -q
python -m pytest tests/unit/application/pipelines/{provider}/ -q
```

Useful project skill:
- `new-pipeline`

### 6.4 Add A New Provider

Read first:
- `docs/03-guides/add-new-source.md`
- `docs/03-guides/add-pipeline-existing-source.md`
- `docs/03-guides/pipeline-configuration.md`
- `docs/04-reference/templates/source_adapter.py.tpl`

Expected change zones:
- `configs/providers/{provider}.yaml`
- `configs/entities/{provider}/{entity}.yaml`
- `src/bioetl/infrastructure/adapters/{provider}/`
- `src/bioetl/application/pipelines/{provider}/`
- `src/bioetl/composition/providers/`
- `src/bioetl/composition/factories/`
- tests and provider docs

Canonical checks:

```bash
python -m scripts.schema validate-configs --verbose
python -m pytest tests/architecture/test_registry_contracts.py -q
python -m pytest tests/architecture/test_source_config_usage.py -q
python -m pytest tests/unit/application/pipelines/{provider}/ -q
```

### 6.5 Documentation Work

Read first:
- `docs/00-project/00-map.md`
- `docs/00-project/TOOLS.md`
- `docs/02-architecture/decisions/ADR-043-documentation-knowledge-management.md`
- `scripts/README.md`

Canonical checks:

```bash
python -m scripts.docs check-drift
python -m scripts.docs check-links
python -m scripts.docs check-links --configs
python -m scripts.docs check-docstrings
```

If architecture docs are touched:

```bash
python scripts/qa/generate_architecture_dependency_map.py --check
python -m pytest tests/architecture/test_documentation_sync.py -q
```

Recommended skill/agent chain:
- `py-doc-bot`
- `documentation-audit`
- `documentation-cascade-audit`

### 6.6 VCR / External API Test Work

Read first:
- `docs/03-guides/testing.md`
- `docs/05-operations/verification/vcr-test-tasks.md`
- `configs/quality/test_matrix.yaml`

Canonical checks:

```bash
python -m scripts.data check-vcr-placement
python -m scripts.data check-vcr-naming
make test-integration
```

Useful project skill:
- `vcr-record`

If cassette policy or governance changed:

```bash
python -m scripts.docs check-drift
python -m pytest tests/architecture/test_test_matrix_coverage.py -q
```

## 7. Role-Based Reading Routes

### 7.1 Auditor / Reviewer

Read:
- `AGENTS.md`
- `docs/00-project/RULES.md`
- `docs/02-architecture/00-overview.md`
- `docs/02-architecture/generated/module-dependency-map.md`
- `docs/03-guides/testing.md`
- `configs/quality/test_matrix.yaml`

Run:

```bash
make test-architecture
make lint
python -m scripts.schema validate-configs
python -m scripts.docs check-drift
```

Primary skills:
- `py-audit-bot`
- `py-review-orchestrator`
- `verify-architecture`

### 7.2 Refactoring Engineer

Read:
- `docs/02-architecture/00-overview.md`
- relevant ADRs
- `docs/02-architecture/05-composition-layer.md`
- `docs/03-guides/testing.md`

Run baseline:

```bash
make test-fast
make test-architecture
```

After changes:

```bash
make lint
make test
```

Primary skills:
- `py-plan-bot`
- `py-test-bot`
- `py-debug-bot`

### 7.3 Pipeline Engineer

Read:
- `docs/03-guides/add-pipeline-existing-source.md`
- `docs/03-guides/pipeline-configuration.md`
- `docs/04-reference/templates/`

Run:

```bash
python -m scripts.schema validate-configs --verbose
python -m pytest tests/architecture/test_registry_contracts.py -q
```

Primary skills:
- `new-pipeline`
- `py-config-bot`
- `py-test-bot`

### 7.4 Documentation Maintainer

Read:
- `docs/00-project/00-map.md`
- `docs/00-project/TOOLS.md`
- `docs/02-architecture/decisions/ADR-043-documentation-knowledge-management.md`
- `scripts/README.md`

Run:

```bash
python -m scripts.docs check-drift
python -m scripts.docs check-links --configs
python -m scripts.docs check-docstrings
```

Primary skills:
- `py-doc-bot`
- `documentation-audit`

### 7.5 VCR / Contract Test Maintainer

Read:
- `docs/03-guides/testing.md`
- `configs/quality/test_matrix.yaml`
- `docs/05-operations/verification/`

Run:

```bash
python -m scripts.data check-vcr-placement
python -m scripts.data check-vcr-naming
make test-integration
```

Primary skills:
- `vcr-record`
- `py-test-bot`
- `py-test-swarm`

## 8. Recommended Default Workflow In This Repository

For most non-trivial tasks:

1. Read `AGENTS.md`, `00-map.md`, `RULES.md`, `TOOLS.md`
2. Run capability discovery if context is missing
3. Use `py-audit-bot` or targeted read-only analysis for baseline
4. Use `py-plan-bot` for multi-step work
5. Implement in the correct layer
6. Run `make lint`
7. Run `make test` or at least `make test-architecture`
8. Run config/docs drift checks when relevant

Best project-specific chain:
- analysis: `capability-discovery` -> `py-audit-bot` -> `py-plan-bot`
- implementation: orchestrator + project-specific helper skills
- verification: `verify-architecture` -> `make lint` -> `make test`

## 9. Notes

- Prefer active docs in `docs/00-05`.
- Treat `docs/99-archive/` as historical evidence only.
- Prefer `python -m scripts.<group>` over ad-hoc script paths when possible.
- Prefer `make` for the standard local quality loop.
- Prefer project-local `py-*` skills over generic workflows when the task fits.
