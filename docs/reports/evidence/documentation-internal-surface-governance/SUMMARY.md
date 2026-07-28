# Сводка evidence: documentation-internal-surface-governance

Дата: 2026-03-27
Статус: refreshed after publication-boundary realignment

Review note (2026-03-27): included in the repo-wide evidence-pack sweep; see `docs/reports/evidence/project-evidence-rebaseline/06-status/EVIDENCE-PACK-REVIEW-2026-03-27.md` for wave status, retained-vs-reopened interpretation, and current review scope.

> Это summary — repo-only evidence layer для publication/discoverability
> решений вокруг внутренних documentation surfaces.
> Для canonical doc policy и active publication guardrails приоритет остаётся у
> `docs/00-project/governance/06-doc-publication-policy.md`,
> `docs/00-project/governance/07-doc-nav-policy.md`,
> `mkdocs.yml` и doc guard scripts under `scripts/docs/`.
>
> Freshness note: the 2026-03-23 snapshot captured a broader
> `internal-published` interpretation for `plans/**` and `reports/**`.
> The 2026-03-27 refresh records the current stricter `published` vs
> `repo-only` split and should be treated as the active interpretation.

## Выходы пакета

- [01-pillars/PILLARS.md](01-pillars/PILLARS.md)
- [02-evidence/internal-surface-governance/RAW-documentation-internal-surface-governance-2026-03-23.md](02-evidence/internal-surface-governance/RAW-documentation-internal-surface-governance-2026-03-23.md)
- [02-evidence/internal-surface-governance/RAW-documentation-internal-surface-governance-2026-03-27.md](02-evidence/internal-surface-governance/RAW-documentation-internal-surface-governance-2026-03-27.md)
- [03-synthesis/CROSS-SYNTHESIS.md](03-synthesis/CROSS-SYNTHESIS.md)
- [04-decisions/DECISIONS.yaml](04-decisions/DECISIONS.yaml)
- [05-risks/RISKS.yaml](05-risks/RISKS.yaml)

## Проверка gate

- `internal-surface-governance`: `10/5` semantic evidence objects, `PASSED`

Всего семантических объектов evidence: `10`

Общий результат: `PASS`

## Главные выводы

- Current documentation state still does not justify a new factual-sync wave: doc guards are green, drift checks report no drift, and strict MkDocs build succeeds on the refreshed tree.
- `docs/00-project/ai/README.md` still works as a coherent top-level AI surface map, but the active model now treats it as a curated repository-path entrypoint rather than a nav candidate that must be promoted immediately.
- The active publication model is no longer a broad `internal-published` surface for `plans/**` and `reports/**`; those clusters are now explicitly governed as `repo-only` reference surfaces.
- Discoverability is preserved through the published project hub, which points readers to repository paths for `plans/`, `reports/`, and the AI surface.
- Experimental deployment docs now match the helper script's registry/tag override model, which is a concrete example of current doc-code synchronization rather than prose-only cleanup.
- The remaining publication noise is mostly intentional excluded-surface information, not evidence of broken governance.
- Mixed RU/EN wording still exists, but current evidence supports treating it as readability debt rather than a governance or correctness defect.

## Интерпретация

Evidence supports a narrower and more explicit governance posture:

- keep the current index-first AI surface discoverability model for now;
- keep `plans/**` and `reports/**` as repo-only reference surfaces and point to
  them from published docs via repository paths or curated summaries;
- keep factual synchronization in the guard layer while the current green
  baseline holds;
- treat RU/EN normalization as opportunistic readability work, not as an
  immediate remediation wave.

## Интерпретация верхнего уровня

- Cross-shard interpretation lives in [03-synthesis/CROSS-SYNTHESIS.md](03-synthesis/CROSS-SYNTHESIS.md).
- Accepted posture is recorded in [04-decisions/DECISIONS.yaml](04-decisions/DECISIONS.yaml).
- Active governance risks are recorded in [05-risks/RISKS.yaml](05-risks/RISKS.yaml).
