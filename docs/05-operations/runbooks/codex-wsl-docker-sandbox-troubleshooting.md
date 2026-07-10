# Codex WSL Docker Sandbox Troubleshooting

This runbook replaces the former root-level
`CODEX_SANDBOX_TROUBLESHOOT.txt` note.

## Trigger

Use this runbook when Codex setup or Docker sandbox startup fails on Windows /
WSL with Docker Desktop virtualization errors such as:

```text
panic: whp error, failed to set extended vm exits: The parameter is incorrect
```

## Primary Response Order

1. Restart Docker Desktop completely.
1. Verify Hyper-V / CPU virtualization is enabled.
1. Confirm the WSL distro is running as WSL 2.
1. Re-check Docker Desktop WSL integration and memory allocation.
1. Fall back to the non-sandboxed Codex launcher path if the sandbox VM stays
   broken.

## 1. Restart Docker Desktop

```powershell
taskkill /IM "Docker Desktop.exe" /F
taskkill /IM "com.docker.proxy.exe" /F
Start-Sleep -Seconds 5
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
Start-Sleep -Seconds 30
docker ps
```

## 2. Verify Hyper-V and CPU Virtualization

```powershell
Get-WindowsOptionalFeature -Online -FeatureName Hyper-V
```

If Hyper-V is disabled, enable it and reboot:

```powershell
Enable-WindowsOptionalFeature -Online -FeatureName Hyper-V -All
```

Also confirm BIOS virtualization is enabled (`VT-x` / `AMD-V`).

## 3. Confirm WSL 2

```powershell
wsl --list -v
```

If the target distro is WSL 1, upgrade it:

```powershell
wsl --set-version Ubuntu 2
```

## 4. Check Docker Desktop Settings

- `Settings > General`: verify container runtime options are healthy.
- `Settings > Resources`: allocate at least 8 GB memory for Codex-heavy runs.
- `Settings > Resources > WSL Integration`: ensure the active distro is
  enabled.

## 5. Fall Back to the Canonical WSL Launchers

If Docker sandbox VMs remain unstable, prefer the canonical Codex launchers
that run the CLI in WSL and keep Docker/MCP as optional adjunct tooling:

```powershell
.\scripts\ai\codex\run-codex.ps1
.\scripts\ai\codex\run-codex.ps1 exec "analyze the failing launcher flow"
.\scripts\ai\codex\run-codex.ps1 check
```

Related setup docs:

- `docs/05-operations/tooling/scripts-ops/CODEX_SETUP.md`
- `docs/05-operations/tooling/scripts-ops/CODEX_WSL_SETUP.md`
- `scripts/ai/codex/QUICKSTART_WSL.md`

## Optional Container Fallback

Only use this when you explicitly need the Docker sandbox image path for
diagnosis:

```powershell
docker pull docker/sandbox-templates:codex
docker run -it --rm `
  -e OPENAI_API_KEY=$env:OPENAI_API_KEY `
  -v "$PWD:/workspace" `
  docker/sandbox-templates:codex `
  codex --dangerously-bypass-approvals-and-sandbox "/workspace"
```

## Validation

After remediation, verify:

```powershell
docker ps
wsl --list --verbose
.\scripts\ai\codex\run-codex.ps1 check
```
