______________________________________________________________________

Version: 1.1.0
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-02'

______________________________________________________________________

# BioETL Kubernetes Manifests - Summary

> **Status:** Internal / Extended document (experimental deployment profile, non-normative for default operations).
> **Note (ADR-010):** BioETL primary deployment model is **Local-Only** (file-based,
> no Docker/Redis in runtime). See [ADR-010](../../02-architecture/decisions/ADR-010-local-only-deployment.md).
> This Kubernetes material is provided for **advanced/experimental use only** and is
> not the recommended deployment strategy.
> It is outside standard operational support runbooks and release flow.
> Placement note: this page lives under [Deployment & Tooling Extras](README.md),
> not under the standard operations/runbook path.

## Purpose

This page is the compact index for the experimental Kubernetes subtree. It is
not a second deployment guide. Use it to answer:

1. Which manifest files exist here?
1. Which document should I read for procedures and troubleshooting?

For actual step-by-step deployment flow, use
[deployment-guide.md](deployment-guide.md).

## Experimental Assets

### Core manifests

1. `k8s-deployment.yaml`

   - BioETL application deployment
   - service, PVC, ConfigMap, Secret
   - ServiceAccount and RBAC wiring

1. `k8s-monitoring.yaml`

   - Prometheus deployment and service
   - Grafana deployment and service
   - monitoring ConfigMaps and secrets
   - monitoring PVCs

1. `k8s-networking.yaml`

   - ingress and TLS routing
   - HPA and PodDisruptionBudget
   - NetworkPolicy and ResourceQuota

### Supporting docs and helpers

4. [deployment-guide.md](deployment-guide.md)

   - prerequisites
   - image build/push flow
   - namespace and manifest apply steps
   - verification, rollout, backup, troubleshooting

1. `scripts/ops/runtime/deploy/deploy-bioetl.sh`

   - helper automation for deploy/update/delete/status/logs
   - convenience wrapper around the experimental manifests

## Minimal Usage Pattern

If you are evaluating this experimental path, the intended reading order is:

1. Read [deployment-guide.md](deployment-guide.md)
1. Inspect the three YAML manifests
1. Optionally use `scripts/ops/runtime/deploy/deploy-bioetl.sh`
1. Return to standard runbooks for supported operations work

## Quick Orientation

- Metrics endpoint: exposed from the BioETL app pod on port `8000`
- Monitoring stack: Prometheus + Grafana
- Persistence: PVC-backed application and monitoring storage
- Networking extras: ingress, autoscaling, disruption budget, quotas

## Scope Boundary

This subtree does **not** redefine the supported production posture of BioETL.
It remains experimental material only. The supported operator model is still:

- local-only single-instance execution
- filesystem-backed checkpoints and storage
- in-memory locking
- standard runbooks under `docs/05-operations/`

## Troubleshooting Pointer

For concrete troubleshooting procedures and rollout commands, see
[deployment-guide.md](deployment-guide.md).
