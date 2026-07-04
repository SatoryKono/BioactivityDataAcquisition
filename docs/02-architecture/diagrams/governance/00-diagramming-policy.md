______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-20'

______________________________________________________________________

# Historical Diagramming Policy

*Historical compatibility shim; canonical policy lives elsewhere.*

> **Canonical policy:** [`policy.md`](policy.md) (`POL-LLM-DIAGRAMS-001`)
>
> **Canonical diagram root:** [`../README.md`](../README.md)
>
> This file is intentionally retained only as historical context for older
> references and audit trails. It must not redefine the current diagram
> contract.

## Why This File Still Exists

- Older notes, prompts, and review artifacts still point at
  `00-diagramming-policy.md`.
- The repository keeps one stable historical path so those references do not
  break.
- Current diagram work must follow `policy.md`, `README.md`,
  `diagrams-index.md`, and `diagram-views-inventory.md`.

## Historical Assumptions That No Longer Govern The Project

- PlantUML is no longer a canonical format for new BioETL diagrams; Mermaid
  `.mmd` is the required source format, with `.mermaid` reserved for derived
  views.
- Rendered SVG/PNG artifacts are maintained publication outputs, not ignored
  scratch files.
- The old directory/file counts in earlier diagram waves are historical only and
  may differ from the current tracked inventory.
- Validation and rendering now route through the maintained `scripts.diagrams`
  and `scripts.docs` entrypoints documented in the canonical policy.

## Use This Page For

- Understanding why historical references mention earlier diagram conventions.
- Preserving stable links for audit trails and superseded workflow notes.

## Do Not Use This Page For

- Current Definition of Done
- Current render/validation commands
- Current file-count or inventory claims
- Current layout/palette policy

For all of those, use [`policy.md`](policy.md) and the diagram root
[`README.md`](../README.md).
