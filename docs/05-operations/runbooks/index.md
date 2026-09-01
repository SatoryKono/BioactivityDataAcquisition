______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Priority: Informational
  Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
  Last verified: '2026-08-27'

______________________________________________________________________

# Operations Runbooks (Playbooks)

## Trigger

- Use this page to route operators to the correct runbook for the active incident, maintenance action, or diagnostic task.
- Escalate according to the priority declared in metadata when operator ownership is unclear.
- For supported control-plane inspection, this index MUST route operators to the
  published `Run Manifest Inspection` runbook rather than to ad-hoc notes or
  repo-only artifacts.

## Impact

- Incorrect routing delays the correct response path for incidents, maintenance, or diagnostics.
- Use the mapped priority and scope of the target runbook before execution.

## Preconditions

- Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
- Required access: repository checkout, local shell, logs, configuration, and relevant data/control-plane artifacts.
- Confirm the incident or maintenance task has been classified before selecting a target runbook.

## Procedure

### Available Runbooks

### Incident Response

| Runbook                                                     | Description                                                  | Priority |
| ----------------------------------------------------------- | ------------------------------------------------------------ | -------- |
| [Incident Response](incident-response.md)                   | Coordination + routing layer for alert triage and escalation | P1       |
| [Pipeline Failure - Critical](pipeline-failure-critical.md) | Critical pipeline failure handling                           | P0       |
| [Pipeline Failure - DQ](pipeline-failure-dq.md)             | Data Quality failure handling                                | P1       |
| [Pipeline Failure Recovery](pipeline-failure-recovery.md)   | Resume/rebuild/manual rollback (there is no `bioetl rollback`) | P1       |

### Data Management

| Runbook                                                 | Description                                        | Priority |
| ------------------------------------------------------- | -------------------------------------------------- | -------- |
| [Data Recovery](data-recovery.md)                       | Steps to recover from data corruption or loss (DR) | P0/P1    |
| [Game Day](game-day.md)                                 | Annual DR restore drill; RPO 24h / RTO 4h          | P1       |
| [Quarantine Management](quarantine-management.md)       | Managing quarantined records                       | P2       |
| [Backfill/Rebuild](backfill-rebuild.md)                 | Data backfill and rebuild procedures               | P2       |
| [Schema Evolution](schema-evolution.md)                 | Handling schema changes                            | P2       |
| [Canonical Semantic Field Unification](canonical-semantic-field-unification.md) | Registry-driven canonical field rename/drift prevention runbook | P2 |
| [Retention-Sensitive Cleanup](retention-sensitive-cleanup.md) | Bounded cleanup gate for protected data, fixtures, reports, archives, and control-plane artifacts | P1 |

### Infrastructure

| Runbook                                                                     | Description                                                          | Priority |
| --------------------------------------------------------------------------- | -------------------------------------------------------------------- | -------- |
| [Checkpoint Debugging](checkpoint-debugging.md)                             | Debugging checkpoint issues                                          | P2       |
| [Codex WSL/Docker Sandbox Troubleshooting](codex-wsl-docker-sandbox-troubleshooting.md) | Optional Codex sandbox failure triage with a guarded WSL recovery path | P2       |
| [Docker Security Baseline](docker-security-baseline.md) | Reproduce RF-001/RF-002 image baseline and attach bounded Trivy/SBOM evidence | P2       |
| [Neo4j Backend Recovery Quick Start](neo4j-backend-recovery-quick-start.md) | Short recovery checklist for local Neo4j backend incidents           | P2       |
| [Stale Lock](stale-lock.md)                                                 | Handling stale lock situations                                       | P1       |
| [Graceful Shutdown](../../03-guides/pipeline-lifecycle.md#graceful-shutdown) | SIGTERM/SIGINT: finish batch, save checkpoint, release lock          | P1       |
| [Vacuum Procedures](vacuum-procedures.md)                                   | Delta Lake vacuum maintenance                                        | P2       |
| [Windows C:→D: Migration](windows-c-to-d-migration.md)                      | Workstation migration plan execution (user/developer applications)      | P2       |
| [Scaling and Performance Tuning](scaling.md)                                | Local-only performance tuning (vertical scaling + Delta maintenance) | P3       |

### Monitoring

| Runbook                                                                  | Description                                                                                     | Priority |
| ------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------- | -------- |
| [Observability Checklist](observability-checklist.md)                    | Operator validation checklist for metrics, log correlation, dashboards, and diagnostics routing | P2       |
| [Monitoring Surface Reduction (2026-07-23)](monitoring-surface-reduction-2026-07-23.md) | Opt-in monitoring; Loki/Tempo/Quarantine Explorer UI removed; BioETL Ops HTTP identity | P2 |
| [Run Manifest Inspection](run-manifest-inspection.md)                    | Mandatory runbook for the supported RunManifest / RunLedger inspection surface                  | P1       |
| [Workflow Control-Plane Recovery](workflow-control-plane.md)             | Workflow manifest/ledger/state triage, resume, repair, and force procedures                     | P1       |
| [Traceability Signal Ownership](traceability-signal-ownership.md)        | Ownership and escalation matrix for traceability signals                                        | P1       |
| [Traceability Tabletop Drills](traceability-tabletop-drills.md)          | Recurring drill catalog, cadence, and scoring model                                             | P2       |
| [Traceability Adoption Checklist](traceability-adoption-checklist.md)    | Evidence log and exit-gate checklist for operator adoption                                      | P2       |
| [Traceability Wave 5 Closeout Pack](traceability-wave5-closeout-pack.md) | Canonical one-time execution pack for the final Wave 5 closeout gate                            | P2       |
| [Merge Campaign](merge-campaign.md)                                      | Consolidation/merge order and reproducibility gate playbook                                      | P2       |
| [Generated Artifact Drift Workflow](generated-artifact-drift-workflow.md) | Governed regeneration and closeout workflow for generated artifact drift                         | P2       |

### Repository Governance

| Runbook | Description | Priority |
| --- | --- | --- |
| [Quarterly read-only GitHub settings review](github-settings-quarterly-review.md) | Evidence-only review of rulesets, merge/Actions/security settings, environments, CODEOWNERS, labels, Issue Forms, Wiki, and workflow health | P2 |

### Control-Plane / Traceability Routing

- Use [Run Manifest and Run Ledger Contract](../../04-reference/contracts/run-manifest-ledger.md)
  when you need storage layout, rollout flags, invariants, or event baseline.
- Use [Retention-Sensitive Cleanup](retention-sensitive-cleanup.md) before
  deleting from `data/**`, `tests/fixtures/**`, `docs/reports/**`,
  `reports/**`, `docs/99-archive/**`, or control-plane artifact paths.
- Use [CLI Reference](../../04-reference/cli.md) for supported inspection
  commands: `bioetl run-manifest show <run-id|manifest-id>` and
  `bioetl run-manifest diff <left> <right>`.
- Use [Run Manifest Inspection](run-manifest-inspection.md) as the mandatory
  operator runbook for the supported inspection surface.
- Use [Workflow Control-Plane Recovery](workflow-control-plane.md) for
  declarative workflow manifest / ledger / execution-state triage.
- Use [Control-Plane Lifecycle](../control-plane-lifecycle.md) for dry-run/apply
  cleanup of manifests, ledgers, checkpoints, lineage, and cached Bronze.
- Use [ADR-044](../../02-architecture/decisions/ADR-044-run-manifest-ledger-control-plane.md)
  and [ADR-045](../../02-architecture/decisions/ADR-045-dq-contract-system.md)
  and [ADR-047](../../02-architecture/decisions/ADR-047-workflow-control-plane.md)
  when triage depends on the intended control-plane or DQ rollout posture.

### See Also

- [RULES.md](../../00-project/RULES.md) - Project rules and governance
- [Project Navigator](../../00-project/00-map.md) - Active routing map for control-plane and traceability docs
- [CLI Reference](../../04-reference/cli.md) - Supported inspection commands
- [Run Manifest and Run Ledger Contract](../../04-reference/contracts/run-manifest-ledger.md) - Published control-plane contract
- [ADR-044: Run Manifest and Run Ledger Control Plane](../../02-architecture/decisions/ADR-044-run-manifest-ledger-control-plane.md)
- [ADR-045: Data Quality Contract System](../../02-architecture/decisions/ADR-045-dq-contract-system.md)
- [ADR-015: Pipeline Services Lifecycle](../../02-architecture/decisions/ADR-015-pipeline-services-lifecycle.md)

## Compliance

- This runbook MUST be executed within the priority and runtime profile declared in the YAML header.
- Operators SHOULD preserve evidence, commands, and follow-up actions in the Verification and Post-incident sections.
- Supported control-plane inspection MUST keep the contract, CLI reference, and
  `Run Manifest Inspection` runbook aligned as one published documentation pack.

## Verification

- Confirm the selected runbook matches the active symptom, severity, and ownership path.
- Verify that follow-on execution moved into the correct detailed runbook.

## Rollback

- If the wrong runbook was selected, return to this index and reroute immediately.
- Revert to the last known safe operating decision before starting a different procedure.

## Post-incident

- Record timeline, commands executed, evidence reviewed, and follow-up owners.
- Update related alerts, dashboards, or runbooks when operator gaps or ambiguous steps are discovered.


- Duplicate notices MUST be treated as routing pointers only; execute procedures from the linked canonical runbook.
