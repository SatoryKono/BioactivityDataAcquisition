4. ПЛАН ДОРАБОТКИ И РАСШИРЕНИЯ СИСТЕМЫ ПРОМПТОВ
4.1. Целевая структура репозитория
docs/00-project/ai/prompts/
  fragments/
    cyclic-kernel-v3.md
    evidence-contract-v3.md
    issue-state-machine-v3.md
  overlays/
    <domain>.yaml
  profiles/
    audit-readonly.yaml
    full-write.yaml
    differential.yaml
  _schema/
    kernel.schema.json
    domain-overlay.schema.json
    execution-profile.schema.json
    finding-v3.schema.json
    ledger-event.schema.json
  generated/
    <domain>/<profile>.md
  compatibility/
    <legacy-prompt-id>.md
scripts/ai/prompts/
  compile.py
  lint.py
  verify.py
  diff.py
tests/prompts/
  unit/
  contract/
  golden/
  integration/

4.2. Этапы реализации

4.3. Автоматические проверки prompt system
1. schema_valid_all_overlays: все 24 overlays соответствуют domain-overlay.schema.json.
2. guard_non_weakening: overlay/profile не может отключить secret, budget, branch, CI или evidence guards.
3. deterministic_compile: одинаковые inputs дают идентичный rendered text и prompt_sha8.
4. legacy_id_parity: legacy ID рендерит тот же domain method через wrapper.
5. no_controller_duplication: overlays не содержат Audit/Plan/Issue/Fix orchestration sections.
6. full_profile_explicit: ALLOW_*=true допустим только в named execution profile или explicit CLI params.
7. finding_fingerprint_stability: перефразирование claim не меняет fingerprint при том же root cause/path set.
8. issue_fsm_contract: create/reuse/defer/blocked/close переходы валидны.
9. target_branch_close_gate: PR-head без merge не считается resolved по умолчанию.
10. resume_idempotency: повтор stage после crash не создаёт duplicate Issue/branch/PR.
11. output_schema_contract: run/baseline/findings/plan/issues/validation/ledger files валидны.
12. scope_cap_enforcement: leaf > cap требует split.
13. budget_non_growth: prompt plan, generated payload и patch не повышают caps/exemptions.
14. source_reference_exists: overlay SSOT/SCOPE paths разрешаются или явно optional.
15. golden_render_24xprofiles: snapshots для read-only/full/differential profiles.
4.4. Расширение предметного покрытия

4.5. Метрики успеха миграции

4.6. Риски и меры
