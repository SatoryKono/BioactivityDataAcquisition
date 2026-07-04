______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-04'

______________________________________________________________________

# Codex Launcher Path Aliases

Canonical Windows launcher locations and legacy path aliases used by docs,
inventory discovery, and local setup guides.

## Canonical paths

| Launcher | Canonical repo path |
| -------- | ------------------- |
| Interactive Codex | `scripts/ops/launchers/codex/codex.bat` |
| Full-auto Codex | `scripts/ops/launchers/codex/codex-exec.bat` |
| WSL proxy starter | `scripts/ops/runtime/wsl/start-wsl-proxy.bat` |

Repo-root convenience wrappers also exist:

| Wrapper | Resolves to |
| ------- | ----------- |
| `scripts/ops/codex.bat` | `scripts/ops/launchers/codex/codex.bat` |
| `scripts/ops/codex-exec.bat` | `scripts/ops/launchers/codex/codex-exec.bat` |

## Legacy aliases recognized by scripts inventory

The scripts inventory normalizes these Windows-style references to the
canonical paths above:

```text
scripts\codex.bat            -> scripts/ops/launchers/codex/codex.bat
scripts\codex-exec.bat       -> scripts/ops/launchers/codex/codex-exec.bat
scripts\start-wsl-proxy.bat  -> scripts/ops/runtime/wsl/start-wsl-proxy.bat
```

Use forward-slash canonical paths in new docs and automation. Legacy aliases
remain supported for backward-compatible references in existing notes.

## Related guides

- [Codex WSL2 Setup](codex-wsl2-setup.md) — full proxy, WSL, and launcher workflow
