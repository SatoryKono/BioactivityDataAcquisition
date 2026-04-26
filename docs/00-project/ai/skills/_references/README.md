*Статус: internal-published (Internal / Extended)*

# \_references/

Mirror of skill reference bundles used by CI validation scripts.

## Purpose

This directory contains **read-only copies** of `references/` subdirectories
from skills that use multi-file reference bundles (checklists, templates,
schemas, playbooks). CI scripts verify that these mirrors stay in sync
with the canonical sources under `.codex/skills/` and the active runtime skill surface.

Treat this directory as a **reference mirror**, not as a canonical editing
surface. If reference content and runtime skills diverge, the runtime source
still wins and the mirror must be re-synced.

## Consumers

| Script                                    | What it checks                                                         |
| ----------------------------------------- | ---------------------------------------------------------------------- |
| `scripts/ai/codex/check_skills_mirror.sh` | Overlays reference bundles from `_references/local` onto skill mirrors |
| `scripts/ai/codex/check_skills_layout.sh` | Validates `_references` exists as a required subdirectory              |

## Rules

- **DO NOT** edit files here directly; update the canonical source and re-sync.
- **DO NOT** remove this directory; CI will fail (`skills-consistency` workflow).
- Structure mirrors: `_references/local/{skill-name}/references/*.md`
