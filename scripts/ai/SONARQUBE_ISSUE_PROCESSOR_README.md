# Sonar Baseline Tooling

## Purpose

The Sonar tooling under `scripts/ai/` is used to make the repository's Sonar
status reproducible from local evidence instead of relying on stale GitHub issue
notes or manual screenshots.

The canonical workflow now has two parts:

1. `scripts/ai/sonar_issue_processor.py`
   - parses `sonar-project.properties`
   - measures the active `sonar.exclusions` quarantine
   - attempts a live SonarCloud / SonarQube unresolved-issues query
   - emits a JSON baseline report

2. `scripts/ai/check_sonar_issues.py`
   - prints a concise audit summary
   - highlights whether the historical near-zero Sonar status should be treated
     as stale
   - optionally fails if a live Sonar baseline cannot be fetched

## Current BioETL assumptions

- canonical Sonar config lives in `sonar-project.properties`
- supported analysis scope is `src/bioetl`
- broad `sonar.exclusions` means the live issue count alone is not enough to
  describe the real debt surface
- the top-level Sonar remediation program should track both:
  - live unresolved issue counts
  - quarantine burn-down over time

## Usage

### Build a JSON baseline report

```bash
python3 scripts/ai/sonar_issue_processor.py --write
```

This writes the report to:

```text
reports/quality/sonar_baseline_report.json
```

### Print a human-readable Sonar baseline audit

```bash
python3 scripts/ai/check_sonar_issues.py
```

### Require live Sonar measurement

```bash
python3 scripts/ai/check_sonar_issues.py --strict-live
```

This exits non-zero if the script cannot fetch a live unresolved-issues summary.

### Enforce quarantine ratchet

```bash
python3 scripts/ai/check_sonar_issues.py --max-quarantine-entries 184
```

This exits non-zero if `sonar.exclusions` grows above the configured threshold.
Lower the threshold only when a remediation wave actually removes entries from the
quarantine.

## Environment variables

The scripts read Sonar credentials from:

```bash
SONARQUBE_TOKEN
SONARQUBE_URL   # optional, defaults to https://sonarcloud.io
SONARQUBE_ORG   # optional metadata only
```

If your repo environment normalizes `SONAR_TOKEN` into `SONARQUBE_TOKEN`, that
also works as long as the final process environment contains `SONARQUBE_TOKEN`.

## Example report fields

The JSON report includes:

- `project.project_key`
- `project.sonar_url`
- `quarantine.entry_count`
- `quarantine.entries`
- `quarantine.buckets`
- `quarantine.top_buckets`
- `live_issues.status`
- `live_issues.total`
- `live_issues.supported_scope_total`
- `live_issues.supported_non_quarantined_total`
- `live_issues.supported_quarantined_total`
- `live_issues.out_of_scope_total`
- `live_issues.issues`
- `assessment.historical_near_zero_status_is_stale`

## Interpreting results

### `live_issues.status = "ok"`

The tool fetched a current unresolved-issues summary from Sonar.

If `live_issues.out_of_scope_total > 0`, the active Sonar project state still
contains findings outside the canonical `sonar.sources` contract and should be
treated as scope drift until the workflow-backed scan becomes authoritative.

If `live_issues.supported_quarantined_total > 0`, the live Sonar project still
reports findings in files that are currently excluded by `sonar.exclusions`.
Treat that as quarantine drift: the cloud-side measurement is not yet honoring
the repo-backed quarantine contract.

### `live_issues.status = "skipped"`

No Sonar token was available in the environment.

### `live_issues.status = "error"`

The tool could not fetch a live baseline. Common reasons:

- invalid token
- insufficient token permissions
- wrong SonarCloud / SonarQube URL
- network failure

## Non-goals

This tooling does not create GitHub issues automatically anymore.

The previous generic layer-based issue creator (`frontend/backend/database`) was
not aligned with the BioETL architecture and should not be treated as the active
workflow for the repository.
