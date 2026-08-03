# Open Docs Issues — 4 Parallel Runs (2026-07-28)

**Source:** 24 open issues in `SatoryKono/BioactivityDataAcquisition` (all `[Docs]`).  
**Rule:** Run 1 = highest leverage first; Runs 2–4 can execute **in parallel** after Run 1 starts (or fully parallel if staffing allows).  
**Constraints:** docs-only unless an issue forces a tiny SSOT cross-link; no debt-budget growth; prefer links to RULES/REQUIREMENTS/ADRs over inventing policy.

## Priority rationale (Run 1)

| Criterion | Why first |
|-----------|-----------|
| Onboarding friction | CLI + config cheatsheets unblock every contributor |
| Normative SSOT | DQ reference + ADR matrix reduce wrong implementations |
| Architecture truth | ADR-040 diagrams keep hexagonal/docs aligned |
| Ops recovery | Troubleshooting is highest day-2 value |

---

## Run 1 — P0 / highest impact (6 issues)

**Theme:** Foundations — quickstart, SSOT, architecture, firefighting  
**Suggested owner track:** `docs-foundation`  
**Do not parallelize *within* this run if one writer** (shared SSOT cross-links).

| # | Title | Why |
|--:|-------|-----|
| [#6535](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6535) | CLI Commands Cheatsheet for Quick Start | `good first issue`; entry surface for all runs |
| [#6536](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6536) | Pipeline Configuration Cheatsheet | Config is the primary product surface |
| [#6537](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6537) | Data Quality Rules Reference | Normative DQ; high regression risk if wrong |
| [#6538](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6538) | ADR Decision Matrix | Architecture decision navigation |
| [#6543](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6543) | Architecture Diagrams Update (ADR-040) | Diagram/SSOT compliance |
| [#6547](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6547) | Troubleshooting Guide - Common Error Patterns | Highest operator value |

**Exit criteria (Run 1):**
- [ ] Cheatsheets land under `docs/03-guides/` (or existing onboarding paths) and are linked from README/onboarding index
- [ ] DQ reference cites RULES §2.x / contracts, no silent-drop wording
- [ ] ADR matrix links live ADRs; diagrams pass mermaid/ADR-040 checks if touched
- [ ] Troubleshooting maps errors → runbook/command, not folklore

---

## Run 2 — P1 / operator workflows (6 issues)

**Theme:** Day-2 ops — tutorials + investigation  
**Suggested owner track:** `docs-ops`  
**Parallel with:** Run 3, Run 4 (after Run 1 cheatsheets exist preferred)

| # | Title |
|--:|-------|
| [#6539](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6539) | Tutorial: Create New Pipeline in 15 Minutes |
| [#6540](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6540) | Tutorial: Debug Data in Bronze/Silver/Gold Layers |
| [#6541](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6541) | Tutorial: Monitoring and Alerts Setup |
| [#6542](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6542) | Tutorial: Working with Quarantine System |
| [#6549](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6549) | Data Quality Investigation Procedures |
| [#6550](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6550) | Lock Contention Resolution |

**Depends on Run 1:** #6535 CLI + #6537 DQ reference (link, don’t duplicate).

---

## Run 3 — P1 / platform integrations (6 issues)

**Theme:** Observability, MCP, CI, flow diagrams  
**Suggested owner track:** `docs-platform`  
**Parallel with:** Run 2, Run 4

| # | Title |
|--:|-------|
| [#6551](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6551) | MCP Integration Guide |
| [#6552](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6552) | Grafana Dashboard Configuration Guide |
| [#6553](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6553) | Prometheus Metrics Export Guide |
| [#6554](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6554) | CI/CD Pipeline Integration Guide |
| [#6544](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6544) | Sequence Diagrams for Pipelines |
| [#6545](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6545) | Data Flow Diagrams for Each Provider |

**Depends on Run 1:** #6543 architecture diagrams conventions (ADR-040).

---

## Run 4 — P2 / deep domain & advanced (6 issues)

**Theme:** Deep dives — performance, ChEMBL, ontologies, identifiers  
**Suggested owner track:** `docs-domain`  
**Parallel with:** Run 2, Run 3

| # | Title |
|--:|-------|
| [#6546](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6546) | State Machine Diagrams for Workflow Control Plane |
| [#6548](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6548) | Performance Tuning Guide |
| [#6559](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6559) | ChEMBL Normalization Deep Dive |
| [#6560](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6560) | Publication Processing Workflows |
| [#6561](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6561) | Ontology Governance Procedures |
| [#6562](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6562) | Identifier Family Policies |

**Depends on Run 1:** #6537 DQ + #6538 ADR matrix for cross-links.

---

## Parallel execution map

```text
                ┌──────────────────────────┐
                │  Run 1 (P0 foundations)  │  ← start first / highest value
                └────────────┬─────────────┘
           ┌─────────────────┼─────────────────┐
           ▼                 ▼                 ▼
   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
   │ Run 2 ops    │  │ Run 3 plat.  │  │ Run 4 domain │
   │ tutorials    │  │ obs/CI/MCP   │  │ deep dives   │
   └──────────────┘  └──────────────┘  └──────────────┘
        (parallel after Run 1 stubs/links exist)
```

### Staffing options

| Mode | How |
|------|-----|
| **A — Strict** | Finish Run 1 completely, then fan out 2+3+4 |
| **B — Overlap** | Run 1 in progress; after CLI/config cheatsheets land, start 2–4 |
| **C — Full parallel** | Four writers from t0; Run 1 writer owns SSOT links others must reference |

**Recommended:** Mode **B**.

---

## Shared acceptance (any run)

1. New docs under existing docs tree (`docs/03-guides/`, `docs/02-architecture/`, `docs/05-operations/` as fits).
2. Front-matter / status consistent with project docs conventions.
3. Cross-link RULES / REQUIREMENTS / ADRs; no new normative policy in guides alone.
4. Close GitHub issue only with path + short evidence in the issue comment.
5. Prefer updating stale existing pages over parallel duplicate guides.

## Counts

| Run | Issues | Priority |
|-----|-------:|----------|
| 1 | 6 | P0 |
| 2 | 6 | P1 |
| 3 | 6 | P1 |
| 4 | 6 | P2 |
| **Total** | **24** | |
