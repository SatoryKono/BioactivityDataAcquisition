# Pillar: governance-signals

Priority: high

## Scope

Collect traceable repository evidence for three governance questions:

1. What is the current enforceable `C901` state?
1. How are size hotspots ratcheted today, and how does that differ from the raw hotspot tail?
1. What current duplication signal exists in `composition` and `application`, and is it governed by an enforceable trend gate?

## In Scope

- `./.venv/Scripts/python.exe -m scripts.engineering.qa check-c901`
- `tests/architecture/test_regression_metrics.py`
- `configs/quality/debt_scorecard.yaml`
- `configs/quality/architecture_metric_exemptions.yaml`
- `Makefile`
- Existing raw hotspot inventory in `docs/reports/evidence/dependency-hotspots/`
- Ad hoc duplication scans for:
  - `src/bioetl/composition`
  - `src/bioetl/application`

## Out of Scope

- Provider runtime latency or throughput benchmarks
- Churn history from git blame or commit analytics
- Refactoring recommendations beyond what current governance already measures
- Duplication scans for layers outside `composition` and `application`

## Research Questions

1. Is the current `C901` budget green against the enforceable baseline?
1. Does the size ratchet track all large files, or only exemption registries?
1. Has the file-size ratchet tightened relative to the historical baseline?
1. Which subsystem is explicitly prioritized by named hotspot budgets?
1. Is duplication in `composition` and `application` part of an enforceable governance trend, or only visible through ad hoc scans?
