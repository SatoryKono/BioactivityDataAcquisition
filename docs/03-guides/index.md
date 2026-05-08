______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-02'

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
| Verify docs and strict site build  | [docs-verification.md](docs-verification.md)           |
| Understand pipeline lifecycle      | [pipeline-lifecycle.md](pipeline-lifecycle.md)         |
| Configure pipelines                | [pipeline-configuration.md](pipeline-configuration.md) |
| Configure DQ behavior              | [dq-configuration.md](dq-configuration.md)             |
| Run tests and local verification   | [testing.md](testing.md)                               |
| Debug common local problems        | [troubleshooting.md](troubleshooting.md)               |
| Metrics and local monitoring setup | [metrics-monitoring.md](metrics-monitoring.md)         |
| Dashboard usage and extension      | [dashboards/README.md](dashboards/README.md)           |

## Role Boundaries

- [Quick Start](quick-start.md): fastest supported bootstrap path and first-run
  smoke flow.
- [Getting Started](getting-started.md): fuller onboarding guide with
  prerequisites, environment setup, configuration, and initial troubleshooting.
- [Running Pipelines](running-pipelines.md): execution, run types, resume,
  cached bronze, and control-plane inspection commands.
- [Workflows](workflows.md): declarative workflow object model, step identity,
  DAG semantics, built-in transforms, and shipped workflow control-plane split.
- [Docs Verification](docs-verification.md): published docs checks, strict
  build flow, mixed-environment notes, and recurring documentation audit
  checklist.
- [Metrics & Monitoring](metrics-monitoring.md): local observability setup and
  metric catalog.
- [Testing](testing.md): test strategy, local execution paths, and governance.
- [Troubleshooting](troubleshooting.md): symptom-oriented problem solving.

## Related Published Surfaces

- [Architecture Overview](../02-architecture/00-overview.md)
- [Reference Index](../04-reference/index.md)
- [Operations Runbooks](../05-operations/runbooks/index.md)
