______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-28'

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
| Understand run lifecycle           | [run-lifecycle.md](run-lifecycle.md)                   |
| Understand replay support          | [replay-guide.md](replay-guide.md)                     |
| Configure pipelines                | [pipeline-configuration.md](pipeline-configuration.md) |
| Configure DQ behavior              | [dq-configuration.md](dq-configuration.md)             |
| Understand DQ framework boundaries | [dq-framework.md](dq-framework.md)                     |
| Apply repository cleanup safely    | [cleanup.md](cleanup.md)                               |
| Run tests and local verification   | [testing.md](testing.md)                               |
| Debug common local problems        | [troubleshooting.md](troubleshooting.md)               |
| Metrics and local monitoring setup | [metrics-monitoring.md](metrics-monitoring.md)         |
| Observability architecture/runtime | [observability-guide.md](observability-guide.md)       |
| Shipped dashboard inventory        | [dashboard-guide.md](dashboard-guide.md)               |
| Dashboard usage and extension      | [dashboards/README.md](dashboards/README.md)           |
| Configure development tools        | [development/pycharm-setup.md](development/pycharm-setup.md) |
| CLI commands quick reference       | [cheatsheets/cli-commands.md](cheatsheets/cli-commands.md) |
| Pipeline config cheatsheet         | [cheatsheets/pipeline-config.md](cheatsheets/pipeline-config.md) |
| Data quality rules cheatsheet      | [cheatsheets/data-quality-rules.md](cheatsheets/data-quality-rules.md) |
| ADR decision matrix                | [cheatsheets/adr-matrix.md](cheatsheets/adr-matrix.md) |
| Tutorials (hands-on)               | [tutorials/README.md](tutorials/README.md) |
| MCP integration                    | [mcp-integration.md](mcp-integration.md) |
| Prometheus metrics export          | [prometheus-metrics-export.md](prometheus-metrics-export.md) |
| Grafana dashboard configuration    | [grafana-dashboard-configuration.md](grafana-dashboard-configuration.md) |
| ADR-040 diagram compliance map     | [../02-architecture/diagrams/adr-040-compliance-map.md](../02-architecture/diagrams/adr-040-compliance-map.md) |
| Sequence diagrams                  | [../02-architecture/diagrams/sequence/README.md](../02-architecture/diagrams/sequence/README.md) |
| State machine diagrams             | [../02-architecture/diagrams/state-machines/README.md](../02-architecture/diagrams/state-machines/README.md) |
| Provider data-flow diagrams        | [../02-architecture/diagrams/providers/README.md](../02-architecture/diagrams/providers/README.md) |
| Common error patterns              | [../05-operations/troubleshooting/common-errors.md](../05-operations/troubleshooting/common-errors.md) |
| Performance tuning                 | [../05-operations/performance-tuning.md](../05-operations/performance-tuning.md) |
| DQ investigation procedures        | [../05-operations/dq-investigation-procedures.md](../05-operations/dq-investigation-procedures.md) |
| Lock contention resolution         | [../05-operations/lock-contention-resolution.md](../05-operations/lock-contention-resolution.md) |
| CI/CD integration                  | [../05-operations/ci-cd-integration.md](../05-operations/ci-cd-integration.md) |

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
- [Observability Guide](observability-guide.md): current observability source
  files, runtime flow, and bounded-label policy.
- [Dashboard Guide](dashboard-guide.md): shipped Grafana dashboard inventory
  and validation commands.
- [Run Lifecycle](run-lifecycle.md): split between runtime execution,
  RunManifest, RunLedger, storage, and quarantine.
- [Replay Guide](replay-guide.md): exact replay support boundaries and
  fail-closed evidence requirements.
- [DQ Framework](dq-framework.md): DQ analyzers, checks, contracts, and
  quarantine boundaries.
- [Testing](testing.md): test strategy, local execution paths, and governance.
- [Troubleshooting](troubleshooting.md): symptom-oriented problem solving.
- [Development Setup](development/pycharm-setup.md): IDE-specific local setup
  and repository integration notes.
- [CLI Commands Cheatsheet](cheatsheets/cli-commands.md): quick reference for all
  BioETL CLI commands organized by category with common examples.

## Related Published Surfaces

- [Architecture Overview](../02-architecture/00-overview.md)
- [Reference Index](../04-reference/index.md)
- [Operations Runbooks](../05-operations/runbooks/index.md)
