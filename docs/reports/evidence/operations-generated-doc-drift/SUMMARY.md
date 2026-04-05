# Сводка evidence: operations-generated-doc-drift

Дата: 2026-03-26
Статус: refreshed after export cleanup

Review note (2026-03-27): included in the repo-wide evidence-pack sweep; see `docs/reports/evidence/project-evidence-rebaseline/06-status/EVIDENCE-PACK-REVIEW-2026-03-27.md` for wave status, retained-vs-reopened interpretation, and current review scope.

Примечание о rebaseline: generated dependency map и compatibility-adjacent
artifacts на текущем дереве свежие и проходят `--check`; этот pack по-прежнему
описывает derivative-document risk и reader-confusion risk, а не текущий red
status docs-as-code.

Примечание о 2026-03-26 follow-up: tracked merged export больше не хранится в
git по умолчанию. Экспорт-специфические findings из раннего RAW now read as
historical trigger evidence, а live residual risk смещается к on-demand export
generation, generated maps и historical verification artifacts.

## Созданные объекты evidence

1. `EV-operations-generated-doc-drift-export-still-preserves-stale-pipelineservices-sections`
1. `EV-operations-generated-doc-drift-export-still-carries-old-manager-labels`
1. `EV-operations-generated-doc-drift-generated-module-dependency-map-is-derivative-not-active-policy`
1. `EV-operations-generated-doc-drift-vcr-verification-artifact-still-lists-duplicate-and-orphan-cassettes`
1. `EV-operations-generated-doc-drift-vcr-verification-artifact-preserves-stale-field-anomaly-names`
1. `EV-operations-generated-doc-drift-tracked-merged-export-retired-from-repo-surface`

## Проверка gate

Minimum evidence required: `5`

Collected: `6`

Статус gate: `PASSED`

## Ключевые выводы

- The previously tracked merged export has been retired from the default repo surface; the old export-specific stale-name findings now act as historical trigger evidence rather than current on-disk drift.
- The generated dependency map remains a derived snapshot, not a policy document; it should not be promoted to active truth even though the current artifact itself is freshly regenerated and green.
- The historical VCR verification artifact remains useful as dated evidence, but its cassette inventory and field-anomaly sections are stale relative to the current tree and current canonical names.
- Repo policy now treats merged exports as generated convenience artifacts that may exist on demand without being committed to git by default.

## Gaps

- I sampled the highest-risk generated and operations surfaces, not every document under `docs/05-operations/`.
- Export-specific findings from the 2026-03-20 raw snapshot are now historical-trigger evidence because the tracked merged export surface has been retired from the default tree.
