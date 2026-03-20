# Documentation Drift Remediation Plan

*Status: completed execution plan (non-normative)*
*Date: 2026-03-20*

## Basis

- [Project Documentation Drift Summary](../reports/evidence/project-documentation-drift/SUMMARY.md)
- [Documentation Drift Cross-Synthesis](../reports/evidence/project-documentation-drift/03-synthesis/CROSS-SYNTHESIS-project-documentation-drift.md)
- [Documentation Drift Decision Summary](../reports/evidence/project-documentation-drift/04-decisions/SUMMARY.md)

## Goal

Reduce active documentation errors without opening a repo-wide docs rewrite. The work is ordered by reader risk:

1. active-source AI and project docs that misstate the current workflow or canonical sources
2. project navigation docs with stale paths
3. API and guide docs that overstate public package surfaces
4. architecture docs that under-report current breadth
5. generated and historical derivative surfaces, handled only after source docs are corrected

## Scope Rules

- Prioritize active source docs over generated exports.
- Treat `py-code-bot` status as an authoritative-source problem, not scattered wording drift.
- Keep derivative and historical docs intact unless labeling or regeneration is explicitly part of the slice.
- Avoid editing generated mirrors unless the canonical source is also updated or the mirror is intentionally labeled as compatibility-only.

## Execution Waves

### DD-01. Reconcile `py-code-bot` Status Across Active AI Docs

- **Priority**: P0
- **Status**: completed
- **Objective**: make the current orchestration model readable from one pass through active AI docs
- **Authoritative source**: `.codex/agents/ORCHESTRATION.md`
- **Target files**:
  - `docs/00-project/ai/skills/README.md`
  - `docs/00-project/ai/skills/SKILLS-CATALOG.md`
  - `docs/00-project/ai/skills/SKILLS-PRACTICAL-INDEX.md`
  - `docs/00-project/ai/agents/README.md`
  - `docs/00-project/ai/memory/memory-py-plan-bot.md`
  - `.codex/agents/py-plan-bot.md`
  - `.codex/agents/py-test-bot.md`
- **Expected result**:
  - active docs say production code is written by the orchestrator in the current model
  - `py-code-bot` is treated, where needed, as a deprecated compatibility profile rather than a first-line recommended workflow step
  - canonical-source wording for skills and agent docs is aligned with current Codex-oriented runtime use

### DD-02. Repair Project Navigation Drift

- **Priority**: P1
- **Status**: completed
- **Objective**: remove stale or misleading entry-point links from project navigation docs
- **Target file**: `docs/00-project/00-map.md`
- **Expected result**:
  - navigation docs resolve to live locations only
  - no dead path remains in the primary project map

### DD-03. Correct Reference and Guide Surface Claims

- **Priority**: P1
- **Status**: completed
- **Objective**: bring API and reference wording back in line with actual exported and recommended surfaces
- **Target files**:
  - `docs/04-reference/api/application.md`
  - `docs/04-reference/api/composition.md`
  - `docs/03-guides/pipeline-configuration.md`
- **Expected result**:
  - no over-claimed package-root public API
  - stale inventory statistics corrected

### DD-04. Refresh Architecture Snapshot Docs

- **Priority**: P2
- **Status**: completed
- **Objective**: correct “snapshot shrinkage” where architecture docs understate current breadth
- **Target files**:
  - `docs/02-architecture/diagrams/descriptions/class/07-application-core-services.md`
  - `docs/02-architecture/diagrams/descriptions/class-summary.md`
  - `docs/02-architecture/diagrams/guide/architecture-reference.md`
- **Expected result**:
  - architecture prose reflects current module families without changing architecture policy

### DD-05. Label or Regenerate Derivative Surfaces

- **Priority**: P3
- **Status**: completed
- **Objective**: reduce confusion from generated and historical artifacts that lag behind active source docs
- **Target files**:
  - `docs/exports/full-documentation-no-plans-reports-skills.merged.md`
  - `docs/02-architecture/generated/module-dependency-map.md`
  - historical verification docs under `docs/05-operations/verification/`
- **Expected result**:
  - derivative surfaces are clearly labeled as generated, lagging, or historical
  - regeneration is done only after source docs are clean

## Verification Matrix

After each wave:

1. `./.venv/Scripts/python.exe scripts/docs/check_doc_links.py --configs`
2. `./.venv/Scripts/python.exe -m pytest -q tests/architecture/test_documentation_sync.py`
3. `git diff --check`

Additional verification when diagrams or bundles change:

1. `./.venv/Scripts/python.exe scripts/diagrams/generate_all_bundles.py`

## Implementation Closeout

Delivered in this wave:

- `DD-01`: active AI/project docs now consistently treat orchestrator as the production-code owner in the current Codex workflow, with `py-code-bot` framed as deprecated compatibility drift where it still appears
- `DD-02`: `docs/00-project/00-map.md` no longer points to the removed `src/bioetl/infrastructure/config_loader.py` path and instead references live config-loading entry points
- `DD-03`: API/reference docs now distinguish layer breadth from canonical package-root exports, and the pipeline-config guide reflects the current `configs/` YAML inventory (`51` files)
- `DD-04`: architecture snapshot prose now describes current application-core and related layer families without relying on narrow stale snapshots
- `DD-05`: generated/historical derivative artifacts now carry stronger non-normative and historical labeling to reduce source-of-truth confusion

Wave-level verification completed:

1. `./.venv/Scripts/python.exe scripts/docs/check_doc_links.py --configs`
2. `./.venv/Scripts/python.exe -m pytest -q tests/architecture/test_documentation_sync.py`
3. targeted `git diff --check` on touched files

## Definition Of Done

- active docs no longer conflict on the current AI workflow model
- canonical-source wording is explicit where readers make navigation or implementation decisions
- reference and architecture docs stop overstating or understating current code surfaces
- generated and historical docs are either regenerated or clearly labeled as non-authoritative
- documentation verification gates stay green
