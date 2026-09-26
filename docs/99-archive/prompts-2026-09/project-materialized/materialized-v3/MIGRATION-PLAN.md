# План обновления системы промптов — Kernel v3 (materialized 28.08.2026)

Источник: `bioetl_prompt_system_kernel_v3_full_portfolio_formatted_v2.1.docx`
ID документа: `BIOETL-PROMPT-ARCH-KERNEL-V3-003` | Baseline: `main @ 3aba8559a58038cd9ff9a90621f19ea39b930a2f` | Дата: 28.08.2026
Папка материализации: `docs/00-project/ai/prompts/library/audit/project/materialized-v3/` (24 промпта + master)

## 1. Что уже сделано в этом шаге

1. Извлечены **24 полных operator-paste текста** из гл.1 DOCX (copy-paste-ready, `MODE=full, ALLOW_*=true`) и сохранены как:
   `01-docs` … `10-coderabbit` (10 `cycle/`) + `11-medallion` … `24-scripts-inventory` (14 `project/new2/`).
2. Извлечён **Master Orchestrator v1.0** (гл.5.6) — `master-orchestrator-v1__full-project-audit.md` — последовательный запуск 01→24 + POST_AUDIT под единым `master-ledger.jsonl`.
3. Сохранены справочные фрагменты DOCX: `_kernel-v3.md` (гл.3.1), `_methodology-v3.md` (гл.2), `_plan-v3.md` (гл.4.1), `_annex-tables-v3.md` (таблицы 0–11).
4. Изменений в `library/audit/cycle/`, `library/audit/project/new2/`, `library/audit/project/full/`, `REGISTRY.yaml` **не вносилось** — это снапшот для аудита/пилота.

Проверка: `ls materialized-v3` — 24× `NN-*__prompt.*.md` + master + README + 4 `_*.md` = 30 файлов; все `id: prompt.*` совпадают с REGISTRY на `3aba8559`.

## 2. Текущее состояние до миграции (диагноз DOCX гл.2–3)

| Проблема | Проявление | Риск |
|---|---|---|
| D1 Controller duplication | 24 копии стадий Audit→Post-audit | Drift |
| D2 Conflict defaults | Карточки уже `ALLOW_*=true`, orchestrator должен быть fail-closed | Небезопасный default |
| D3 Incomplete Issue FSM | `reuse/defer/blocked`, target-branch close не формализованы | Преждевременное close |
| D4 No stable fingerprint | `sha256(domain|req|cause|paths)` отсутствует | Дубликаты |
| D5 Weak resume | `run_id` есть, ledger/cursor неедины | Повтор side effects |
| D6 Different schemas | `reports/` задан, JSON-контракты не унифицированы | Несопоставимые outputs |
| D7 Overlay как проза | Нет JSON Schema, запрещающей ослабление kernel | Тихий regression |
| D8 No compiler/golden | Не проверяются rendered prompts, precedence | Скрытые регрессии |
| D9 Method+execution mixed | Предметный метод хранит `ALLOW_*` | Смешение ответственности |
| D10 Migration complexity | IDs используются операторами | Ломает bookmarks |

Оценки до/после (гл.3.3, табл.5): 9.40–9.74 (Δ +0.47…+1.09) — см. `_annex-tables-v3.md`.

## 3. Целевая архитектура (DOCX гл.3–4.1)

```
docs/00-project/ai/prompts/
  fragments/
    cyclic-kernel-v3.md
    evidence-contract-v3.md
    issue-state-machine-v3.md
  overlays/
    docs.yaml .. scripts-inventory.yaml   # 24 overlay (без дублирования controller)
  profiles/
    audit-readonly.yaml   # MODE=audit, ALLOW_*=false (fail-closed default)
    full-write.yaml       # MODE=full, ALLOW_*=true (explicit override)
  _schema/
    kernel.schema.json / domain-overlay.schema.json / finding-v3.schema.json / ledger-event.schema.json
  generated/<domain>/<profile>.md
  compatibility/<legacy-prompt-id>.md
scripts/ai/prompts/compile.py lint.py verify.py
tests/prompts/unit/ contract/ golden/ integration/
```

Принцип: library kernel fail-closed; `full-write` — явный именованный профиль.

## 4. Пошаговый план (приоритеты табл.7 DOCX)

### P0 — Норматив и ядро (1–2 недели, один PR)

- [x] ADR Prompt Kernel and Overlay Architecture: [`ADR-060`](../../../../02-architecture/decisions/ADR-060-prompt-kernel-and-overlay-architecture.md) — owners, precedence (runtime → AGENTS.md → NORMATIVE_SOURCES.md → RULES.md → registry → kernel/overlay/profile), versioning (kernel SemVer / overlay per-domain / profile), migration window (закрыто в #9807).
- [x] Вынесено `fragments/cyclic-kernel-v3.md` (+ `evidence-contract-v3.md` + `issue-state-machine-v3.md`) — контент из `_kernel-v3.md` (Kernel v3.0 fail-closed, §3.1 DOCX).
- [x] Создано `_schema/*.json` (D7): `kernel.schema.json` / `domain-overlay.schema.json` (reject `ALLOW_*` — `patternProperties: ^ALLOW_.*` + `not anyOf`) / `execution-profile.schema.json` / `finding-v3.schema.json` (fingerprint `^[a-f0-9]{64}$`) / `ledger-event.schema.json` — запрещает `unknown guard overrides`, требует обязательные поля.
- [x] Зафиксировано: `materialized-v3/` — frozen snapshot 28.08.2026 `3aba8559` (не SSOT, не редактировать); SSOT — `fragments/` + `overlays/*.yaml` + `profiles/` + `_schema/` + `scripts/ai/prompts/` + `generated/`.

Accept: ADR принят; линтер не находит Audit/Plan/Issue секций в `overlays/` — см. `lint.py: no_controller_duplication`.

### P1 — Компилятор, ledger, миграция 24 доменов, тесты (2–4 недели)

- [x] `scripts/ai/prompts/compile.py`: детерминированный `kernel+overlay+profile → generated/<domain>/<profile>.md` + `prompt_sha8 = sha256(rendered).hex[:8]` + provenance header `kernel_sha8/overlay_sha8/profile` — `compile.py --all` (72 файла: 24×3 профиля), `compile.py --all --check` — byte-identical recompile.
- [x] `scripts/ai/prompts/lint.py` / `verify.py` / `diff.py`: `kernel_schema_valid`, `overlay_schema_valid`, `guard_non_weakening`, `no_controller_duplication`, `full_profile_explicit`; `verify` — `deterministic_compile`, `profile_precedence`, `finding_fingerprint_stability`.
- [x] Ledger/resume: `ledger-event.schema.json` append-only `reports/audit-runs/<run_id>/ledger.jsonl` + `master-ledger.jsonl`; resume reuses `run_id`/iteration/stage, side effects not replayed (описано в ADR-060 §6, фрагмент `issue-state-machine-v3.md`).
- [x] Мигрировано 24 домена в `overlays/*.yaml` (DOCX гл.3.2.1–3.2.24, Table 11): 01 docs … 10 coderabbit + 11 medallion … 24 scripts-inventory; предметные `OBJECT/SCOPE/SSOT/AUDIT_CONTOURS/MANDATORY_EVIDENCE/VALIDATION/DOMAIN_STOP/OUTPUT_EXTRAS`; kernel-части не дублируются.
- [x] Легаси wrappers в `compatibility/` — 24× `prompt.audit.cycle.*` (10) + `prompt.audit.project.new2.*` (14) → `generated/` wrapper (deprecation window до P3).
- [x] `profiles/`: `audit-readonly.yaml` (MODE=audit, ALLOW_*=false) / `full-write.yaml` (MODE=full, ALLOW_*=true explicit) / `differential.yaml`; `tests/prompts/` — 6 модулей, 23 теста (`compile_determinism`, `schema`, `guard_non_weakening`, `profile_precedence`, `finding_fingerprint`, `issue_fsm`).

Accept: 24 overlays валидны (lint: 0 errors); прерванный пилот возобновляется без дубликатов; legacy ID → тот же текст (compatibility wrappers, будет проверен golden-render в P3).

### P2 — Пилоты (1 неделя) — закрыто в #9809

- [x] 5 macro-групп: `requirements-trace → Medallion → DQ → control-plane` / `providers → HTTP → normalization → CLI` / `security → VCR → scripts → agents` / `tests → architecture → tech-debt → QA` / `GHA → telemetry → dashboards → ops → diagrams → docs → CodeRabbit` — каждая в `audit-readonly` (findings-only) + `full-write` прогоны (см. `reports/pilots/README.md`, метрики `duration/noise/duplicate/precision/cycle-completion/regression`).
- [x] Метрики envelope измерены; ledger/resume без дубликатов Issue/PR (`reports/pilots/ledger-resume-proof.md`).
- [x] Overlays откалиброваны по пилотам (MANDATORY_EVIDENCE/VALIDATION/SCOPE уточнены, kernel не дублируется).
- [x] Dry-run `master-orchestrator-v1` на 2–3 доменах (`security-secrets`, `qa-gates`, `medallion`) — калибровка до полного прогона.

Accept: нет P0 method break; resume-тест 0 дубликатов; envelope приложен.

### P3 — Deprecation и расширение — закрыто в #9810

- [x] `REGISTRY.yaml` — 24 легаси `status: deprecated` + `successor: overlays/<domain>.yaml` / `compatibility/<id>.md` (закрыто в #9810).
- [x] `MIGRATION-GUIDE-KERNEL-V3.md` — таблица `legacy id → overlay id → generated path`, deprecation window, предупреждения lint (см. `docs/00-project/ai/prompts/MIGRATION-GUIDE-KERNEL-V3.md`).
- [x] `generated/` catalog + diff + `prompt_sha8` закоммичены; новые домены — только `overlays/*.yaml` + `_schema` + тесты (`golden`, `guard_non_weakening`, `finding_fingerprint_stability`); 10 кандидатов табл.8 оценены (приоритет `Composite semantics`, `Quarantine lifecycle`).
- [x] Parity reports 24 доменов приложены (`reports/pilots/parity/`).

## 5. Автоматические проверки (гл.4.3)

`kernel_schema_valid` / `overlay_schema_valid` / `guard_non_weakening` / `deterministic_compile` / `legacy_id_parity` / `no_controller_duplication` / `full_profile_explicit` / `finding_fingerprint_stability` / `issue_fsm_contract` / `target_branch_close_gate`

## 6. Интеграция Master Orchestrator

До миграции: полный аудит 24 через `materialized-v3/master-orchestrator-v1__full-project-audit.md` (operator-paste). Порядок 01→24 по гл.5.3.
После миграции: master резолвит 24 overlay id, компилирует через `compile.py` с профилем `full-write`, ведёт `master-ledger.jsonl`.

## 7. Риски (табл.10)

Kernel-монолит → версионированные фрагменты. Потеря нюанса overlay → обязательные MANDATORY_EVIDENCE/VALIDATION + golden. Casual full profile → read-only default. Скрытый рендер → коммитить `generated/` + `prompt_sha8`. Ломка bookmarks → wrappers + deprecation window.

## 8. Следующий шаг

1. Ветка `chore/prompt-kernel-v3-adr-and-schemas` (P0).
2. Dry-run master на 2–3 доменах (security-secrets, qa-gates, medallion).

Связанные файлы: `materialized-v3/README.md`, `_kernel-v3.md`, `_plan-v3.md`, `_methodology-v3.md`, `_annex-tables-v3.md`, 24× `NN-*__prompt.*.md`, `master-*`.
