# Optional Docker stability incident

Docker is an optional local adjunct under ADR-010. The canonical Python/venv
runtime does not depend on this probe, its alerts, or any Docker service.

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
