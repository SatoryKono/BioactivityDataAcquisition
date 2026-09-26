# Risk Ledger Schema

Use this schema for `05-risks/RISKS.yaml`.

## Entry Shape

```yaml
- id: RISK-market-smb-churn-rate
  risk: "SMB customers may churn if onboarding value is not immediate"
  created_by: DEC-scope-smb-first
  severity: medium
  likelihood: medium
  triggers:
    - "Activation drops below target"
    - "Churn exceeds expected baseline"
  mitigations:
    - "Improve first-run onboarding"
    - "Instrument activation funnel"
  notes: "Track during beta rollout"
```

## Required Fields

| Field         | Type         | Description                                         |
| ------------- | ------------ | --------------------------------------------------- |
| `id`          | string       | Semantic risk ID prefixed with `RISK-`              |
| `risk`        | string       | Concise description of the negative outcome         |
| `created_by`  | string       | The `DEC-*` ID that introduces or surfaces the risk |
| `severity`    | string       | Recommended values: `high`, `medium`, `low`         |
| `likelihood`  | string       | Recommended values: `high`, `medium`, `low`         |
| `mitigations` | list[string] | One or more practical mitigation actions            |

## Recommended Fields

| Field      | Type         | Description                                      |
| ---------- | ------------ | ------------------------------------------------ |
| `triggers` | list[string] | Signals that the risk is materializing           |
| `notes`    | string       | Context, monitoring guidance, or ownership notes |

## Quality Gate

- Every risk links back to a creating decision.
- Severity and likelihood are explicitly stated.
- At least one mitigation is documented.
