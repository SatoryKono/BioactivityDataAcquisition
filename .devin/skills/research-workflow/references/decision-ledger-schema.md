# Decision Ledger Schema

Use this schema for `04-decisions/DECISIONS.yaml`.

## Entry Shape

```yaml
- id: DEC-scope-smb-first
  decision: "Target SMB segment before enterprise"
  status: accepted
  owner: user
  created_at: 2026-01-21
  alternatives:
    - Enterprise-first
    - Multi-segment simultaneous
  evidence:
    - EV-users-smb-pain-points
    - EV-economics-smb-unit-economics
  tradeoffs:
    wins:
      - "Faster iteration cycles with smaller customers"
    loses:
      - "Smaller initial contract values"
  risks:
    - RISK-market-smb-churn-rate
  implications:
    - "MVP UX must optimize for self-serve onboarding"
```

## Required Fields

| Field             | Type         | Description                                                     |
| ----------------- | ------------ | --------------------------------------------------------------- |
| `id`              | string       | Semantic decision ID prefixed with `DEC-`                       |
| `decision`        | string       | Clear statement of what was chosen                              |
| `status`          | string       | Recommended values: `accepted`, `provisional`, `needs-research` |
| `owner`           | string       | Decision owner, usually `user` unless another owner is explicit |
| `created_at`      | date         | Decision date in `YYYY-MM-DD` format                            |
| `alternatives`    | list[string] | Options that were considered                                    |
| `evidence`        | list[string] | Supporting `EV-*` IDs                                           |
| `tradeoffs.wins`  | list[string] | Benefits of the chosen option                                   |
| `tradeoffs.loses` | list[string] | Downsides or sacrifices                                         |

## Recommended Fields

| Field          | Type         | Description                                                  |
| -------------- | ------------ | ------------------------------------------------------------ |
| `risks`        | list[string] | Linked `RISK-*` entries created or affected by the decision  |
| `implications` | list[string] | Follow-on consequences for scope, architecture, or execution |

## Quality Gate

- At least two evidence IDs per accepted decision whenever possible.
- At least one alternative must be documented.
- Both wins and loses must be present.
