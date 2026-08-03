______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-07-28'

______________________________________________________________________

# Usability baseline protocol (operator dashboards)

Maps to scenarios in [operator-scenarios-s1-s6.md](operator-scenarios-s1-s6.md).

## Stopwatch protocol

1. Start timer when dashboard first paint completes (or screenshot load).
2. Operator has written scenario goal only (no board walkthrough).
3. Stop when first correct suspect is named **or** next action CTA is clicked.
4. Record: time, clicks, screens visited, wrong first drilldown (Y/N).

## Required scenarios (≥4)

| ID | Goal | Entry board | Stop condition |
| --- | --- | --- | --- |
| S1 | What is broken now? | Overview/Fleet | Names degraded subsystem from Inputs/Status |
| S2 | Safe to resume/replay? | Trust | States resume safe/unsafe with basis |
| S3 | Which provider is failing? | Provider | Names provider from GLOBAL matrix/causes |
| S4 | DQ hard fail path | DQ | Separates Now vs Range evidence |
| S5 | Runtime blockers | Pipeline | Names blocker reason or VALID EMPTY+OK |
| S6 | Single-run identity | Run Explorer | Reads run_id identity without Prom labels |

## Score sheet fields

`date, operator, scenario, ttfs_sec, clicks, screens, wrong_first, notes`

## Targets (not claims)

See operator-ux-v2 KPI table. Re-measure after each DUX phase.
