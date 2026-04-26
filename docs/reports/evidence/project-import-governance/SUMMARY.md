# Сводка evidence: project-import-governance

Дата: 2026-03-23
Статус: актуализировано под текущий verify baseline

Review note (2026-03-27): included in the repo-wide evidence-pack sweep; see `docs/reports/evidence/project-evidence-rebaseline/06-status/EVIDENCE-PACK-REVIEW-2026-03-27.md` for wave status, retained-vs-reopened interpretation, and current review scope.

> Это summary — repo-only evidence layer для import-governance
> интерпретации и sequencing. Для canonical import policy и active architectural
> guardrails приоритет остаётся у `docs/00-project/RULES.md`,
> `docs/02-architecture/`, `.importlinter` и architecture tests.

Примечание о rebaseline: текущее состояние репозитория по-прежнему соответствует
интерпретации `managed governance with localized hotspots`, а свежий `RF-011`
дополнительно подтвердил зелёный baseline для generated-artifact checks и import
governance guardrails.

## Выходы shard-ов

- [import-governance-state/SUMMARY.md](import-governance-state/SUMMARY.md)
- [cyclic-and-topology-risk/SUMMARY.md](cyclic-and-topology-risk/SUMMARY.md)
- [facade-and-private-import-surface/SUMMARY.md](facade-and-private-import-surface/SUMMARY.md)
- [03-synthesis/CROSS-SYNTHESIS.md](03-synthesis/CROSS-SYNTHESIS.md)
- [04-decisions/DECISIONS.yaml](04-decisions/DECISIONS.yaml)
- [05-risks/RISKS.yaml](05-risks/RISKS.yaml)

## Проверка gate

- `import-governance-state`: `7/5` semantic evidence objects, `PASSED`
- `cyclic-and-topology-risk`: `12/5` semantic evidence objects, `PASSED`
- `facade-and-private-import-surface`: `12/5` semantic evidence objects, `PASSED`

Всего семантических объектов evidence: `31`

Общий результат: `PASS`

## Главные выводы

- Import governance in the repo is explicit and executable. `.importlinter`, architecture tests, facade-size rules, private-module guards, and generated dependency artifacts collectively form a real enforcement surface.
- The repo does not currently support a broad forbidden-import or widespread topology-breakage narrative. The generated dependency map still publishes `0` layer policy violations.
- Cyclic-import pressure exists, but it is localized in a small number of SCC clusters, especially around provider-registry/datasource resolution and pipeline factory assembly.
- The broadest-looking import surfaces are largely intentional and governed. Ports enter through a single facade, compatibility surfaces are inventory-backed, and cross-owner private imports are forbidden.
- Текущие hygiene-сигналы уже уже, чем в раннем проходе:
  - compatibility snapshot и measured-registry checks зелёные после YAML SSOT refresh и повторно подтверждены в `RF-011`
  - dependency-map `--check` зелёный на актуальном дереве после последней регенерации артефактов
  - `ruff F401` остаётся зелёным across `src` и `tests`
  - активный риск смещён от live import-governance drift к локализованному topology pressure и watchlist SCC clusters

## Интерпретация

Evidence supports a `managed-governance with localized topology hotspots`
narrative. Import policy is strong, facade/private import surfaces are actively
constrained, and the remaining risks are concentrated in specific SCC clusters
and composition/provider assembly seams rather than in repo-wide architectural
breakdown, generated-artifact freshness drift, or live governance regression.

## Рекомендуемая позиция

- Treat the observed SCC clusters as watchlist seams for future refactors, especially in composition/provider wiring and pipeline factory assembly.
- Treat facade and compatibility layers as governed public surfaces unless a separate migration plan changes that policy.

## Интерпретация верхнего уровня

- A formal cross-shard interpretation now lives in [03-synthesis/CROSS-SYNTHESIS.md](03-synthesis/CROSS-SYNTHESIS.md).
- Accepted posture is recorded in [04-decisions/DECISIONS.yaml](04-decisions/DECISIONS.yaml).
- Active governance risks are recorded in [05-risks/RISKS.yaml](05-risks/RISKS.yaml).
