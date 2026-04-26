______________________________________________________________________

Version: 1.1.0
Status: template
Class: internal
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-01'

______________________________________________________________________

# Control-Plane Contract Specification: <Surface Name>

**Template type:** `control-plane-contract-spec`
**Surface ID:** `<surface_id>`
**Layer:** `control-plane`
**Source of truth:** `<code path>`
**Published contract doc:** `<published doc path>`
**Related ADR:** `<ADR path>`
**Related runbook:** `<runbook path>`
**Related CLI reference:** `<CLI doc path>`

## Purpose

- State what runtime or operator-facing surface this contract defines.
- State whether the surface is feature-flagged, always-on, or transitional.
- State what operators and consumers MUST NOT assume.

## Storage layout

| Artifact       | Path     | Lookup / ownership notes |
| -------------- | -------- | ------------------------ |
| `<artifact_a>` | `<path>` | `<notes>`                |
| `<artifact_b>` | `<path>` | `<notes>`                |

- Storage layout MUST list canonical lookup paths.
- Sidecars, indexes, and correlation anchors SHOULD be identified explicitly.

## Rollout flags

| Setting                                  |   Default | Effect     | Constraints            |
| ---------------------------------------- | --------: | ---------- | ---------------------- |
| `<settings.pipeline.control_plane.flag>` | `<value>` | `<effect>` | `<compatibility rule>` |
| `<settings.pipeline.control_plane.flag>` | `<value>` | `<effect>` | `<compatibility rule>` |

- Flag semantics MUST describe disabled behavior.
- Partial rollout behavior MUST be explicit.
- Incompatible flag combinations MUST be listed.

## Entities / payloads

### <Artifact A>

| Field          | Type     | Required | Notes    |
| -------------- | -------- | -------: | -------- |
| `<field_name>` | `<type>` | \`\<true | false>\` |
| `<field_name>` | `<type>` | \`\<true | false>\` |

### <Artifact B>

| Field          | Type     | Required | Notes    |
| -------------- | -------- | -------: | -------- |
| `<field_name>` | `<type>` | \`\<true | false>\` |
| `<field_name>` | `<type>` | \`\<true | false>\` |

## Current event set / inspection surface

- CLI commands:

```bash
bioetl <command> <args>
```

- Supported identifiers: `<run-id|manifest-id|ledger-id|other>`
- Output modes: `<text|json|yaml>`
- Diagnostics anchors: `<event names / file anchors / correlation ids>`
- Related runbook: `<runbook path>`

## Invariants

1. `<immutable or append-only guarantee>`
1. `<identity lookup guarantee>`
1. `<cross-artifact correlation guarantee>`

## Compatibility / escalation

- Disabled behavior: `<what happens when flags are off>`
- Partial rollout behavior: `<mixed-mode behavior>`
- Incident trigger(s): `<condition that requires escalation>`
- Escalation path: `<team / runbook / owner>`

## References

- `<ADR path>`
- `<published contract doc>`
- `<CLI doc>`
- `<runbook path>`
- `<related guide or provider/pipeline spec>`
