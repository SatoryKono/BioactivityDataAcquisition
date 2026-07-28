______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-07-28'

______________________________________________________________________

# Verdict ontology (Dashboard System 2.0)

Cross-links: [design-system.md](design-system.md), [operator-ux-v2.md](operator-ux-v2.md).

## Model

Every operator-facing **verdict** is a 4-tuple:

`state × confidence × basis × next_action`

| Field | Meaning |
| --- | --- |
| **state** | OK / WARN / CRIT / INCOMPLETE / UNKNOWN (role-aware; see design-system) |
| **confidence** | high / medium / low / none — based on presence of required evidence |
| **basis** | Why this state (metric, rule, missing series, mixed segments) |
| **next_action** | Single primary CTA (dashboard panel or runbook) |

## Canonical state mapping

| Numeric (L0) | Term | Color |
| ---: | --- | --- |
| 0 | OK | green |
| 1 | WARN | orange |
| ≥2 | CRIT | red |
| null | UNKNOWN | gray |
| 3 (trust gates only) | INCOMPLETE | gray |

### Board-specific status language

| Board | uid | Primary verdict source | Extra states |
| --- | --- | --- | --- |
| Trust / Control Plane | `bioetl-control-plane-v1` | Evidence-aware Status; replay safety cards | **INCOMPLETE** when required checkpoint/scrape evidence missing |
| Overview / Fleet | `bioetl-overview-v2` | `bioetl_l0_status` | UNKNOWN when scope universe missing |
| Pipeline Diagnostics | `bioetl-runtime` | `bioetl_runtime_current_status_trusted` | INCOMPLETE via telemetry gap / scrape trust |
| Provider Health | `bioetl-provider-health-v2` | `bioetl_provider_current_status` (GLOBAL matrix) | Selected provider may disagree with fleet — must be labeled |
| Data Quality | `bioetl-dq-v2` | `bioetl_dq_current_status` | Now / Run / Range are **not** peer badges |
| Incident Workspace | `bioetl-incident-v1` | `bioetl_l0_status` worst-of for scope | `0/1/2` + **labelled** `3/null=UNKNOWN` (never bare numeric); confidence from missing-telemetry / VALID_EMPTY suspects |
| Run Explorer | `bioetl-run-explorer-v1` | HTTP identity + processed records | N/A when no run_id selected |

## Anti-patterns (forbidden)

1. **Silent green** — OK without required evidence present.
2. **Peer badges** — presenting Now vs Range (or selected vs fleet) as equal severity chips.
3. **Prose-only first screen** — multi-paragraph Provenance/First Action without evidence tables.
4. **Bare No data** — empty causes without next action.
5. **UNKNOWN as OK** — mapping null → green.
6. **Bare status number** — e.g. red `3` without text mapping.
7. **Table-wide severity paint** — `color-background` on all columns of a table so timestamps/names look like severity.

## Trust example

`Status=INCOMPLETE`, confidence=`none`, basis=`telemetry missing / checkpoint lag unknown`,
next_action=`Inspect: Telemetry Missing` then runbook checkpoint debug.

## Provider example

`GLOBAL matrix=CRIT`, `selected Status=OK` is **not** a contradiction if selected
provider is healthy while fleet peers fail. Copy must say **fleet vs selected**.
