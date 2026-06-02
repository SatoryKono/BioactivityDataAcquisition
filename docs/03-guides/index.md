______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-06-02'

______________________________________________________________________

# Guides Index

## Purpose

This page is the landing surface for practical how-to guidance in
`docs/03-guides/`.

Use guides for step-by-step workflows and operator/developer procedures. Use
architecture docs for design rationale and boundaries, and use reference docs
for published contracts, CLI surfaces, and specs.

## Common Entry Points

| Need                               | Entry point                                            |
| ---------------------------------- | ------------------------------------------------------ |
| Bootstrap quickly                  | [quick-start.md](quick-start.md)                       |
| Full local setup walkthrough       | [getting-started.md](getting-started.md)               |
| Run and resume pipelines           | [running-pipelines.md](running-pipelines.md)           |
| Understand the workflow object     | [workflows.md](workflows.md)                           |
| GitHub setup and workflow          | [github-setup-plan.md](github-setup-plan.md)           |
| GitHub quick reference             | [github-quick-reference.md](github-quick-reference.md) |
| GitHub local workflow              | [github-local-workflow.md](github-local-workflow.md)   |
| GitHub workflow diagrams           | [github-workflow-diagrams.md](github-workflow-diagrams.md) |
| Verify docs and strict site build  | [docs-verification.md](docs-verification.md)           |
| Understand pipeline lifecycle      | [pipeline-lifecycle.md](pipeline-lifecycle.md)         |
| Configure pipelines                | [pipeline-configuration.md](pipeline-configuration.md) |
| Configure DQ behavior              | [dq-configuration.md](dq-configuration.md)             |
| Apply repository cleanup safely    | [cleanup.md](cleanup.md)                               |
| Run tests and local verification   | [testing.md](testing.md)                               |
| Debug common local problems        | [troubleshooting.md](troubleshooting.md)               |
| Metrics and local monitoring setup | [metrics-monitoring.md](metrics-monitoring.md)         |
| Dashboard usage and extension      | [dashboards/README.md](dashboards/README.md)           |
| Configure development tools        | [development/pycharm-setup.md](development/pycharm-setup.md) |

## Role Boundaries

- [Quick Start](quick-start.md): fastest supported bootstrap path and first-run
  smoke flow.
- [Getting Started](getting-started.md): fuller onboarding guide with
  prerequisites, environment setup, configuration, and initial troubleshooting.
- [Running Pipelines](running-pipelines.md): execution, run types, resume,
  cached bronze, and control-plane inspection commands.
- [Workflows](workflows.md): declarative workflow object model, step identity,
  DAG semantics, built-in transforms, and shipped workflow control-plane split.
- [GitHub Setup Plan](github-setup-plan.md): comprehensive GitHub repository
  setup guide covering local Git config, CI/CD workflows, branch strategy,
  security, and release process.
- [GitHub Quick Reference](github-quick-reference.md): one-page cheatsheet with
  essential commands and procedures for daily GitHub workflow.
- [GitHub Local Workflow](github-local-workflow.md): detailed local Git workflow,
  branch management, sync strategy, and PR creation process.
- [GitHub Workflow Diagrams](github-workflow-diagrams.md): visual Mermaid
  diagrams for feature development, CI pipeline, PR lifecycle, and troubleshooting.
- [Docs Verification](docs-verification.md): published docs checks, strict
  build flow, mixed-environment notes, and recurring documentation audit
  checklist.
- [Cleanup](cleanup.md): deterministic local cleanup and retention-sensitive
  hygiene workflow.
- [Metrics & Monitoring](metrics-monitoring.md): local observability setup and
  metric catalog.
- [Testing](testing.md): test strategy, local execution paths, and governance.
- [Troubleshooting](troubleshooting.md): symptom-oriented problem solving.
- [Development Setup](development/pycharm-setup.md): IDE-specific local setup
  and repository integration notes.

## Related Published Surfaces

- [Architecture Overview](../02-architecture/00-overview.md)
- [Reference Index](../04-reference/index.md)
- [Operations Runbooks](../05-operations/runbooks/index.md)
