# Prompt archive

Historical and non-default prompt material. **Not** default operator paste SSOT.

| Subdir | Contents |
| --- | --- |
| `mirrors/` | Snapshots that duplicated runtime agents/skills/workflows — prefer `.codex/**` / `.junie/**` / `.devin/**` |
| `campaigns/` | Long playbooks and pre-library megaprompts (evaluation bloat retained for history) |

Notable campaigns:

- `campaigns/generic-nine-audit-kit-2026-08.md` (+ `…-SOURCES.md`) — nine-domain
  kit #1
- `campaigns/project-audit-orchestrator-kit-2026-08-11.md` (+ `…-SOURCES.md`) —
  nine domains + full N-iteration GitHub orchestrator (kit #2)
- `campaigns/bi-dashboard-audit-kit-2026-08-11.md` (+ `…-SOURCES.md`) — BI
  acceptance (visual/layout/data); prefer
  `../library/observability/bi-dashboard-acceptance.md`

Prefer short cards under `../library/audit/` (including `orchestrator.md`),
`../library/observability/`, and `../library/architecture/review-assessment.md`.

Active short cards live under `../library/`. Discover via `../REGISTRY.yaml` or
`python -m scripts.ai.prompts list`.

External archive: `docs/99-archive/guides/stale-ai-prompts/`.
Collected snapshots index: `../COLLECTED_PROMPTS_INDEX.md`.
