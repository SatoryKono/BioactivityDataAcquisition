# Orchestration: project-evidence-rebaseline

- Mode: `full`
- Shard strategy: `custom`
- Parent output root: `docs/reports/evidence/project-evidence-rebaseline/`

## Topic

Repo-wide re-baseline of mutable evidence layers under `docs/reports/evidence/` to the
current code and documentation state.

Special rule for this wave:

- refresh `RAW-*` and `EV-*` packs in place under their existing evidence roots;
- refresh `SUMMARY`, `SYN-*`, `CROSS-SYNTHESIS`, and decision/backlog layers where needed;
- preserve historical meaning, but let current-state evidence replace outdated baselines;
- do not rewrite evidence families outside the assigned shard scope.

## Shards

| Shard                                          | Scope                                                                      | Output Root              | Status    |
| ---------------------------------------------- | -------------------------------------------------------------------------- | ------------------------ | --------- |
| `evidence-rebaseline-naming`                   | naming-drift families and parent naming packs                              | `docs/reports/evidence/` | completed |
| `evidence-rebaseline-documentation`            | documentation-drift families and parent documentation packs                | `docs/reports/evidence/` | completed |
| `evidence-rebaseline-compatibility-governance` | compatibility, import-governance, ownership, loader/runtime seam packs     | `docs/reports/evidence/` | completed |
| `evidence-rebaseline-structure-topology`       | file-structure, package-topology, topology-recursive, layer package packs  | `docs/reports/evidence/` | completed |
| `evidence-rebaseline-architecture-diagrams`    | architecture, diagram-state, artifact-surface packs                        | `docs/reports/evidence/` | completed |
| `evidence-rebaseline-quality-health`           | dependency, debt, test-health, duplication, broader quality evidence packs | `docs/reports/evidence/` | completed |

## Agent Ownership

| Shard                                          | Owner           |
| ---------------------------------------------- | --------------- |
| `evidence-rebaseline-naming`                   | `Copernicus`    |
| `evidence-rebaseline-documentation`            | `Volta`         |
| `evidence-rebaseline-compatibility-governance` | `Tesla`         |
| `evidence-rebaseline-structure-topology`       | `Chandrasekhar` |
| `evidence-rebaseline-architecture-diagrams`    | `Halley`        |
| `evidence-rebaseline-quality-health`           | `Bohr`          |

## Output Roots

Each shard owns a disjoint family of existing evidence directories under `docs/reports/evidence/`
and may update:

- `01-pillars/PILLARS.md` only if scope drift requires it
- `02-evidence/**/RAW-*.md`
- `02-evidence/**/EV-*.yaml`
- `SUMMARY.md`
- `03-synthesis/**`
- `04-decisions/**` and `05-risks/**` only when evidence IDs or current-state wording drift

Parent artifacts produced by the L1 orchestrator:

- `docs/reports/evidence/project-evidence-rebaseline/ORCHESTRATION.md`
- `docs/reports/evidence/project-evidence-rebaseline/SUMMARY.md`
- `docs/reports/evidence/project-evidence-rebaseline/03-synthesis/CROSS-SYNTHESIS-project-evidence-rebaseline.md`

## Gate Rules

- collection gate: each refreshed pack must still have a valid evidence set and coherent `RAW-*`
- synthesis gate: parent and shard syntheses must cite current `EV-*` ids
- closeout gate: `git diff --check -- docs/reports/evidence`

## Aggregation Plan

1. Refresh child evidence families in parallel by shard.
1. Validate refreshed evidence layers and gate status per shard.
1. Refresh shard-level synthesis and backlog/decision wording where needed.
1. Build one parent cross-synthesis for repo-wide evidence re-baseline.
1. Publish parent summary with completed shard list and remaining stale families, if any.

## Closeout

- All six shard families were rebaselined against the 2026-03-21 repository state.
- Five shard families reported explicit closeout notes via delegated agents.
- The remaining `quality-health` shard was validated locally from refreshed pack outputs plus a clean
  `git diff --check` over its assigned scope.
- A 2026-03-27 parent sweep then reviewed all 41 root evidence packs sequentially at the summary
  layer, added freshness notes to each root `SUMMARY.md`, materially reopened the
  `documentation-internal-surface-governance` pack, and published a root-pack review matrix in
  `06-status/EVIDENCE-PACK-REVIEW-2026-03-27.md`.
- Parent closeout artifacts:
  - `docs/reports/evidence/project-evidence-rebaseline/SUMMARY.md`
  - `docs/reports/evidence/project-evidence-rebaseline/03-synthesis/CROSS-SYNTHESIS-project-evidence-rebaseline.md`
  - `docs/reports/evidence/project-evidence-rebaseline/06-status/EVIDENCE-PACK-REVIEW-2026-03-27.md`
