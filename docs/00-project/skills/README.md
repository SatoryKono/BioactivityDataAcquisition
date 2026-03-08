# Skills Mirror in docs/

This directory stores documentation mirrors for Codex skills.

## Canonical Source

- Canonical local skill source: `.codex/skills/`
- Canonical local mirror: `docs/00-project/skills/local/`
- Rule: edit skills only in `.codex/skills/`; never edit `docs/00-project/skills/local/` manually.

## Mirror Operations

- Check mirror drift:
  - `bash scripts/check_skills_mirror.sh --check`
- Sync mirror from canonical source:
  - `bash scripts/check_skills_mirror.sh --sync`

The check is also enforced in CI by `.github/workflows/skills-consistency.yml`.

## Global Snapshot

- `docs/00-project/skills/global/` is a documentation snapshot of selected global skills from `/root/.codex/skills/`.
- It is not the canonical source for repository-local skill behavior.

### System Skill References

- Internal system skills are mirrored under `docs/00-project/skills/global/.system/`.
- These files are intentionally excluded from the published docs site.

### Internal-Generated Policy

- `docs/00-project/skills/global/.system/**` is classified as `internal-generated` and remains non-nav by design.
- For NCI references, canonical entrypoint is:
  - `docs/00-project/skills/local/nci-analysis/SKILL.md`
- `docs/00-project/skills/local/nci-analysis/references/**` is published in mkdocs nav under `Internal / Extended -> Skills -> Local Skills`.
