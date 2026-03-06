# Debt Ownership Dashboard (2026-03-06)

- Snapshot date: 2026-03-06
- Registry source: `configs/quality/architecture_metric_exemptions.yaml`
- Scorecard source: `configs/quality/debt_scorecard.yaml`

## Active Owners (Registry Snapshot)

Total exemptions: **116**

| Owner | Active Exemptions | Q2 Allocation | Utilization vs Q2 |
|---|---:|---:|---:|
| `@bioetl-architecture` | 65 | 120 | 54.2% |
| `@bioetl-platform` | 14 | 80 | 17.5% |
| `@bioetl-data-model` | 37 | 50 | 74.0% |

Distinct active owners: **3**

## Subsystem Ownership Mapping

| Subsystem | Owner | Scope |
|---|---|---|
| `architecture` | `@bioetl-architecture` | application, interfaces, cross-cutting architecture |
| `platform` | `@bioetl-platform` | infrastructure, composition, runtime observability |
| `data_model` | `@bioetl-data-model` | domain model, domain schemas, domain mapping |

## Governance Policy

New exemptions are reviewed only when both fields are present:

- `owner`
- `removal_step`

Policy references:

- `configs/quality/architecture_metric_exemptions.yaml` (`policy.required_fields`)
- `configs/quality/debt_scorecard.yaml` (`governance.review_policy`)
