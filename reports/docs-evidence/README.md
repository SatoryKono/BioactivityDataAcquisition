# docs-evidence (relocated bulk evidence)

**Status:** historical / working evidence surface
**Relocated:** 2026-07-28 (DOC-GOV-01 / GitHub #6873)
**Former path:** `docs/reports/evidence/**` (bulk packs)

## Purpose

This tree holds research evidence packs moved out of the published
documentation surface so that `docs/` search and MkDocs stay focused on SSOT
(RULES, ADRs, contracts, runbooks, active guides).

## Authority

- **Non-normative.** Code, configs, ADRs, and active docs win on conflict.
- Curated governance manifests that still participate in freshness checks remain
  under `docs/reports/evidence/` (thin surface).
- Prefer new evidence under `reports/{LLM}/` or this tree; never reintroduce
  multi-MB dumps into `docs/reports/`.

## Retention

- Keep until a retention review archives or deletes individual packs.
- Safe to omit from clone-critical workflows; not required for runtime.
- Do not wire these packs into MkDocs navigation.

## Related

- Thin curated index: `docs/reports/evidence/INDEX.md`
- Reports taxonomy: `reports/README.md`
- Issue: https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6873
