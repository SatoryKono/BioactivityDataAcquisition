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

The supported launch surface is `python -m scripts.ai vibe` plus the canonical
`launch.sh` / `launch.ps1` entrypoints and the local `helper/` setup/check
helpers.

## Retired compatibility path

`python -m scripts.ai.vibe` was a direct module-level compatibility shim during
the module-dispatch migration. It was retired on 2026-05-21 after the
in-repository caller audit found no active callers. Use
`python -m scripts.ai vibe` for Python dispatch.
