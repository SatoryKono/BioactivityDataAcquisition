# References Overlay

Required by `scripts/ai/codex/skills-mirror-contract.json` `reference_overlay`.

Files here are merged on top of `.codex/skills/` when generating
`docs/00-project/ai/skills/local/`. Use this tree for docs-only extras that
are not BioETL runtime skills (vendor/reference skill trees and published
redirect stubs). Do not hand-edit the generated `local/` mirror.

Regenerate:

```bash
python -m scripts.ai.sync.governance --root . --only skill-mirrors --apply
python -m scripts.ai.sync.governance --root . --only skill-mirrors --check
```
