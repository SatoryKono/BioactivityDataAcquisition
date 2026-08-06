# One-shot prompt: full BioETL CodeRabbit residual audit

Copy everything inside the fenced `PROMPT` block into a new agent session
(or attach this file and say “execute PROMPT”).

Do not increase tech-debt budgets. Do not edit `.env*`. Artifacts only under
`reports/quality/coderabbit/YYYYMMDD/`.

______________________________________________________________________

## PROMPT

```text
# MISSION
Проведи **полный исчерпывающий residual-аудит всего BioETL** через CodeRabbit CLI
(дополнительно — ground-truth gates репозитория). Цель: не «мнение модели», а
воспроизводимая кампания: preflight → leaf scopes ≤300 files → CLI waves →
FINDINGS/TRIAGE → GH path-cluster issues (critical/major) → 3–5 implement streams
→ re-audit → FINAL.md.

Репозиторий: SatoryKono/BioactivityDataAcquisition (локальный checkout).
Язык отчётов пользователю: **русский**. Код/paths/commands/issue titles — как в репо.

# NON-NEGOTIABLE PRECEDENCE (SSOT)
1. Code / domain contracts / config
2. Accepted ADRs + `docs/00-project/RULES.md` + `docs/00-project/NORMATIVE_SOURCES.md`
3. Architecture tests / quality gates (import-linter, basedpyright, debt/scorecard)
4. CodeRabbit findings (обязаны мапиться на evidence выше)

На конфликте: **code wins**.
**ЗАПРЕЩЕНО** повышать tech-debt / quality budgets, чтобы заглушить findings.
Local-only default (ADR-010): не делай Docker/Redis/внешнюю оркестрацию обязательными.
Root hygiene: никаких ad-hoc `_tmp_*.py` / device-name файлов в корне.

# CANONICAL REFERENCES (прочитай до работы)
- `docs/03-guides/coderabbit-audit-playbook.md`
- `docs/03-guides/development/coderabbit-local-reviews.md`
- `.coderabbit.yaml` (assertive)
- `.github/workflows/coderabbit.yml`
- `scripts/ops/run-coderabbit-reviews.sh`
- Scope matrix template: `reports/quality/coderabbit/20260805/01-scope-matrix.md`
- Prior campaign (de-dupe / не повторять closed): `reports/quality/coderabbit/20260806/`
- AI runtime entry: `Agents.md` / `docs/00-project/NORMATIVE_SOURCES.md`

# HARD CONSTRAINTS (CLI)
1. ≤ **~300 files** на один `coderabbit review` — всегда `git ls-files … | wc -l` до запуска
2. Host Windows → CLI в **WSL/Linux**; scopes **строго последовательно** (rate_limit)
3. Backoff при rate_limit; не крутить busy-loop; зафиксировать blocker-issue при необходимости
4. “All files ignored” / orphan-scope → P2 blocker, **не** выдумывать findings
5. Артефакты только: `reports/quality/coderabbit/YYYYMMDD/**` (allowlisted)
6. Secrets: не коммитить ключи; `.env*` не трогать без явного approve
7. De-dupe: **один open path-cluster issue на path** (canonical = earlier wave при равенстве)

# PHASE 0 — PREFLIGHT (обязательно первым)
1. `git fetch origin` (если есть сеть) → `BASE_SHA=$(git rev-parse origin/main)` иначе HEAD
2. Зафиксируй: `coderabbit --version`, `coderabbit auth status`, python/uv versions
3. Создай каталог: `reports/quality/coderabbit/YYYYMMDD/`
4. Построй **полную leaf scope matrix** (все части проекта) с file counts и under_cap=true/false
5. Запиши:
   - `00-preflight.md` (BASE_SHA, tools, auth, risks)
   - `01-scope-matrix.md` (таблица leaf_id | wave | files | globs)
6. Открой/обнови meta-epic issue (если пользователь разрешил gh write), иначе веди локальный CAMPAIGN.md

# FULL SCOPE MATRIX — ВСЕ ЧАСТИ ПРОЕКТА (обязательный охват)
Разбей так, чтобы **каждый tracked surface** попал ровно в один leaf (или residual-leaf).
Если leaf >300 files — split (half / subpackage). Минимум покрыть:

## Wave A — Architecture / core code
- `src/bioetl/domain/**` (по пакетам: ports, entities, aggregates, contracts, … + residual-root)
- `src/bioetl/application/core/**`
- `src/bioetl/application/services/control_plane/**`
- `src/bioetl/application/services/**` (без CP, если CP отдельным leaf)
- `src/bioetl/composition/**` (split если ≥300)
- `src/bioetl/interfaces/cli/**`, `src/bioetl/interfaces/http/**`

## Wave B — Data plane
- `src/bioetl/application/pipelines/**`
- `src/bioetl/infrastructure/http/**`, `storage/**`, `delta/**` (и соседние data I/O)
- `configs/quality/**`, pipeline/entity configs под `configs/**` (split по размеру)

## Wave C — Adapters / resilience / observability
- `src/bioetl/infrastructure/adapters/**`
- `src/bioetl/infrastructure/observability/**`
- прочий `src/bioetl/infrastructure/**` residual

## Wave D — Security residual
- secret-handling, path safety, subprocess, pickle/eval, HTTP SSRF/auth surfaces
  (scopes из security-relevant paths: interfaces, composition bootstrap, infra http/storage,
   scripts that touch credentials — только tracked, без .env)

## Wave E — Contracts / docs / Grafana / ops surfaces
- `docs/00-project/**` (normative: RULES, NORMATIVE_SOURCES, TOOLS, governance)
- `docs/02-architecture/decisions/**`
- `grafana/**`, dashboard-related docs/guides (split)
- CI workflows security-relevant: `.github/workflows/coderabbit.yml` и соседние quality workflows
  (если CLI ignores — blocker note)

## Wave F — Test honesty
- `tests/architecture/**` (две half-leaf при >300)
- `tests/unit/domain/**`, `tests/unit/application/**`, `tests/unit/infrastructure/**` (split)
- `tests/integration/**`
- critical scripts tests under `tests/unit/scripts/**` если в matrix

## Residual catch-all (после волн)
- любой `git ls-files` path, не попавший в leaf → residual leaves ≤300
- `scripts/**` (engineering/quality/ai) — отдельными leaves если в scope campaign

# PHASE 1 — RUN CLI (sequential)
Для каждого leaf в matrix:

```bash
export PATH="$HOME/.local/bin:$PATH"
OUT="reports/quality/coderabbit/$(date -u +%Y%m%d)"
mkdir -p "$OUT"
# pre-count files for leaf; abort/split if >300
coderabbit review --base main --dir <LEAF_DIR_OR_SPARSE> --plain \
  | tee "$OUT/review_<WAVE>_<LEAF_ID>.log"
```

Между leaf: короткая пауза; при rate_limit — backoff + запись в `BLOCKERS.md`, продолжай другие waves позже.
Не запускай параллельные CLI review на одном API key.

# CODERABBIT SYSTEM PROMPT (вставляй в каждый scoped run)
You are reviewing BioETL (hexagonal + DDD + medallion + local-only ADR-010).

Rules:
- Domain must stay I/O-free; DI only in composition.
- Prefer evidence: path + symbol + broken invariant.
- Do not propose increasing quality/debt budgets.
- Do not treat Docker/monitoring as required default.
- DQ hard_fail is multi-default (hierarchical 0.50 vs Silver-request 0.20).
- Ignore pure style nits unless they hide correctness risk.
- Skip themes already closed in ARCH-CR / DOC-GOV / prior CR residual packs
  unless you prove regression on current BASE_SHA.
- Prefer residual risks that escape unit tests: concurrency, lineage, quarantine,
  FK reconciliation, determinism/replay, secret leakage, gate honesty, contract drift.

Output for EACH finding (machine-parseable):
1) severity: critical | major | minor | trivial
2) path: repo-relative
3) claim: one sentence
4) why it matters: invariant / ADR / RULES id if possible
5) suggested fix class: code | test | config | docs
6) acceptance check: command or test name if possible
7) confidence: high | medium | low

# PHASE 2 — NORMALIZE + TRIAGE
После всех волн (или после каждой волны, если user wants incremental):
1. Слей логи → `FINDINGS.md` + machine table `FINDINGS.jsonl`
   fields: id, wave, leaf, severity, path, claim, fix_class, confidence, status
2. `TRIAGE.md`: confirm | reject | downgrade | upgrade vs current main (code wins)
3. `DE_DUPE_MAP.json`: path → canonical issue/finding
4. Severity counts: critical/major/minor/trivial (raw vs accepted)

Triage rules:
- reject: already fixed / FP / pure style / duplicate path
- downgrade: docs nit without contract impact
- upgrade: security, data loss, non-determinism, broken gate honesty

# PHASE 3 — PUBLISH GH ISSUES (critical + major only)
Для каждого **accepted** path-cluster severity critical|major:
- Title: `[CR-FULL][Wave X][severity] residual in \`path\` (N findings)`
- Body: epic, wave, path, top findings, acceptance checklist,
        “do not grow tech-debt budgets”, link to FINDINGS id
- Labels: architecture/quality + priority mapping (critical→priority:critical/high)
- De-dupe against open issues before create
- Minor/trivial: только в FINDINGS.md (issues — если user явно просит)

# PHASE 4 — STREAM PLAN (3–5 независимых потоков)
Разбей open critical+major path-clusters на **3–5 streams** с exclusive path ownership:
- нет общих файлов между параллельными worktree
- critical first
- выдай таблицу: Stream | paths | issue # | count
- предложи worktree commands, но **не** начинай implement без явного “go implement”
  (если user сказал “полный аудит” — default = audit+plan only, implement optional)

# PHASE 5 — OPTIONAL IMPLEMENT (только по явной команде)
Если user сказал implement:
- 1 worktree / stream
- fix root cause, tests, no budget growth
- PR per stream, close issues with evidence
- re-run CR only on fixed leaves

# PHASE 6 — CLOSEOUT (обязательно)
1. Re-audit fixed scopes (или sample high-risk leaves если implement не делали)
2. `FINAL.md`:
   - BASE_SHA, tool versions
   - leaves run / skipped / blocked
   - severity counts before/after triage
   - open critical/major remaining
   - stream plan
   - explicit: no tech-debt budget growth
3. `CAMPAIGN_STATUS.md` one-pager
4. Итоговый отчёт пользователю на русском: цифры + ссылки на артефакты + next actions

# GROUND-TRUTH (дополнительно к CodeRabbit, не вместо)
Минимум, когда feasible (зафиксируй skip+reason если нет env):
- architecture verify / import-linter (project command from TOOLS/playbook)
- targeted pytest for hot paths touched by critical findings
- basedpyright на затронутых пакетах (если принято в репо)

# EXECUTION MODE
- Работай автономно end-to-end по фазам 0→2→3→4→6
- Phase 5 (implement) — только если user явно просит fix/implement
- После preflight покажи matrix summary (N leaves, max files, waves) и **сразу продолжай** CLI waves
- Не останавливайся после первого leaf: цель — **весь matrix**
- При блокере leaf: document + next leaf (не abort whole campaign)

# DEFINITION OF DONE
- [ ] 00-preflight.md + 01-scope-matrix.md (полный охват проекта)
- [ ] review_*.log для каждого runnable leaf (или blocker reason)
- [ ] FINDINGS.md + FINDINGS.jsonl + TRIAGE.md + DE_DUPE_MAP.json
- [ ] GH issues для accepted critical/major path-clusters (de-duped) ИЛИ dry-run pack если нет gh write
- [ ] 3–5 stream split table
- [ ] FINAL.md + user summary in Russian
- [ ] No tech-debt budget growth; no .env edits; no root clutter

# START
Начни с Phase 0 preflight на текущем origin/main (или HEAD), создай YYYYMMDD artifacts dir,
построй полную scope matrix по всем частям проекта, затем последовательно гоняй Wave A→F + residual.
```

______________________________________________________________________

## How to launch

```bash
# Agent / Grok / Codex session:
# 1) Attach or open: reports/quality/coderabbit/PROMPT_FULL_PROJECT_AUDIT.md
# 2) Message: «Выполни PROMPT из этого файла end-to-end»

# Manual CLI only (без agent) — минимум:
# WSL + coderabbit auth + matrix из 01-scope-matrix + sequential review --dir
```

## Related

- Playbook: `docs/03-guides/coderabbit-audit-playbook.md`
- Prior full campaign: epic pattern CR-FULL 2026-08 under `reports/quality/coderabbit/20260806/`
