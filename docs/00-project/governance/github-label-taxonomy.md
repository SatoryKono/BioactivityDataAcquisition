# GitHub label taxonomy, intake, and Wiki ownership

Status: active

Owner: BioETL Team (@SatoryKono fallback)

Effective: 2026-08-30

Review cadence: quarterly and after repository-setting migrations

This page implements the contributor-facing details of
[GitHub Policy](05-github-policy.md). The machine-readable source for label
classification, migration dates, Issue Forms, Wiki posture, and quarterly
controls is configs/quality/github_governance_policy.json. If prose and
configuration diverge, update the configuration and this page together.

## Classification model

Every live label is assigned exactly one protective classification by the
quarterly review:

| Classification | Meaning | Allowed action |
| --- | --- | --- |
| canonical | Preferred vocabulary for new automation and contributor work | Create and apply normally |
| deprecated | Legacy alias or obsolete marker | Migrate references; do not add to new work |
| retained | Project-specific label with no approved replacement | Preserve until an owner explicitly reclassifies it |

Unknown labels default to retained. This prevents an inventory refresh from
silently treating a project-specific integration label as deletable.

## Canonical vocabulary

### Priority

| Canonical label | Meaning |
| --- | --- |
| priority:critical | Immediate/release-blocking work |
| priority:high | Should be addressed soon |
| priority:medium | Normal planned work |
| priority:low | Nice-to-have work |

### Core work type

bug, enhancement, documentation, ci/cd, config, testing, technical-debt,
governance, security, dependencies, cleanup, guardrails, refactor, and
breaking-change are the preferred work labels. Provider and architecture
dimensions use the provider:* and layer:* namespaces defined in
.github/labeler.yml.

Automation-specific canonical labels are contract-failure, api-change,
automated, and stale. An automation consumer MUST use only canonical labels
that exist in the repository.

## Alias migration

The complete mapping is in configs/quality/github_governance_policy.json. The
principal migrations are:

| Legacy family | Canonical target |
| --- | --- |
| P0, priority:P0, critical | priority:critical |
| P1, priority:P1, priority/P1, high-priority | priority:high |
| P2, priority:P2, priority/P2, medium-priority | priority:medium |
| P3, priority:P3, priority/P3 through priority/P8 | priority:low |
| docs | documentation |
| ci, ci-cd, workflow, workflows | ci/cd |
| configs, configuration | config |
| test, tests | testing |
| tech debt, tech-debt, technical debt | technical-debt |
| breaking-changes | breaking-change |
| refactoring | refactor |
| legacy layer names | the matching layer:* label |

The migration window starts on 2026-08-30. Legacy labels MUST NOT be deleted
before 2026-11-30. During the window:

1. New automation and issues use canonical labels only.
1. Open issues and pull requests are migrated to the canonical target.
1. Legacy label descriptions point to the replacement and the end date.
1. The quarterly review continues to classify every live label.
1. Saved-search owners and known external-integration owners are asked to
   attest that they no longer depend on the legacy name.

After the date, deletion still requires human review proving:

- zero open issues and pull requests use the label;
- no repository automation consumes the label;
- saved-search and external-integration review is recorded;
- an export of the final label inventory is attached to the review issue.

Absence from local search is not, by itself, deletion approval.

## Automation consumers

| Consumer | Required label posture |
| --- | --- |
| .github/labeler.yml | Canonical layer:*, provider:*, ci/cd, documentation, and config |
| .github/dependabot.yml | dependencies and ci/cd |
| .github/workflows/contract-tests.yml | contract-failure, api-change, and automated |
| .github/workflows/stale.yml | stale; exemptions remain operational configuration |

## Issue intake ownership

GitHub Issue Forms are the only active intake format:

- bug_report.yml and feature_request.yml are the primary forms;
- retention_sensitive_cleanup.yml is the retained specialized form;
- config.yml disables blank public issues and routes private security reports
  to Security Advisories.

bug_report.md and feature_request.md are inactive migration references: they
intentionally have no YAML front matter and are not offered by the issue
chooser. They remain through the migration window so direct links and external
references can be reviewed before removal.

## Wiki decision and ownership

The GitHub Wiki is disabled. The initial 2026-08-30 audit found the repository
setting enabled but no initialized Wiki repository/pages. BioETL Team owns the
setting and the decision.

Repository documentation is the sole documentation source. Normative
precedence starts at docs/00-project/NORMATIVE_SOURCES.md; a Wiki MUST NOT be
used as a second normative source. Any future proposal to enable Wiki requires
a governance issue that defines a narrow, non-normative purpose, an owner,
review cadence, and links back to canonical repository docs.

## Evidence

The initial inventory and control baseline is
reports/quality/github-settings-review-2026-08-30.json with a readable
Markdown companion. Future evidence is produced by the quarterly read-only
workflow and retained as a workflow artifact.
