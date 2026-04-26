# Сводка evidence: project-and-ai-doc-drift

Дата: 2026-03-21
Статус: ребейзлайнено под текущее состояние

Review note (2026-03-27): included in the repo-wide evidence-pack sweep; see `docs/reports/evidence/project-evidence-rebaseline/06-status/EVIDENCE-PACK-REVIEW-2026-03-27.md` for wave status, retained-vs-reopened interpretation, and current review scope.

## Созданные объекты evidence

1. `EV-project-and-ai-doc-drift-project-map-now-points-to-live-config-loader-seams`
1. `EV-project-and-ai-doc-drift-config-bot-memory-now-points-to-live-config-loader-seams`
1. `EV-project-and-ai-doc-drift-local-py-code-bot-skill-now-explicitly-compatibility-only`
1. `EV-project-and-ai-doc-drift-practical-index-now-labels-py-code-bot-as-historical-compatibility`
1. `EV-project-and-ai-doc-drift-local-catalog-now-labels-py-code-bot-as-compatibility-profile`
1. `EV-project-and-ai-doc-drift-orchestration-now-explicitly-marks-changelog-as-non-normative`

## Проверка gate

Minimum evidence required: `5`

Collected: `6`

Статус gate: `PASSED`

## Сводка evidence

| ID                                                                                             | Claim Summary                                                                                                                             | Confidence |
| ---------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| EV-project-and-ai-doc-drift-project-map-now-points-to-live-config-loader-seams                 | The active project map now points readers to live config-loader seams instead of the removed infrastructure `config_loader.py` file.      | 0.99       |
| EV-project-and-ai-doc-drift-config-bot-memory-now-points-to-live-config-loader-seams           | The config-bot memory now points to the live runtime config-loader seam and the live infrastructure config package.                       | 0.99       |
| EV-project-and-ai-doc-drift-local-py-code-bot-skill-now-explicitly-compatibility-only          | The local `py-code-bot` skill mirror now presents itself as deprecated compatibility guidance rather than an active profile surface.      | 0.96       |
| EV-project-and-ai-doc-drift-practical-index-now-labels-py-code-bot-as-historical-compatibility | The practical skills index now labels `py-code-bot` as historical compatibility material instead of exposing it as a normal active skill. | 0.95       |
| EV-project-and-ai-doc-drift-local-catalog-now-labels-py-code-bot-as-compatibility-profile      | The local skills catalog now labels `py-code-bot` as a compatibility profile rather than an ordinary active profile entry.                | 0.95       |
| EV-project-and-ai-doc-drift-orchestration-now-explicitly-marks-changelog-as-non-normative      | The canonical orchestration file now explicitly marks historical changelog text as non-normative.                                         | 0.97       |

## Ключевые выводы

- The sampled project/AI doc surfaces now represent the current baseline for config-loader navigation and `py-code-bot` compatibility handling.
- `py-code-bot` no longer appears in these sampled files as a silent active-workflow contradiction; it is now exposed as explicit compatibility or historical material.
- The remaining question in this pillar is governance: whether deprecated compatibility surfaces should stay discoverable at all.
