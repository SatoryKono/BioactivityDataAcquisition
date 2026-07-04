______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-01'

______________________________________________________________________

# Template Index

Published entrypoint for documentation templates used by BioETL governance and
reference docs.

The index is normative as a discoverability surface. Individual template files
remain implementation templates and MAY keep `Class: internal`.

## Core Templates

| Template type                 | File                                                                               | Primary use                                            |
| ----------------------------- | ---------------------------------------------------------------------------------- | ------------------------------------------------------ |
| `adr`                         | [adr-template.md](adr-template.md)                                                 | Architecture decisions                                 |
| `runbook`                     | [runbook-template.md](runbook-template.md)                                         | Operator procedures                                    |
| `provider-spec`               | [provider-spec-template.md](provider-spec-template.md)                             | Provider reference docs                                |
| `pipeline-spec`               | [pipeline-spec-template.md](pipeline-spec-template.md)                             | Pipeline reference docs                                |
| `data-contract-spec`          | [data-contract-spec-template.md](data-contract-spec-template.md)                   | Data contract and published schema docs                |
| `control-plane-contract-spec` | [control-plane-contract-spec-template.md](control-plane-contract-spec-template.md) | Feature-flagged control-plane and inspection contracts |

`contract-spec` MAY be used as a short alias for `data-contract-spec`, but the
published governance name for the family is `data-contract-spec`.

## Governance Links

- [D-01: Governance & Style Guide документации BioETL](../../00-project/governance/01-documentation-governance-style-guide.md)
- [Documentation Publication Policy](../../00-project/governance/06-doc-publication-policy.md)
- [Documentation Navigation Policy](../../00-project/governance/07-doc-nav-policy.md)

## Control-Plane Example

Use the following published pack as the reference example for
`control-plane-contract-spec`:

- [ADR-044: Run Manifest and Run Ledger Control Plane](../../02-architecture/decisions/ADR-044-run-manifest-ledger-control-plane.md)
- [Run Manifest and Run Ledger Contract](../contracts/run-manifest-ledger.md)
- [Run Manifest Inspection](../../05-operations/runbooks/run-manifest-inspection.md)
