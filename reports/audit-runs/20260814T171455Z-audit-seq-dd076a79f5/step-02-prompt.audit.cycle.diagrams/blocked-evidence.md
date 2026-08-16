# Blocked render evidence

Classification: `ENVIRONMENT`.

The canonical syntax validation wrapper found the host
`/mnt/c/Users/Fedor/AppData/Roaming/npm/mmdc` at version `11.12.0`, while
`scripts/diagrams/mmdc_wrapper.sh` requires `10.6.1`. It failed closed and
explicitly rejected version drift. The pinned Docker fallback image
`minlag/mermaid-cli:10.6.1` is not present locally.

No `MMDC_ALLOW_VERSION_DRIFT` override was used. Existing artifact, visual
smoke, SVG text, and class-method baselines all passed.
