# Prioritized Hotspot Backlog

Date: 2026-03-21
Status: Proposed
Source pillar: `dependency-hotspots`

This backlog turns the current hotspot evidence into an execution-oriented queue. It follows the proposed prioritization model:

Historical note: the current hotspot snapshot has since shifted to 82 files above 10 KB and 10 files above 350 LOC, with the repeat overlap tail centered on `src/bioetl/interfaces/cli/commands`. The wave ordering below is preserved as a historical backlog artifact, not a live current-state queue.

1. Start with overlap hotspots (`>10 KB` and `>350 LOC`).
1. Use dependency-pressure seams as escalation and tie-break rules.
1. Keep size-only hotspots as phase-two items instead of silently dropping them.

## Prioritization Rule

| Priority Band | Selection Rule                                                                                           | Purpose                |
| ------------- | -------------------------------------------------------------------------------------------------------- | ---------------------- |
| `P0`          | Overlap hotspots in the most concentrated package or in seams with direct dependency-pressure importance | First execution wave   |
| `P1`          | Remaining overlap hotspots outside the first package wave                                                | Second and third waves |
| `P2`          | Size-only hotspots in pressure seams or top-size files                                                   | Phase-two cleanup      |
| `P3`          | Remaining large files above `10 KB` with lower immediate pressure                                        | Long tail              |

## Wave 0: Guardrails and Baseline

**Goal**
Freeze the prioritization baseline before code movement starts.

**Scope**

- Keep [`module-dependency-map.md`](../../../../02-architecture/generated/module-dependency-map.md) current.
- Use [`RAW-dependency-hotspot-metrics-2026-03-20.md`](../02-evidence/dependency-hotspots/RAW-dependency-hotspot-metrics-2026-03-20.md) as the baseline snapshot.
- Carry the wave ordering from [`DEC-HOTSPOT-proposed-decisions-2026-03-20.md`](../04-decisions/DEC-HOTSPOT-proposed-decisions-2026-03-20.md).

**Definition of done**

- Baseline metrics are referenced in the implementation issue or branch plan.
- Each refactor wave names which hotspot set it is shrinking.

## Wave 1: Infrastructure Adapter Concentration

**Priority**
`P0`

**Why first**

- `src/bioetl/infrastructure/adapters` contains `7` of the `17` overlap hotspots.
- This is the single most concentrated dense-file package in the current snapshot.

**Target files**

- `src/bioetl/infrastructure/adapters/crossref/batch.py`
- `src/bioetl/infrastructure/adapters/http/client_retry_mixin.py`
- `src/bioetl/infrastructure/adapters/health_check_mixin.py`
- `src/bioetl/infrastructure/adapters/chembl/fetch_resilience_mixin.py`
- `src/bioetl/infrastructure/adapters/error_handling.py`
- `src/bioetl/infrastructure/adapters/http/health_monitor.py`
- `src/bioetl/infrastructure/adapters/openalex/filter_fetch_adapter_mixin.py`

**Execution intent**

- Split mixin-heavy modules by concern, not mechanically by line count.
- Prefer extracting policy/resilience/monitoring helpers into internal modules while preserving adapter-facing contracts.
- Keep provider-specific behavior tests attached to each slice.

**Exit criteria**

- Hotspot count in `src/bioetl/infrastructure/adapters` decreases materially.
- No regression in provider retry, health-check, or error-handling paths.

## Wave 2: CLI and Application Pressure Seams

**Priority**
`P0` for CLI, `P1` for application overlap hotspots

**Why second**

- `interfaces.cli -> application.services` is one of the named dependency-pressure seams.
- User-facing orchestration logic still contains overlap hotspots and should not wait until the entire infrastructure backlog is done.

**Target files**

- `src/bioetl/interfaces/cli/commands/domains/run/command.py`
- `src/bioetl/interfaces/cli/commands/domains/run/command_policy.py`
- `src/bioetl/application/services/dq/silver_statistics_helpers.py`
- `src/bioetl/application/pipelines/pubmed/extractors/date.py`
- `src/bioetl/application/pipelines/uniprot/extractors/_comment_facets.py`

**Execution intent**

- Decompose CLI run command modules by parsing/policy/presentation seams.
- Split application helpers and extractors around cohesive transformation or statistics responsibilities.
- Keep orchestration contracts stable while shrinking the file surface.

**Exit criteria**

- CLI command path becomes less hotspot-heavy without expanding public seams.
- Application-side helper modules become narrower by responsibility and easier to test in isolation.

## Wave 3: Infrastructure Storage, Config, Quality, and Schemas

**Priority**
`P1`

**Why third**

- These files remain in the overlap tail but are less package-concentrated than adapters.
- They still contribute to dense infrastructure maintenance burden.

**Target files**

- `src/bioetl/infrastructure/storage/gold/io_delta_mixins.py`
- `src/bioetl/infrastructure/storage/base_delta_writer.py`
- `src/bioetl/infrastructure/config/_base.py`
- `src/bioetl/infrastructure/quality/_governance_validation.py`
- `src/bioetl/infrastructure/schemas/silver_chembl_core.py`

**Execution intent**

- Separate I/O, policy, and assembly concerns in storage/config modules.
- Split validation registries and helper blocks in quality governance.
- Break large schema modules only where schema groupings remain semantically clear.

**Exit criteria**

- Remaining infrastructure overlap files fall below the current density thresholds or become materially narrower in responsibility.
- Refactors do not fragment schema/config discoverability.

## Wave 4: Size-Only Tail in Pressure-Seam Modules

**Priority**
`P2`

**Why fourth**

- These files are not in the overlap set, but they are still among the largest modules and include pressure-seam code.
- They are the best candidates for the second-wave inventory after overlap reduction starts.

**Target files**

- `src/bioetl/infrastructure/schemas/silver_publications.py`
- `src/bioetl/application/core/_filtered_data_source_mixins.py`
- `src/bioetl/composition/factories/pipeline/configs.py`
- `src/bioetl/application/pipelines/pubmed/blocks.py`
- `src/bioetl/application/pipelines/uniprot/transformer_business_data_mixin.py`
- `src/bioetl/application/core/runner.py`

**Execution intent**

- Review these modules for packed responsibilities, not just file size.
- Prioritize cases where size intersects with known dependency-pressure seams such as `composition.factories -> application.core`.

**Exit criteria**

- Size-only hotspots are either decomposed or justified as intentionally dense cohesive modules.
- The backlog no longer treats below-350 LOC files as automatically out of scope.

## Residual Long Tail

**Priority**
`P3`

**Scope**

- Remaining files above `10 KB` after waves 1-4.
- Any new hotspot file introduced during ongoing feature work.

**Rule**

- No new file should enter the overlap set without a compensating cleanup plan.
- Size growth in pressure seams should be treated as backlog debt immediately, even if it stays below `350 LOC`.

## Verification Loop

After each wave:

1. Recompute the hotspot snapshot against the same thresholds.
1. Recheck [`module-dependency-map.md`](../../../../02-architecture/generated/module-dependency-map.md) to ensure clean layer policy remains intact.
1. Compare package-level hotspot concentration, especially for:
   - `src/bioetl/infrastructure/adapters`
   - `src/bioetl/interfaces/cli`
   - `src/bioetl/application/pipelines`
   - `src/bioetl/infrastructure/storage`

## Backlog Summary

| Wave   | Priority | Focus                               | Primary Outcome                                       |
| ------ | -------- | ----------------------------------- | ----------------------------------------------------- |
| Wave 0 | Baseline | Metrics and rules                   | Freeze the current hotspot snapshot                   |
| Wave 1 | `P0`     | Infrastructure adapters             | Shrink the most concentrated overlap package          |
| Wave 2 | `P0/P1`  | CLI + application seams             | Reduce user-facing and service-bound hotspot pressure |
| Wave 3 | `P1`     | Storage/config/quality/schema infra | Reduce remaining infrastructure overlap tail          |
| Wave 4 | `P2`     | Size-only tail                      | Catch dense modules missed by LOC-only triage         |
