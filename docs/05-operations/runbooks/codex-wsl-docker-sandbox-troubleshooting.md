______________________________________________________________________

Version: 1.1.0
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Priority: P2
  Runtime profile: Local-Only single-instance (ADR-010); Docker/MCP are optional adjunct tooling.
  Last verified: '2026-07-16'

______________________________________________________________________

# Codex WSL Docker Sandbox Troubleshooting

This runbook replaces the former root-level
`CODEX_SANDBOX_TROUBLESHOOT.txt` note.

## Trigger

Use this runbook when Codex setup or the optional Docker sandbox fails on
Windows / WSL with Docker Desktop virtualization errors such as:

```text
panic: whp error, failed to set extended vm exits: The parameter is incorrect
```

## Impact

- Priority: P2.
- The failure blocks optional Codex sandbox tooling; it does not alter the
  local-only BioETL runtime, pipeline data, or control-plane artifacts.
- An unsafe container fallback can expose a token or let an unsandboxed process
  act on a mounted workspace, so it is never the default recovery path.

## Preconditions

- Confirm that the target symptom is a Docker Desktop / WSL sandbox failure,
  rather than a BioETL pipeline failure.
- Have local administrator access before changing Hyper-V or WSL settings.
- Keep Docker/MCP optional under ADR-010; use the canonical WSL launcher for
  normal Codex work.
- Do not create, edit, rename, move, or delete any `.env` file while following
  this runbook.
- An optional container fallback requires explicit task-owner approval, a
  reviewed isolated workspace, and a token supplied only through the local
  process environment. Never paste a token into a command, issue, log, or doc.

## Procedure

### 1. Capture evidence and use bounded Docker Desktop recovery

The helper feature-detects supported `docker desktop status`, `restart`,
`logs`, and `diagnose` commands, captures bounded diagnostics first, and never
begins with a force-kill or WSL shutdown:

```powershell
.\scripts\ops\runtime\docker\restart-docker.ps1 -TimeoutSeconds 180
```

The v2 report classifies Desktop capabilities, CLI and engine origins,
WSL/VHD accessibility, Compose origins, distinct port owners, bind translation,
and Docker data capacity. Every external command and the complete recovery use
the same bounded deadline.

Only after the normal path times out and its report has been reviewed may an
operator explicitly pass both `-ConfirmLastResort` and
`-LastResortConfirmation I_UNDERSTAND_FORCE_TERMINATION_IS_DESTRUCTIVE`.
PowerShell `ShouldProcess` confirmation is still required. The action never
invokes `wsl --shutdown`.

### 2. Verify virtualization and WSL prerequisites

Check Hyper-V and the target WSL distribution:

```powershell
Get-WindowsOptionalFeature -Online -FeatureName Hyper-V
wsl --list --verbose
```

If Hyper-V is disabled, enable it and reboot. If the target distribution is
WSL 1, upgrade the named distribution to WSL 2. Also verify BIOS virtualization
(`VT-x` / `AMD-V`).

```powershell
Enable-WindowsOptionalFeature -Online -FeatureName Hyper-V -All
wsl --set-version <distribution-name> 2
```

### 3. Check Docker Desktop settings

- `Settings > General`: verify that the container runtime is healthy.
- `Settings > Resources`: preserve at least 4 GB Docker-VM reserve and validate
  host-specific peaks before changing limits.
- `Settings > Resources > WSL Integration`: enable the active distribution.
- Record `docker version`, `docker desktop version`, `wsl --version`, the one
  integrated distribution, startup posture, and Resource Saver setting in the
  incident. More than one active engine/CLI origin is a failed topology check.
- Treat Resource Saver and `autoMemoryReclaim=gradual` as optional,
  operator-reviewed host tuning. Automation must not edit `.wslconfig`; apply
  either setting only after a host-specific recovery/volume-preservation test.

### 4. Recover with the canonical WSL launchers

If Docker sandbox VMs remain unstable, use the supported WSL launchers. They
keep Docker/MCP as optional adjunct tooling:

```powershell
.\scripts\ai\codex\run-codex.ps1
.\scripts\ai\codex\run-codex.ps1 exec "analyze the failing launcher flow"
.\scripts\ai\codex\run-codex.ps1 check
```

### 5. Escalate an exceptional container fallback

Do not use `--dangerously-bypass-approvals-and-sandbox` as a normal recovery
step. If diagnostic access to a Docker sandbox image is indispensable, stop
here and obtain explicit task-owner approval for a bounded, isolated diagnostic
session. Record the approved image, workspace scope, token-handling method,
operator, and exit criterion in the incident or issue. Do not mount a workspace
containing secret-bearing files and do not use the fallback to perform writes.

## Verification

After remediation, verify the supported path:

```powershell
wsl --list --verbose
.\scripts\ai\codex\run-codex.ps1 check
```

From the Linux runtime mirror, require readiness rather than a running-only
container check:

```bash
python scripts/ops/runtime/docker/runtime_manager.py check --stack main
python scripts/ops/runtime/docker/runtime_manager.py status --stack main
```

Record the observed Docker/WSL status and launcher result in the incident or
issue before declaring the problem resolved.

## Rollback

- If a Hyper-V or WSL change worsens the host, stop the procedure and restore
  the previous Windows feature or distribution setting through the approved
  local administrator process.
- If Docker remains unhealthy, do not retry an unbounded container fallback;
  return to the canonical WSL launcher path and escalate the host issue.
- No BioETL runtime configuration, pipeline data, or `.env` file is changed by
  this runbook, so no data rollback is expected.

## Post-incident

- Record the error signature, host/WSL version, commands run, and verification
  result.
- Link the incident or issue to any Docker Desktop, WSL, launcher, or
  documentation follow-up.
- Update this runbook only when a supported launcher or safety boundary changes.

## Compliance

| Control | Requirement | Status | Evidence |
| --- | --- | --- | --- |
| Runtime posture | Docker/MCP remain optional under ADR-010 | pass | Preconditions and Procedure |
| Safety | Bypass fallback requires explicit approval and isolated scope | pass | Procedure step 5 |
| Secret handling | No secret values or `.env` mutation | pass | Preconditions |
| Verification | Supported launcher health check is reproducible | pass | Verification |
| Ownership | Incident/issue records operator and outcome | pass | Post-incident |

## References

- [ADR-010: Local-Only Deployment Strategy](../../02-architecture/decisions/ADR-010-local-only-deployment.md)
- [Codex Setup](../tooling/scripts-ops/CODEX_SETUP.md)
- [Codex WSL Setup](../tooling/scripts-ops/CODEX_WSL_SETUP.md)
- [`scripts/ai/codex/QUICKSTART_WSL.md`](../../../scripts/ai/codex/QUICKSTART_WSL.md)
