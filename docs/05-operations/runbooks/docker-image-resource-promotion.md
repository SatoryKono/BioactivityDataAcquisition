______________________________________________________________________

Version: 1.0.0
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Priority: P1
  Runtime profile: Local-Only optional Docker adjunct (ADR-010).
  Last verified: '2026-07-16'

______________________________________________________________________

# Docker image and resource promotion

## Trigger

Use this procedure when a retained Docker image/resource change or the complete
workstation bundle is proposed for promotion.

## Impact

Priority P1 for the optional Docker lane. A failed or incomplete campaign
blocks Docker promotion but does not change the canonical Python/venv runtime.

## Preconditions

Docker remains an optional local adjunct under ADR-010. Promotion is performed
only on an explicitly scheduled workstation lane. This runbook does not
authorize edits to `.env`, `.wslconfig`, volumes, VHDX or Docker data. Obtain
explicit host-disruption scheduling and an approved signing identity first.

Before campaign execution, verify that every target volume named by the
release-bundle `migration.volume_map` already exists. The bootstrap records each
legacy volume as `present` or `not_applicable` and fails before Compose mutation
when a target volume is missing. Provisioning or migration requires a separate
approved maintenance procedure and a fresh campaign evidence directory.

## Procedure

## Static and image gates

Every retained `image:` and Dockerfile `FROM` reference must use an immutable
`sha256` digest. Record upstream tag, digest, release URL, architecture and
retrieval timestamp, then run:

```bash
python scripts/ops/runtime/docker/docker_runtime_preflight.py --static-only
python -m pytest tests/architecture/test_docker_runtime_contracts.py -q
```

Compose rendering and readiness are owned by `runtime_manager.py`; do not add a
parallel raw Compose promotion path.

## Host-lane approval

Before `--execute`, the operator must:

1. confirm that repeated target-service and Docker Desktop interruption is
   scheduled and that unrelated local containers may be affected;
2. synchronize the reviewed revision to one Linux filesystem runtime origin;
3. inject required environment values into the process without a repository
   `.env`;
4. select an existing approved GPG secret key and its exact full fingerprint.

The campaign does not create a signing identity. Run from the Linux runtime
origin:

```bash
python scripts/engineering/qa/run_docker_stability_campaign.py \
  --runtime-origin /home/<user>/.local/share/bioetl-runtime/BioactivityDataAcquisition \
  --contract configs/quality/docker_runtime_contracts.yaml \
  --cycles 100 \
  --soak-hours 72 \
  --soak-sample-seconds 60 \
  --engine-recovery-trials 10 \
  --confirm-host-disruption I_UNDERSTAND_THIS_INTERRUPTS_DOCKER_DESKTOP \
  --signing-key <approved-key-id> \
  --signing-fingerprint <full-approved-fingerprint> \
  --execute
```

## Mandatory coverage

The immutable release bundle is `bioetl-main` plus stateful
`bioetl-monitoring`. The runner records both projects and every protected
current/legacy volume across:

- selected service termination;
- failed health/readiness;
- occupied required port;
- expected-image identity drift classification;
- interrupted startup;
- bounded memory/PID pressure;
- supported Docker Desktop engine restart;
- 100 cold/warm idempotency cycles;
- one uninterrupted 72-hour soak;
- 10 bounded engine recovery trials.

Workstation cutover RF-017 (#6311) closes on a continuous healthy observation
window after canonical restore. Default is 24 hours; the active operator
override for the 2026-07 cutover is **2.4 hours**. That window satisfies
RF-017 only when its evidence also covers both stacks, exact Run/Manifest ID,
numeric Processed Records (including a legitimate zero), host/in-network
Prometheus parity, reviewed Grafana panels, and Linux-only Compose origins
(no `/tmp` or Windows bind paths). The separate release-level 72-hour soak and
100-cycle campaign remain under the Docker stability program (#6299).

## Resume and evidence integrity

Resume requires an exact match for runtime origin, contract hash, release
bundle, thresholds, sample interval, evidence/summary paths, fault set and
signing fingerprint. Every existing JSON hash and the complete evidence set are
validated before host mutation. A sampling gap resets the clean soak window;
elapsed time is never reconstructed from configured intervals.

The operational summary is written once and then signed once. It is not
modified after signing. A separate verification receipt records the exact
`VALIDSIG` fingerprint, summary/signature hashes, final gates and promotion
result.

## Release gates

- 100 clean cycles and complete fault matrix;
- continuous 72-hour window with zero unexpected restart, OOM, unresolved
  unhealthy state or identity/origin drift;
- every resource peak below 80% of its hard limit;
- Docker VM free reserve at least 4 GiB and contract disk reserve preserved;
- at least 99% of required engine recoveries (10 trials) complete within 180 seconds;
- zero protected volume loss and exactly one incident record for each failed
  start/recovery;
- detached signature verified against the approved fingerprint.

A missing/partial artifact or failed gate blocks promotion. Do not raise retry,
timeout, resource, health or technical-debt budgets to waive a failure.

## Verification

Verify the detached signature receipt, every release gate, raw evidence hash,
protected volume map and exact campaign identity. A missing field is failure.

## Rollback/Recovery

Restore the last passing pinned image/config bundle and retain failed campaign
evidence. Never roll back by deleting volumes, VHDX or Docker data.

## Post-incident

Record the failed gate, primary cause, affected trial/window, operator and
follow-up issue. Start a new campaign identity only after the defect is fixed.

## Compliance

Docker remains optional under ADR-010; `.env`/`.wslconfig` and technical-debt
budgets remain unchanged by this procedure.
