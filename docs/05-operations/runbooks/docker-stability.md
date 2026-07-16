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

# Optional Docker stability incident

## Trigger

Use this runbook when a Docker runtime alert fires, a probe is missing, or a
contracted stack fails readiness/stability checks.

## Impact

Priority P1 for the optional Docker lane. The canonical Python/venv runtime is
not blocked by Docker unavailability.

## Preconditions

Docker is an optional local adjunct under ADR-010. The canonical Python/venv
runtime does not depend on this probe, its alerts, or any Docker service.

Work from one Linux filesystem origin, preserve volumes, and do not edit `.env`
or `.wslconfig`.

## Procedure

When `BioETLDockerRuntimeIncident` fires, open
`reports/quality/docker-stability-latest.json` and use `primary_cause` as the
single first action. Review the bounded `services`, `disk`, `recovery`, and
`observations` evidence; values matching secret-bearing names are redacted.

Run the supported read-only checks from the repository root:

```bash
python scripts/ops/runtime/docker/docker_runtime_probe.py --stack main
python scripts/ops/runtime/docker/runtime_manager.py diagnose --stack main
python scripts/ops/runtime/docker/runtime_manager.py status --stack main
```

Use `runtime_manager.py recover --stack <stack>` only after preflight passes.
Recovery is bounded to three attempts and preserves named volumes. Never use
`docker system prune`, `docker compose down -v`, or delete Docker data as an
incident response shortcut.

When the daemon itself is unavailable, use
`scripts/ops/runtime/docker/restart-docker.ps1`. Its v2 report bounds every
Desktop/WSL command and classifies VHD, engine/CLI origins, ports, binds and
capacity before mutation. Force termination requires the exact two-part
last-resort confirmation described in `docs/DOCKER_SETUP.md`; it is not an
unattended recovery path.

`BioETLDockerRuntimeProbeMissing` means state is unknown, not healthy. Restore
the scheduled host probe or run it manually. Publishing to Pushgateway is
explicit through `--pushgateway-url`; disabling publication does not start,
stop, or modify Docker services.

The `bioetl_docker_runtime_primary_cause` metric is intentionally label-free:
its value is a bounded numeric cause enum (zero means no cause). Never add
command output, image identifiers, incident text, or `stderr` to metric labels.
Probe JSON is recursively redacted before it is written, while exposition
contains only the bounded contract fields.

Host-disruptive Docker Desktop/WSL restart tests are manual-only. They require
explicit operator scheduling because unrelated local containers can be
affected. Force-killing Docker Desktop, `wsl --shutdown`, VHDX deletion, and
`.wslconfig` edits are never unattended recovery actions.

Image provenance, controlled updates, and measured resource-envelope
promotion are defined in
`docs/05-operations/runbooks/docker-image-resource-promotion.md`.

## Verification

Require clean manager status, probe summary, project origins, restart/OOM/
health/image signals, disk/VM reserve and unchanged protected volume identity.

## Rollback/Recovery

Return only to the last passing pinned bundle through the lifecycle manager.
Never use volume/data deletion or prune as rollback.

## Post-incident

Record timestamps, primary cause, bounded commands, evidence paths, operator
and follow-up owner.

## Compliance

Docker remains optional under ADR-010; no secret-bearing file or technical-debt
budget is changed by incident response.
