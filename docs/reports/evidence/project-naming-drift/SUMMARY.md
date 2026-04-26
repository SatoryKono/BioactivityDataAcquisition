# Сводка evidence: project-naming-drift

Дата: 2026-03-21
Статус: актуализировано

Review note (2026-03-27): included in the repo-wide evidence-pack sweep; see `docs/reports/evidence/project-evidence-rebaseline/06-status/EVIDENCE-PACK-REVIEW-2026-03-27.md` for wave status, retained-vs-reopened interpretation, and current review scope.

## Статус пакета

- `ORCHESTRATION.md` существует и определяет naming-drift evidence pass.
- Cross-shard synthesis находится в [CROSS-SYNTHESIS-project-naming-drift.md](./03-synthesis/CROSS-SYNTHESIS-project-naming-drift.md).
- Слои решений и рисков находятся в [DECISIONS.yaml](./04-decisions/DECISIONS.yaml) и [RISKS.yaml](./05-risks/RISKS.yaml).
- Активный implementation follow-up отслеживается в [NAMING-CLEANUP-SHORTLIST.md](./06-backlog/NAMING-CLEANUP-SHORTLIST.md).

## Текущая интерпретация

- Naming drift реален, но после current-state rebaseline он остаётся концентрированным, а не repo-wide.
- Самые ценные сигналы кластеризуются в orchestration, composition, compatibility seams и naming-family boundaries.
- Самый повторяющийся паттерн — это vocabulary split для одной и той же роли, а не разрозненные one-off плохие имена.
- Function и variable naming drift создают самый явный локальный риск для readability и correctness reasoning.
- Compatibility и helper/file-name drift по умолчанию принимаются как monitoring debt, если только их public surface не продолжает расти.

## Текущая позиция по решениям

- Проект не запускает repo-wide renaming wave.
- Follow-up намеренно строится вокруг shortlist.
- Function и variable semantics имеют приоритет перед broad object/file convergence.
- Исторические compatibility names допускаются, пока они не продолжают распространяться.
- Current baseline отражает documentation remediation wave от 2026-03-20 и naming rebaseline pass от 2026-03-21.

## Ключевые ссылки

- [CROSS-SYNTHESIS-project-naming-drift.md](./03-synthesis/CROSS-SYNTHESIS-project-naming-drift.md)
- [Сводка решений](./04-decisions/SUMMARY.md)
- [DECISIONS.yaml](./04-decisions/DECISIONS.yaml)
- [RISKS.yaml](./05-risks/RISKS.yaml)
- [NAMING-CLEANUP-SHORTLIST.md](./06-backlog/NAMING-CLEANUP-SHORTLIST.md)
