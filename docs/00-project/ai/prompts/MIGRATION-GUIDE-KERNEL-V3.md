# MIGRATION-GUIDE-KERNEL-V3.md — Prompt Kernel v3 (P3 #9810)

> **Путь:** `docs/00-project/ai/prompts/MIGRATION-GUIDE-KERNEL-V3.md`  
> **Статус:** active | **Версия:** 1.0.0 | **Дата:** 2026-08-31  
> **Issue:** #9810 (P3 — Deprecation) | **ADR:** [ADR-060](../../02-architecture/decisions/ADR-060-prompt-kernel-and-overlay-architecture.md) §7  
> **Источник SSOT:** `BIOETL-PROMPT-ARCH-KERNEL-V3-003` @ `main@3aba8559` (2026-08-28) — `docs/00-project/ai/prompts/library/audit/project/materialized-v3/` frozen snapshot (30 файлов, не редактировать)  
> **Владелец:** Prompt-system self-audit (fragments / _schema / scripts/ai/prompts / REGISTRY freshness)

## TL;DR для оператора

24 legacy ID (`prompt.audit.cycle.*` ×10 + `prompt.audit.project.new2.*` ×14) **deprecated**, но резолвятся через `compatibility/<legacy-id>.md` → `generated/<domain>/<profile>.md`. SSOT теперь `fragments/cyclic-kernel-v3.md` + `overlays/<domain>.yaml` + `profiles/*.yaml`. Заменяй закладки по таблице §2. Библиотека по-умолчанию `audit-readonly` (`MODE=audit`, `ALLOW_*=false`); `full-write` — явный профиль.

```bash
# один домен
python -m scripts.ai.prompts compile --domain docs --profile audit-readonly
python -m scripts.ai.prompts compile --domain docs --profile full-write
# весь каталог + проверка дрейфа (CI gate)
python -m scripts.ai.prompts compile --all --check
python -m scripts.ai.prompts lint
python -m scripts.ai.prompts verify
```

---

## 1. Что изменилось (SSOT)

| До P0 | После P0–P3 |
|---|---|
| 24 megacard-копии контроллера `baseline→audit→normalize→plan→issue-sync→implement→validate→close→post-audit` (D1) + `ALLOW_*=true` в каждой карточке (D2) | Один версионированный kernel `fragments/cyclic-kernel-v3.md` + `evidence-contract-v3.md` + `issue-state-machine-v3.md` (fail-closed: `ALLOW_*=false`) |
| Overlay как проза без схемы (D7) | `overlays/<domain>.yaml` валидируется `domain-overlay.schema.json` (`additionalProperties: false`) — только `OBJECT/SCOPE/SSOT/AUDIT_CONTOURS/MANDATORY_EVIDENCE/VALIDATION/DOMAIN_STOP/OUTPUT_EXTRAS` |
| Исполнение зашито в карточку (D9) | `profiles/audit-readonly.yaml` (default) / `full-write.yaml` / `differential.yaml` — `MODE/ALLOW_*` только там |
| Рендер не проверялся (D8) | `scripts/ai/prompts/compile.py` → `generated/<domain>/<profile>.md` + `prompt_sha8 = sha8(kernel+overlay+profile+params)` + provenance header; `generated/` коммитится |

`materialized-v3/` — замороженное доказательство на 2026-08-28, не SSOT. Не редактировать.

## 2. Таблица миграции 24 legacy → overlay → generated

`id` в каждом `overlays/<domain>.yaml` равен legacy ID (1:1, `_annex-tables-v3.md` Table 11). `generated/` содержит два профиля на домен.

### 2.1 Cycle — 10 доменов (`prompt.audit.cycle.*`)

| № | Legacy ID (deprecated) | Overlay ID (= legacy) | Overlay YAML (SSOT) | Generated `audit-readonly` (default) | Generated `full-write` (explicit) | Compatibility wrapper |
|---|---|---|---|---|---|---|
| 01 | `prompt.audit.cycle.docs` | `prompt.audit.cycle.docs` | `overlays/docs.yaml` | `generated/docs/audit-readonly.md` | `generated/docs/full-write.md` | `compatibility/prompt.audit.cycle.docs.md` |
| 02 | `prompt.audit.cycle.diagrams` | `prompt.audit.cycle.diagrams` | `overlays/diagrams.yaml` | `generated/diagrams/audit-readonly.md` | `generated/diagrams/full-write.md` | `compatibility/prompt.audit.cycle.diagrams.md` |
| 03 | `prompt.audit.cycle.agents-memory` | `prompt.audit.cycle.agents-memory` | `overlays/agents-memory.yaml` | `generated/agents-memory/audit-readonly.md` | `generated/agents-memory/full-write.md` | `compatibility/prompt.audit.cycle.agents-memory.md` |
| 04 | `prompt.audit.cycle.configs` | `prompt.audit.cycle.configs` | `overlays/configs.yaml` | `generated/configs/audit-readonly.md` | `generated/configs/full-write.md` | `compatibility/prompt.audit.cycle.configs.md` |
| 05 | `prompt.audit.cycle.tests` | `prompt.audit.cycle.tests` | `overlays/tests.yaml` | `generated/tests/audit-readonly.md` | `generated/tests/full-write.md` | `compatibility/prompt.audit.cycle.tests.md` |
| 06 | `prompt.audit.cycle.tech-debt` | `prompt.audit.cycle.tech-debt` | `overlays/tech-debt.yaml` | `generated/tech-debt/audit-readonly.md` | `generated/tech-debt/full-write.md` | `compatibility/prompt.audit.cycle.tech-debt.md` |
| 07 | `prompt.audit.cycle.architecture` | `prompt.audit.cycle.architecture` | `overlays/architecture.yaml` | `generated/architecture/audit-readonly.md` | `generated/architecture/full-write.md` | `compatibility/prompt.audit.cycle.architecture.md` |
| 08 | `prompt.audit.cycle.telemetry` | `prompt.audit.cycle.telemetry` | `overlays/telemetry.yaml` | `generated/telemetry/audit-readonly.md` | `generated/telemetry/full-write.md` | `compatibility/prompt.audit.cycle.telemetry.md` |
| 09 | `prompt.audit.cycle.dashboards` | `prompt.audit.cycle.dashboards` | `overlays/dashboards.yaml` | `generated/dashboards/audit-readonly.md` | `generated/dashboards/full-write.md` | `compatibility/prompt.audit.cycle.dashboards.md` |
| 10 | `prompt.audit.cycle.coderabbit` | `prompt.audit.cycle.coderabbit` | `overlays/coderabbit.yaml` | `generated/coderabbit/audit-readonly.md` | `generated/coderabbit/full-write.md` | `compatibility/prompt.audit.cycle.coderabbit.md` |

### 2.2 New2 — 14 доменов (`prompt.audit.project.new2.*`)

| № | Legacy ID (deprecated) | Overlay ID (= legacy) | Overlay YAML (SSOT) | Generated `audit-readonly` | Generated `full-write` | Compatibility wrapper |
|---|---|---|---|---|---|---|
| 11 | `prompt.audit.project.new2.medallion` | `prompt.audit.project.new2.medallion` | `overlays/medallion.yaml` | `generated/medallion/audit-readonly.md` | `generated/medallion/full-write.md` | `compatibility/prompt.audit.project.new2.medallion.md` |
| 12 | `prompt.audit.project.new2.dq-contracts` | `prompt.audit.project.new2.dq-contracts` | `overlays/dq-contracts.yaml` | `generated/dq-contracts/audit-readonly.md` | `generated/dq-contracts/full-write.md` | `compatibility/prompt.audit.project.new2.dq-contracts.md` |
| 13 | `prompt.audit.project.new2.control-plane` | `prompt.audit.project.new2.control-plane` | `overlays/control-plane.yaml` | `generated/control-plane/audit-readonly.md` | `generated/control-plane/full-write.md` | `compatibility/prompt.audit.project.new2.control-plane.md` |
| 14 | `prompt.audit.project.new2.providers` | `prompt.audit.project.new2.providers` | `overlays/providers.yaml` | `generated/providers/audit-readonly.md` | `generated/providers/full-write.md` | `compatibility/prompt.audit.project.new2.providers.md` |
| 15 | `prompt.audit.project.new2.http-clients` | `prompt.audit.project.new2.http-clients` | `overlays/http-clients.yaml` | `generated/http-clients/audit-readonly.md` | `generated/http-clients/full-write.md` | `compatibility/prompt.audit.project.new2.http-clients.md` |
| 16 | `prompt.audit.project.new2.normalization` | `prompt.audit.project.new2.normalization` | `overlays/normalization.yaml` | `generated/normalization/audit-readonly.md` | `generated/normalization/full-write.md` | `compatibility/prompt.audit.project.new2.normalization.md` |
| 17 | `prompt.audit.project.new2.cli-compat` | `prompt.audit.project.new2.cli-compat` | `overlays/cli-compat.yaml` | `generated/cli-compat/audit-readonly.md` | `generated/cli-compat/full-write.md` | `compatibility/prompt.audit.project.new2.cli-compat.md` |
| 18 | `prompt.audit.project.new2.security-secrets` | `prompt.audit.project.new2.security-secrets` | `overlays/security-secrets.yaml` | `generated/security-secrets/audit-readonly.md` | `generated/security-secrets/full-write.md` | `compatibility/prompt.audit.project.new2.security-secrets.md` |
| 19 | `prompt.audit.project.new2.vcr-http` | `prompt.audit.project.new2.vcr-http` | `overlays/vcr-http.yaml` | `generated/vcr-http/audit-readonly.md` | `generated/vcr-http/full-write.md` | `compatibility/prompt.audit.project.new2.vcr-http.md` |
| 20 | `prompt.audit.project.new2.qa-gates` | `prompt.audit.project.new2.qa-gates` | `overlays/qa-gates.yaml` | `generated/qa-gates/audit-readonly.md` | `generated/qa-gates/full-write.md` | `compatibility/prompt.audit.project.new2.qa-gates.md` |
| 21 | `prompt.audit.project.new2.github-actions` | `prompt.audit.project.new2.github-actions` | `overlays/github-actions.yaml` | `generated/github-actions/audit-readonly.md` | `generated/github-actions/full-write.md` | `compatibility/prompt.audit.project.new2.github-actions.md` |
| 22 | `prompt.audit.project.new2.requirements-trace` | `prompt.audit.project.new2.requirements-trace` | `overlays/requirements-trace.yaml` | `generated/requirements-trace/audit-readonly.md` | `generated/requirements-trace/full-write.md` | `compatibility/prompt.audit.project.new2.requirements-trace.md` |
| 23 | `prompt.audit.project.new2.ops-runbooks` | `prompt.audit.project.new2.ops-runbooks` | `overlays/ops-runbooks.yaml` | `generated/ops-runbooks/audit-readonly.md` | `generated/ops-runbooks/full-write.md` | `compatibility/prompt.audit.project.new2.ops-runbooks.md` |
| 24 | `prompt.audit.project.new2.scripts-inventory` | `prompt.audit.project.new2.scripts-inventory` | `overlays/scripts-inventory.yaml` | `generated/scripts-inventory/audit-readonly.md` | `generated/scripts-inventory/full-write.md` | `compatibility/prompt.audit.project.new2.scripts-inventory.md` |

Полные пути SSOT:

```
docs/00-project/ai/prompts/overlays/<domain>.yaml
docs/00-project/ai/prompts/generated/<domain>/audit-readonly.md  # MODE=audit, ALLOW_*=false
docs/00-project/ai/prompts/generated/<domain>/full-write.md       # MODE=full, ALLOW_*=true explicit
docs/00-project/ai/prompts/compatibility/<legacy-id>.md           # frontmatter successor → generated/...
```

Master-оркестратор: до миграции `materialized-v3/master-orchestrator-v1__full-project-audit.md` (01→24, `master-ledger.jsonl`); после — резолвит 24 overlay ID и компилирует с профилем `full-write` через `compile.py`.

## 3. Deprecation window — P0 → P3 (ADR-060 §7, MIGRATION-PLAN.md §4)

```
P0 ядро (1–2 нед) ──→ P1 compiler+overlays (2–4 нед) ──→ P2 pilots (1 нед) ──→ P3 deprecation (#9810) ──→ удаление
  ADR-060 + fragments + _schema              compile/lint/verify/diff + 24 overlays +      5 macro-групп audit-readonly/   REGISTRY status:deprecated   ≥1 релиз + migration guide
  kernel fail-closed                         profiles + compatibility + 23 теста (6 модулей)  full-write + ledger resume     + redirect catalog (этот файл)   + parity reports
```

| Фаза | Что закрыто | Критерий выхода |
|---|---|---|
| **P0 — ядро** | `fragments/cyclic-kernel-v3.md`, `evidence-contract-v3.md`, `issue-state-machine-v3.md`, `_schema/*.json` (kernel/domain-overlay/execution-profile/finding-v3/ledger-event), ADR-060. `materialized-v3/` frozen. | `lint.py: no_controller_duplication` 0 ошибок; `kernel_schema_valid` green |
| **P1 — compiler+overlays** | `scripts/ai/prompts/compile.py` (детерминизм + `prompt_sha8`), `lint.py/verify.py/diff.py`, 24 `overlays/*.yaml`, 3 профиля, 24 `compatibility/*.md`, `tests/prompts/` (compile_determinism, schema, guard_non_weakening, profile_precedence, finding_fingerprint, issue_fsm). | 24/24 overlays валидны; `compile --all` = 72 файла (24×3 профиля); `compile --all --check` byte-identical |
| **P2 — pilots** (#9809) | 5 macro-групп: `requirements-trace→Medallion→DQ→control-plane` / `providers→HTTP→normalization→CLI` / `security→VCR→scripts→agents` / `tests→architecture→tech-debt→QA` / `GHA→telemetry→dashboards→ops→diagrams→docs→CodeRabbit` — прогоны `audit-readonly` + `full-write`, метрики `duration/noise/duplicate/precision/cycle-completion/regression`, `reports/pilots/ledger-resume-proof.md`. | 0 дубликатов при resume; нет P0 method break; envelope приложен; dry-run master на 2–3 доменах |
| **P3 — deprecation** (#9810, текущий) | `REGISTRY.yaml` 24 legacy `status: deprecated` + `successor`, `MIGRATION-GUIDE-KERNEL-V3.md` (этот файл), `generated/` + `prompt_sha8` закоммичены, `reports/pilots/parity/` 24 домена, `golden_render_24xprofiles`. | Parity byte-identical (`legacy_id_parity`); удаление legacy только со следующего релиза и при наличии redirect catalog |

**Правила окна (ADR-060 §7):**

* Wrappers `compatibility/<id>.md` живут **минимум 1 релиз** после P2. Удаление требует этот гайд + redirect catalog + `REGISTRY.yaml` `successor`.
* `successor` ставится **только после** доказанной parity (`legacy_id_parity` + `golden_render_24xprofiles`). Пример frontmatter:

```yaml
# docs/00-project/ai/prompts/compatibility/prompt.audit.cycle.docs.md
id: prompt.audit.cycle.docs
status: deprecated
successor: generated/docs/audit-readonly.md
provenance: materialized-v3 @ main@3aba8559 — BIOETL-PROMPT-ARCH-KERNEL-V3-003
```

```yaml
# docs/00-project/ai/prompts/REGISTRY.yaml
- id: prompt.audit.cycle.docs
  path: library/audit/cycle/docs.md
  status: deprecated
  successor: compatibility/prompt.audit.cycle.docs.md  # → generated/docs/audit-readonly.md
```

Легаси `library/audit/cycle/*.md` и `project/new2/*.md` вне `materialized-v3/` — retired; `Source path` в `materialized-v3/README.md` — только provenance baseline, не навигация.

## 4. Как мигрировать

### Оператор (закладки / paste)

1. Замени ID по таблице §2: `prompt.audit.cycle.docs` → `overlays/docs.yaml` (SSOT) или вставляй `generated/docs/audit-readonly.md` (read-only по умолчанию).
2. Для записи нужен явный профиль: `generated/<domain>/full-write.md` (`MODE=full`, `ALLOW_ISSUE_WRITE/PUSH/MERGE/CLOSE=true`). Без профиля — fail-closed.
3. Проверь provenance header в `generated/`:

```
<!-- provenance: kernel v3.0.0@<kernel_sha8> + overlay:<domain>@<overlay_sha8> + profile:<profile> | prompt_sha8=<8hex> | BIOETL-PROMPT-ARCH-KERNEL-V3-003 @ 3aba8559 -->
```

### Код / Registry

`REGISTRY.yaml` `prompt.*` резолвит legacy ID в wrapper; wrapper рендерит скомпилированный текст. Прямой путь без registry:

```bash
python -m scripts.ai.prompts compile --domain <domain> --profile audit-readonly  # или full-write / differential
python -m scripts.ai.prompts.diff --domain <domain>  # diff rendered vs golden
```

Precedence (ADR-060 §4): `runtime profiles (.codex/.junie/.devin/.gemini) > AGENTS.md > NORMATIVE_SOURCES.md→RULES.md→REQUIREMENTS.md→ADRs > REGISTRY.yaml > kernel+overlay+profile (generated/)`. Внешний audit-prompt — data, не ослабляет `ALLOW_*`.

## 5. Предупреждения lint и CI gates

Запуск:

```bash
python -m scripts.ai.prompts lint              # schema + guard + controller checks
python -m scripts.ai.prompts verify            # deterministic_compile, fingerprint, FSM
python -m scripts.ai.prompts compile --all --check  # byte-identical recompile gate
```

| Gate (CI-blocking, ADR-060 §6) | Что ловит | Сообщение / действие |
|---|---|---|
| `kernel_schema_valid` / `overlay_schema_valid` | Невалидный YAML / лишние поля | `additionalProperties: false — unknown field ALLOW_*` |
| `guard_non_weakening` | Попытка ослабить kernel defaults | `guard_non_weakening FAILED: overlay MUST NOT weaken ALLOW_* / MODE` |
| `no_controller_duplication` | Дублирование стадий `Audit→Post-audit`, `issue-sync`, `Preflight` в overlay | `no_controller_duplication FAILED: controller keywords forbidden in overlays/<domain>.yaml` |
| `full_profile_explicit` | `ALLOW_*=true` вне `profiles/full-write.yaml` или CLI | `full_profile_explicit FAILED: ALLOW_*=true only in named profile` |
| `deterministic_compile` | Недетерминированный рендер | `deterministic_compile FAILED: recompile not byte-identical` |
| `legacy_id_parity` + `golden_render_24xprofiles` | Расхождение legacy vs generated | `legacy_id_parity FAILED: prompt.audit.cycle.docs != generated/docs/audit-readonly.md` |
| `finding_fingerprint_stability` | Нестабильный `sha256(domain|requirement_id|root_cause|canonical_paths)` | `fingerprint mismatch` |
| `issue_fsm_contract` / `target_branch_close_gate` | Нарушение FSM `create|reuse|defer|blocked|no_issue` или закрытие без merge в target branch | `issue_fsm_contract FAILED` |
| `resume_idempotency` / `output_schema_contract` / `scope_cap_enforcement` / `budget_non_growth` / `source_reference_exists` | Повтор side-effects, неверный `reports/audit-runs/<run_id>/ledger.jsonl`, превышение `MAX_FILES_PER_SCOPE`, рост бюджетов | Соответствующий FAILED + `run_id = <UTC>-<domain>-<shortsha>-<prompt_sha8>` |

Любой `FAILED` — блокирует PR. Overlay **MUST NOT** содержать `ALLOW_*`, `MODE`, orchestration-прозу; это ловится `domain-overlay.schema.json` (`patternProperties: ^ALLOW_.*` + `not anyOf`) и `no_controller_duplication`.

## 6. Профили и компиляция

| Профиль | Файл | `MODE` | `ALLOW_*` | Когда использовать |
|---|---|---|---|---|
| `audit-readonly` | `profiles/audit-readonly.yaml` | `audit` | `false` (все) | Default, findings-only, безопасно для paste |
| `full-write` | `profiles/full-write.yaml` | `full` | `true` (`ISSUE_WRITE/PUSH/MERGE/CLOSE`) | Явный оператор-override, требует provenance |
| `differential` | `profiles/differential.yaml` | `audit` | `false` | `AUDIT_MODE=differential` вариант |

`compile.py` рендерит `kernel + overlay + profile → generated/<domain>/<profile>.md` детерминированно; повторный прогон byte-identical. `N=10` итераций, caps `MAX_FILES_PER_SCOPE=300`, `MAX_ISSUES_PER_ITERATION=5`, `MAX_WAVES=3` — из `kernel.schema.json`, не повышать через prompt.

## 7. Lead-time метрика — Copy megacard → One overlay + tests

Цель ADR-060 Consequences: расширение стоит **один overlay + тесты**, а не копия kernel.

| Метрика | До Kernel v3 (megacard copy) | После Kernel v3 (overlay) | Дельта |
|---|---|---|---|
| Артефакт нового домена | Copy-paste ~800–1200 строк megacard с контроллером + ручная правка `ALLOW_*` | `overlays/<domain>.yaml` ~30 строк (8 полей) + `tests/prompts/golden/<domain>.md` | **24× → 1×** (D1 устранён, Table 9: 24→1) |
| Обязательные проверки | Нет схемы, drift между доменами | `overlay_schema_valid` + `guard_non_weakening` + `no_controller_duplication` + `golden` | 0 → 15 CI gates |
| Время добавления домена | ~4–8 ч (копирование, вычитка, риск drift) | **~0.5–1 ч**: `copy overlays/docs.yaml → <domain>.yaml` + `compile --domain <domain> --profile audit-readonly` + `lint/verify` | **-75–85%** |
| Миграция 24 доменов (P1) | — | 1 PR (24 YAML, 72 generated, 6 модулей 23 теста) | Доказано в P1 |
| Калибровка | Ручная | Пилоты P2 (5 macro-групп, 2 профиля) + `golden_render_24xprofiles` | Автоматизировано |

**Как измерить lead-time сейчас:**

```bash
time (cp docs/00-project/ai/prompts/overlays/docs.yaml docs/00-project/ai/prompts/overlays/<new>.yaml \
  && $EDITOR docs/00-project/ai/prompts/overlays/<new>.yaml \
  && python -m scripts.ai.prompts compile --domain <new> --profile audit-readonly \
  && python -m scripts.ai.prompts lint && python -m scripts.ai.prompts verify)
# ожидаемо <60 мин до green CI, без правки fragments/
```

Кандидаты расширения из `_annex-tables-v3.md` Table 8 (оценены в P3): `Composite semantics`, `Quarantine lifecycle` — каждый = 1 overlay по тому же пути.

## 8. Parity и проверка

* Parity отчёты: `reports/pilots/parity/<domain>.md` (24 шт) — byte-identical `legacy megacard (materialized-v3, MODE=full)` vs `generated/<domain>/full-write.md`.
* Golden: `tests/prompts/golden/<domain>__<profile>.md` — `golden_render_24xprofiles` gate.
* Resume: `reports/pilots/ledger-resume-proof.md` — прерванный прогон возобновляется с тем же `run_id`/iteration/stage без дубликатов `Issue/PR` (`resume_idempotency`).

Если `legacy_id_parity` FAILED — не помечать `status: deprecated`; чинить overlay/контур, затем `compile --all --check`.

## 9. Redirect catalog и удаление

Удаление legacy ID / wrapper — только после:

1. `legacy_id_parity` + `golden_render_24xprofiles` green,
2. P2 envelope без P0 break,
3. Этот гайд опубликован и `REGISTRY.yaml` `successor` указывает на `generated/<domain>/audit-readonly.md`,
4. Прошёл минимум 1 релиз с `status: deprecated` (ADR-060 §7).

Redirect catalog — таблица §2 этого файла + `compatibility/README.md` (§ Resolve legacy ID → generated file).

## 10. Ссылки

* ADR-060: `docs/02-architecture/decisions/ADR-060-prompt-kernel-and-overlay-architecture.md`
* MIGRATION-PLAN: `docs/00-project/ai/prompts/library/audit/project/materialized-v3/MIGRATION-PLAN.md` (P0–P3)
* Frozen 24 + master: `docs/00-project/ai/prompts/library/audit/project/materialized-v3/README.md`
* Kernel source: `docs/00-project/ai/prompts/library/audit/project/materialized-v3/_kernel-v3.md` (§3.1)
* Plan / Methodology / Annex: `_plan-v3.md`, `_methodology-v3.md`, `_annex-tables-v3.md`
* Fragments: `docs/00-project/ai/prompts/fragments/cyclic-kernel-v3.md`, `evidence-contract-v3.md`, `issue-state-machine-v3.md`
* Schemas: `docs/00-project/ai/prompts/_schema/kernel.schema.json`, `domain-overlay.schema.json`, `execution-profile.schema.json`, `finding-v3.schema.json`, `ledger-event.schema.json`
* Overlays: `docs/00-project/ai/prompts/overlays/*.yaml` (24)
* Generated: `docs/00-project/ai/prompts/generated/<domain>/<profile>.md`
* Compatibility: `docs/00-project/ai/prompts/compatibility/README.md` + `compatibility/<legacy-id>.md` (24)
* Registry: `docs/00-project/ai/prompts/REGISTRY.yaml`
* Scripts: `scripts/ai/prompts/compile.py`, `lint.py`, `verify.py`, `diff.py`
* Tests: `tests/prompts/unit/`, `contract/`, `golden/`, `integration/` (6 модулей, 23 теста)
