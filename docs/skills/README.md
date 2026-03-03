# Skills Mirror in docs/

This directory stores documentation mirrors for Codex skills.

## Canonical Source

- Canonical local skill source: `.codex/skills/`
- Canonical local mirror: `docs/skills/local/`
- Rule: edit skills only in `.codex/skills/`; never edit `docs/skills/local/` manually.

## Mirror Operations

- Check mirror drift:
  - `bash scripts/check_skills_mirror.sh --check`
- Sync mirror from canonical source:
  - `bash scripts/check_skills_mirror.sh --sync`

The check is also enforced in CI by `.github/workflows/skills-consistency.yml`.

## Global Snapshot

- `docs/skills/global/` is a documentation snapshot of selected global skills from `/root/.codex/skills/`.
- It is not the canonical source for repository-local skill behavior.

### System Skill References

- Internal system skills are mirrored under `docs/skills/global/.system/`.
- These files are intentionally excluded from the published docs site.
