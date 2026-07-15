# Docker image and resource promotion

Docker remains an optional local adjunct under ADR-010. Image or resource
changes are promoted only from a reviewed supported host lane; this procedure
does not authorize edits to `.env`, `.wslconfig`, volumes, or Docker data.

## Image identity

Every retained `image:` and Dockerfile `FROM` reference must include an
immutable `sha256` digest. Build tooling is version-pinned in the Dockerfile.
To update an image, resolve the candidate digest from the upstream registry,
record its tag, digest, upstream release URL, architecture, and retrieval time
in the change, update exactly one service, then run:

```bash
python scripts/ops/runtime/docker/docker_runtime_preflight.py --static-only
docker compose -p <project> -f <compose-file> config --quiet
python -m pytest tests/architecture/test_docker_runtime_contracts.py -q
```

Rollback restores the last passing digest for that service. It never removes
named volumes or weakens readiness/resource limits.

## Resource calibration

Use `docker_runtime_probe.py` during baseline, canary, the 100-cycle campaign,
and the continuous 72-hour soak. The campaign report must retain raw probe
hashes and prove for every service:

- memory, CPU, and PID peak ratios remain below `0.80` of their hard limits;
- Docker-VM free memory reserve remains at least 4 GiB;
- disk reserve satisfies `docker_runtime_contracts.yaml`;
- restart delta, OOM kills, unresolved unhealthy state, and identity drift are
  all zero.

Do not infer calibration from the configured numbers. A missing or partial
campaign is a failed promotion gate. Increase a service limit only from
measured baseline/canary evidence and preserve the 4 GiB VM reserve; retry,
timeout, health, and technical-debt thresholds may not be raised to waive a
failure.

## Controlled failures

Memory, PID, failed-readiness, termination, and engine-interruption exercises
run only in the explicitly scheduled host lane. Use
`run_docker_stability_campaign.py`; retain its per-cycle/probe/recovery JSON
and detached GPG signature. Unscheduled CI runs static and unit gates only.
