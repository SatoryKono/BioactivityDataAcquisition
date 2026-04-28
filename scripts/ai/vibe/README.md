# scripts/ai/vibe

Canonical Vibe launch tooling.

## Scope

- Vibe interactive launch from WSL/Linux
- Vibe launch from Windows via WSL
- Stable `python -m scripts.ai vibe` entrypoint

## Entry points

```bash
python -m scripts.ai vibe --help
python -m scripts.ai vibe check
python -m scripts.ai vibe setup
bash scripts/ai/vibe/launch.sh --help
pwsh -File scripts/ai/vibe/launch.ps1 --help
```

Historical compatibility context remains under `scripts/ai/mistrallvibe/`, but
the supported launch surface is `python -m scripts.ai vibe` plus the canonical
`launch.sh` / `launch.ps1` entrypoints.
