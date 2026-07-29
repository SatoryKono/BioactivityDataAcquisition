______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-07-28'

______________________________________________________________________

# Operator UX v2 (Dashboard System 2.0)

Source of truth for layout: `grafana/dashboards/*.json`.
Normative design track for epic #6800 (DUX). See also
[verdict-ontology.md](verdict-ontology.md), [migration-map-v2.md](migration-map-v2.md),
[library-panels-inventory.md](library-panels-inventory.md),
[metrics-readiness-matrix.md](metrics-readiness-matrix.md).

## Goals

1. **Evidence first** — live status, suspects, and matrices before multi-paragraph prose.
2. **Explicable verdicts** — every non-OK state exposes basis + confidence + next action.
3. **Context-preserving handoffs** — inter-dashboard links keep `${__url_time_range}` and key vars.
4. **≤7 first-class workspaces** — Fleet / Incident / Pipeline / Provider / Data Trust / Control Plane / Run.
5. **Platform-agnostic** — no lock-in to Grafana Drilldown Investigations.

## First-screen zones (required)

| Zone | Purpose | Budget |
| --- | --- | --- |
| **Nav bus** | Full portfolio switcher `0–6` (Trust…Run Explorer) | `h≤3`, wrap at 1024px; owned by `render_nav_bus.py` |
| **Status strip** | Current verdict + provenance | Provenance + Status shell (ids stable where contracted) |
| **Evidence** | Population / matrix / blockers / reasons | Above fold (typically `y` ≤ 17) |
| **Actions** | ≤4 CTA links or compact route table | Not a multi-screen narrative |
| **Confidence** | Missing telemetry / INCOMPLETE basis | Explicit copy or card, never silent green |

### First-screen checklist (agents + humans)

Before shipping a dashboard edit:

1. Can an operator answer the ONE BIG QUESTION in ≤30s without expanding rows?
2. Is evidence (table/matrix/stat strip) visible before long provenance prose?
3. Are First Action CTAs ≤4 and actionable (dashboard/runbook links with time)?
4. Do empty states distinguish: no events / no projection / no scrape / invalid scope?
5. Is `run_id` never used as a Prometheus high-cardinality label?
6. Do collapsed rows hold forensics only (Tier 3–4)?

## Prose budget

- Nav text panels: navigation chrome only, not runbooks.
- Provenance: scope + identity anchors; full manifest forensics stay collapsed.
- First Action: ordered steps or route table; max ~120 words equivalent.

## Variable-secondary rule

Selectors (`pipeline`, `run_type`, `provider`, …) are **filters**, not the primary
UX. Population-first boards (Provider Fleet, Overview Inputs) must answer without
requiring a precise provider selection.

## Empty-state taxonomy

| UI signal | Meaning | Next action |
| --- | --- | --- |
| `0` / VALID EMPTY | Query ok, zero matching events | Stay / monitor |
| `UNKNOWN` / TELEMETRY ABSENT | Required series missing | Scrape/rules repair |
| `INCOMPLETE` | Trust gate: evidence gap | Fix missing evidence before resume |
| Backend error | HTTP/Prom failure | Check Ops HTTP / Prometheus |

## DSA residual grammar (2026-07-28)

- First-screen cell = `state × confidence × basis × next_action` ([verdict-ontology.md](verdict-ontology.md)).
- **Operations Home** (`bioetl-overview-v2`): Status + Inputs + First Action; domain tables stay collapsed matrix detail.
- **Run Explorer hub**: only `bioetl-run-explorer-v1` ships full first-screen ID/Processed Records; other boards keep collapsed thin shell.
- **Telemetry confidence** (Runtime `#9102`) is not pipeline health.
- **Incident** remains read-only; alerts now + history form one evidence timeline.
- Portfolio remains **7 UIDs**; logical 6-workspace IA via nav/docs/Scenes (ADR-053).

## Context-preserving link standard

Every inter-dashboard link MUST:

- include `${__url_time_range}` (or `from=${__from}&to=${__to}` for Explore)
- pass allowed vars only (see `contracts/navigation-links.yaml`)
- set `includeVars: false` when URL enumerates vars explicitly
- never inject `run_id` into Prometheus selectors

## KPI targets (measurement, not claims)

See [usability-baseline-protocol.md](usability-baseline-protocol.md):

| Proxy | Baseline (pre-2.0 audit) | Target |
| --- | ---: | ---: |
| Clicks to first cause | 6–12 | 3–5 |
| Screens per investigation | 4–5 | 2–3 |
| Time-to-first-suspect | often >60s | ≤30s on first screen |

## WCAG notes

- Status colors use green/orange/red/gray with **text mappings** (OK/WARN/CRIT/UNKNOWN).
- Nav bus keeps contrast on dark/light themes (theme-safe borders).
- Do not rely on color alone for severity.
