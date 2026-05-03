# Dashboard UX Checks Reports

Store one report per date in this folder using the filename format:

- `YYYY-MM-DD.md`

Use the template below for each scenario in the report.

## Template

```markdown
# Dashboard UX Check — YYYY-MM-DD

## Scenario: <scenario name>
- scenario: <runtime / provider-health / dq / control-plane / workflow / other>
- time-to-first-action: <measured value, e.g. `38s`>
- click-depth: <integer>
- first-hop accuracy: <pass|fail + short note>
```

## Rules

- Dashboard PRs that change `grafana/dashboards/*.json` MUST add/update a
  same-day UX report artifact in this directory.
- Dashboard PR change notes MUST include a link to the created report artifact.
