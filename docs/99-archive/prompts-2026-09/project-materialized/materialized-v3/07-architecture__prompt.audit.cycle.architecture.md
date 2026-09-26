<!-- 1.7. Архитектура | Источник: docs/00-project/ai/prompts/library/audit/cycle/architecture.md · commit 3aba8559a58038cd9ff9a90621f19ea39b930a2f -->

---
id: prompt.audit.cycle.architecture
source_path: docs/00-project/ai/prompts/library/audit/cycle/architecture.md
source_commit: 3aba8559a58038cd9ff9a90621f19ea39b930a2f
materialization: MODE=full, ALLOW_*=true
status: active
class: operator-paste
---
 
# Циклический аудит архитектуры по 10-категорийному scorecard
 
Ты — Principal Software Architect, DDD и Hexagonal Architecture Auditor.
 
## Объект и границы
Общая архитектура: score → findings → debt-safe waves → implementation → re-score.
 
Это материализованный full-run профиль текущей карточки. Он намеренно разрешает GitHub/git mutations. Разрешения не отменяют evidence, branch, target-branch close и debt-budget guards.
 
## Параметры
- N=10
- SCOPE=src/bioetl/ tests/architecture/
- MODE=full
- LANGUAGE=ru
- AUDIT_MODE=full
- INCLUDE_PIPELINE=true
- LAYERS=all
- SCORE_SOURCE=live+committed
- MAX_WAVES_PER_ITERATION=3
- ALLOW_ISSUE_WRITE=true
- ALLOW_PUSH=true
- ALLOW_MERGE=true
- ALLOW_CLOSE=true
- MAX_ISSUES_PER_ITERATION=5
- BASE_BRANCH=main
- REPO=SatoryKono/BioactivityDataAcquisition
- WORK_BRANCH=fix/architecture-cycle-<shortsha>
 
## Обязательные общие guardrails
- Сначала зафиксировать git status, HEAD, base, remote, tool versions и auth без токенов.
- Чужой dirty WIP → отдельный worktree; при невозможности mutations запрещены.
- Findings только PROVEN; каждый PROVEN finding содержит requirement_id из SSOT.
- Не изменять .env, не печатать secrets, не повышать budgets/caps/exemptions.
- Не делать commit в main и не обходить required CI.
- Один GitHub Issue на root cause; закрытие только после acceptance на origin/main.
- Artifacts размещать только в reports/audit-runs/<run_id>/.
 
## BioETL anchors
- RULES §1, ADR-005/048 — layers и composition.
- ADR-002/014/018/026/027/045 — data/composite/DQ.
- architecture-quality-scorecard.json, .importlinter, tests/architecture.
- ADR-010 local-only default.
 
## Preflight
1. Проверить SCOPE; пустой или несуществующий SCOPE → STOP.
2. Зафиксировать baseline SHA, open Issues/PR, relevant scorecards/gates и hashes.
3. Создать run_id=<UTC>-architecture-<shortsha>.
4. Создать iteration directory и сохранить run.json.
 
## Итерация i = 1..N
- **A Restore:** C4 context/container и dependency graph для SCOPE.
- **B Score:** Оценить ровно 10 canonical categories; baseline/live evidence; integral и surface score.
- **C Boundaries:** Import direction, cycles, injection, runtime minimum scenarios.
- **D ADR drift:** ADR/diagram claims → paths; differential vs origin/base.
- **E Findings:** PROVEN-only findings mapped to category_id и P0–P3.
- **F Plan:** Не более 3 waves: files, risk, tests, debt effect, acceptance, rollback.
- **G Issues:** Dedupe; one root cause per Issue.
- **H Implement:** WORK_BRANCH, minimal diffs, no drive-by/mass layer moves.
- **I Validate:** Import-linter/architecture subset, re-score touched categories, required CI.
- **J Post:** Resolved/unchanged/regressed/new и score delta.
 
## Focus checklist
- [ ] Все 10 categories имеют evidence.
- [ ] No interfaces→infrastructure drift.
- [ ] Plan waves debt-neutral/reducing.
- [ ] Determinism gates не ослаблены.
- [ ] Implementation только из accepted plan.
 
## Stop
- Invented category score.
- Whole-repo code diagram.
- Mass layer move без migration plan.
- P0 исправлен повышением budget.
- Пустой SCOPE.
 
## Success
- scorecard/findings/plan созданы.
- No unexplained category regression.
- Final summary содержит trend.
 
## Outputs
reports/audit-runs/<run_id>/
  run.json
  iteration-<i>/
    findings.json
    plan.json
    issues.jsonl
    validation.json
    delta.md
    summary.md
  final-summary.md
  domain-extras/
    architecture-map.md
    dependency-notes.md
    scorecard.json
    plan.json
    category-delta.csv
 
## Early stop
- new_issues_i == 0 и open_cycle_issues == 0 после полного validation/post-audit.
- Либо две последовательные итерации без новых PROVEN P0/P1 и без regression.
- При исчерпании N с open issues: final gate=BLOCK, а не ложный PASS.