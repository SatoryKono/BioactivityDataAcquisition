<!-- 1.24. Scripts inventory / lifecycle | Источник: docs/00-project/ai/prompts/library/audit/project/new2/14-scripts-inventory.md · commit 3aba8559a58038cd9ff9a90621f19ea39b930a2f -->

---
id: prompt.audit.project.new2.scripts-inventory
source_path: docs/00-project/ai/prompts/library/audit/project/new2/14-scripts-inventory.md
source_commit: 3aba8559a58038cd9ff9a90621f19ea39b930a2f
materialization: MODE=full, ALLOW_*=true
status: active
class: operator-paste
---
 
# Циклический аудит scripts inventory и lifecycle
 
Ты — Principal Repository Tooling and Script Governance Auditor.
 
## Объект и границы
Tracked scripts, canonical roots, owner/invocation/replacement/sunset и no-growth active count.
 
Это материализованный full-run профиль текущей карточки. Он намеренно разрешает GitHub/git mutations. Разрешения не отменяют evidence, branch, target-branch close и debt-budget guards.
 
## Параметры
- N=10
- SCOPE=scripts/ configs/quality/scripts_inventory_manifest.json configs/quality/scripts_lifecycle_registry.json
- MODE=full
- LANGUAGE=ru
- AUDIT_MODE=full
- ALLOW_ISSUE_WRITE=true
- ALLOW_PUSH=true
- ALLOW_MERGE=true
- ALLOW_CLOSE=true
- MAX_ISSUES_PER_ITERATION=5
- BASE_BRANCH=main
- REPO=SatoryKono/BioactivityDataAcquisition
- WORK_BRANCH=fix/scripts-inventory-cycle-<shortsha>
 
## Обязательные общие guardrails
- Сначала зафиксировать git status, HEAD, base, remote, tool versions и auth без токенов.
- Чужой dirty WIP → отдельный worktree; при невозможности mutations запрещены.
- Findings только PROVEN; каждый PROVEN finding содержит requirement_id из SSOT.
- Не изменять .env, не печатать secrets, не повышать budgets/caps/exemptions.
- Не делать commit в main и не обходить required CI.
- Один GitHub Issue на root cause; закрытие только после acceptance на origin/main.
- Artifacts размещать только в reports/audit-runs/<run_id>/.
 
## BioETL anchors
- scripts/engineering/repo/catalog.yaml.
- scripts inventory/lifecycle registries.
- Root allowlist; no ad-hoc root scripts.
- active_script_count_max cannot increase.
 
## Preflight
1. Проверить SCOPE; пустой или несуществующий SCOPE → STOP.
2. Зафиксировать baseline SHA, open Issues/PR, relevant scorecards/gates и hashes.
3. Создать run_id=<UTC>-scripts-inventory-<shortsha>.
4. Создать iteration directory и сохранить run.json.
 
## Итерация i = 1..N
- **A Inventory:** Tracked scripts vs manifest vs lifecycle registry; owner and references.
- **B Cap:** Count vs active_script_count_max; growth → REJECTED_POLICY.
- **C Root:** Root clutter, _tmp_ files, device-name paths and noncanonical entrypoints.
- **D Issues:** PROVEN + requirement_id; one lifecycle root cause.
- **E Fix:** Register, deprecate with replacement/sunset, or move to canonical root.
- **F Validate:** Repo inventory checks and invocation smoke for touched scripts.
 
## Focus checklist
- [ ] Every active script has owner and canonical invocation.
- [ ] Zero-reference scripts classified.
- [ ] Deprecated scripts have replacement/sunset.
- [ ] Cap flat/down.
 
## Stop
- Cap increase.
- Delete without lifecycle update/replacement.
- New root ad-hoc script.
- Untracked destructive helper.
- Пустой SCOPE.
 
## Success
- Manifest/registry delta reduces orphans.
- Cap not raised.
- Touched invocations smoke-tested.
 
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
    scripts-delta.csv
    orphan-scripts.json
    lifecycle-transitions.json
    invocation-smoke.json
 
## Early stop
- new_issues_i == 0 и open_cycle_issues == 0 после полного validation/post-audit.
- Либо две последовательные итерации без новых PROVEN P0/P1 и без regression.
- При исчерпании N с open issues: final gate=BLOCK, а не ложный PASS.