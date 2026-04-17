# scripts/ai/vibe

Canonical Vibe launch tooling.

## Scope

- Vibe interactive launch from WSL/Linux
- Vibe launch from Windows via WSL
- Stable `python -m scripts.ai vibe` entrypoint

## Entry points

```bash
python -m scripts.ai vibe --help
bash scripts/ai/vibe/launch.sh --help
pwsh -File scripts/ai/vibe/launch.ps1 --help
```

Historical wrappers in `scripts/` remain available as compatibility facades
during the consolidation window.
