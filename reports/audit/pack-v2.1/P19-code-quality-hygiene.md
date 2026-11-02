# P19. Code quality, repository hygiene, typing, duplication и dead code

## A. Audit Manifest
- **Repo**: `https://github.com/SatoryKono/BioactivityDataAcquisition`
- **Branch**: `main`
- **Pinned Revision**: `7250ba1fee73d721ab78d4bac75763db24ef469e`
- **Scope**: `full repository excluding intentional caches/build outputs`
- **Worktree State**: Clean
- **Tool Versions**: Python 3.12, ruff (latest), mypy (latest), vulture (latest), radon (latest)
- **Permissions**: READ_ONLY (Issue creation authorized via WRITE_AUTHORIZED = YES)

## B. Scope/ownership и exclusions
- Исключены: `.venv`, `__pycache__`, `reports`, `docs`, intentional build outputs/artifacts.
- Аудит выполнен с помощью `vulture`, `radon`, `ruff`, `mypy`.

## C. Evidence Ledger
- **E2 STATIC**: At audited pin, `rg -n '# type:\s*ignore' src/bioetl` → **24** suppressions (nearly all with `[code]`); bare `rg -n 'type:\s*ignore' src/bioetl` → **25** hits including one prose mention in `arrow_typed.py`. Ticket/TODO refs on those lines: **0**.
- **E3 CLAIMED (pin, no artifact attached in this PR)**: `uv run mypy --config-file pyproject.toml --strict --incremental src/bioetl src/memory scripts/engineering/quality` — exit/output not stored here; treat as **NOT_REATTACHED**.
- **E3 TIP-SPOTCHECK**: `uv run --frozen --no-build ruff check src/bioetl` on post-rebase tip → exit 0 (scoped to `src/bioetl`, not full-tree `.`).
- **E3 CLAIMED (pin, no artifact attached)**: `uv run vulture src/bioetl scripts tests` → **1909** candidates reported by original run; not re-executed on tip.
- **E3 TIP-SPOTCHECK**: `rg -n '# type:\s*ignore' src/bioetl | wc -l` → **24** on tip after rebase onto `origin/main`.

## D. Findings Register

### finding_id: P19-HYGIENE-001
- **root_cause_id**: `unjustified_type_ignores`
- **owner_prompt**: P19
- **concern**: В `src/bioetl` есть **24** `# type: ignore[...]` без ticket/TODO-ссылок; коды ошибок у большинства есть, но обоснование техдолга отсутствует — это ослабляет аудируемость type-safety.
- **severity**: P2
- **confidence**: high
- **status**: CONFIRMED
- **expected**: Каждый `type: ignore` либо удалён (с исправлением типов), либо сопровождается ticket/обоснованием, например `# type: ignore[attr-defined]  # TODO(#123): dynamic attrs`.
- **actual**: 24 директивы с кодами ошибок; **0** с ticket/TODO. Не «голые» без `[code]`, но без трассируемого долга.
- **evidence_ids**: E2, E3 TIP-SPOTCHECK
- **attempted_disproof**: Ruff не запрещает `type: ignore` без ticket-комментария; scoped `ruff check src/bioetl` на tip → 0.
- **exceptions_checked**: Исключений для массовых `type: ignore` без ticket в BioETL `RULES.md` / `AGENTS.md` не найдено.
- **impact**: Затруднение рефакторинга и аудита suppressions на границах систем.
- **root cause**: Историческое накопление suppressions без оформления техдолга.
- **recommendation**: Ревизия 24 случаев: удалить ненужные; оставшиеся снабдить ticket/TODO.
- **scope / non-goals**: Только строки `# type: ignore` в `src/bioetl` (не prose-упоминания).
- **acceptance criteria**: Нет `type: ignore` без ticket/обоснования.
- **verification command/test**: `rg -n '# type:\s*ignore' src/bioetl`
- **dependencies**: None
- **related_findings**: None

### finding_id: P19-HYGIENE-002
- **root_cause_id**: `high_volume_dead_code_candidates`
- **owner_prompt**: P19
- **concern**: Инструмент статического анализа `vulture` выявил 1909 потенциальных кандидатов на мертвый код. Большинство относится к неиспользуемым переменным, функциям и классам в скриптах и тестовых утилитах.
- **severity**: P3
- **confidence**: low
- **status**: NOT_VERIFIABLE (actionable, evidence-collection required)
- **expected**: Отсутствие значительного объема мертвого кода, либо настроенный `.vulture_whitelist.py`.
- **actual**: 1909 кандидатов, требующих ручного анализа и разметки.
- **evidence_ids**: E3
- **attempted_disproof**: Большинство кандидатов (60% confidence) могут быть ложными срабатываниями (например, публичный API, фикстуры pytest, скрипты, вызываемые по имени).
- **exceptions_checked**: Скрипты и тесты часто имеют неявные вызовы.
- **impact**: Накопление noise, усложнение понимания кодовой базы.
- **root cause**: Отсутствие интегрированного и настроенного линтера мертвого кода (vulture/eradicate) в CI/pre-commit.
- **recommendation**: Внедрить `.vulture_whitelist.py`, настроить ignore-паттерны, поэтапно разобрать оставшиеся кандидаты.
- **scope / non-goals**: Разбор всех 1909 случаев не входит в данный таск.
- **acceptance criteria**: Внедрен настроенный whitelist, снижающий false-positives.
- **verification command/test**: `uv run vulture src/bioetl scripts tests`
- **dependencies**: None
- **related_findings**: None

## E. Quantitative Scorecard
- **Scale:** 1 (критичный незакрытый hygiene/typing debt) … 5 (чистые ratchets, tuned dead-code, обоснованные ignores).
- **Overall Score:** **3** (не 5): −1 dead-code noise/`NOT_VERIFIABLE` (1909 vulture, pin-claimed); −1 typing debt (24 ignores без ticket) + mypy pin-claim без артефакта.
- Repository hygiene, naming: 4 (tip spotcheck: `ruff check src/bioetl` exit 0; full-tree `.` не перепроверялся)
- Duplication: **NOT_VERIFIABLE** на tip (radon A/B — pin-claim без сохранённого вывода)
- Dead code: 2 (pin-claim 1909 vulture; требует whitelist/тюнинга; на tip не перезапускался)
- Static typing: 3 (24 `# type: ignore` без ticket; mypy `--strict` на pin **не** приложен артефактом → не ставить 4/5)
- Build/package hygiene: **NOT_VERIFIABLE** в этом PR (отдельных команд не записывали)
- Debt budgets/ratchets: 3 (нет явного CI-ratchet на «ignore без ticket»)

## F. Cross-cutting/root-cause clusters
- **type-safety debt**: Накопление `type: ignore`.
- **tooling gap**: Отсутствие настроенного анализатора мертвого кода.

## G. Prioritized roadmap P0→P3
1. [P2] Ревизия `type: ignore` (Issue: unjustified_type_ignores).
2. [P3] Внедрение vulture whitelist и разбор мертвого кода (Issue: high_volume_dead_code_candidates).

## H. Verification Matrix
- Naming/ruff (`src/bioetl`): tip spotcheck exit 0.
- Dead/zero-reference candidates: pin-claimed vulture 1909 — **NOT_REATTACHED** on tip.
- Static typing ignores: tip spotcheck 24× `# type: ignore` без ticket.
- mypy `--strict`: pin-claimed — **NOT_REATTACHED** (нет сохранённого stdout/exit в PR).
- LOC/complexity/radon: pin-claimed A/B — **NOT_VERIFIABLE** на tip.

## I. `NOT_VERIFIABLE` и missing evidence
- Полный разбор 1909 vulture-кандидатов без whitelist/entrypoints.
- Повторный mypy `--strict` / full-tree ruff / radon на tip с артефактами.
- Audited pin `7250ba1fee73d721ab78d4bac75763db24ef469e` ≠ текущий `origin/main` tip.

## J. Self-check
- unsupported claims: Убраны абсолютные «ruff/mypy 100% PASS» и Overall без формулы; mypy/vulture/radon без артефакта → `NOT_REATTACHED` / `NOT_VERIFIABLE`.
- stale evidence: Pin сохранён; tip spotcheck только для ruff(`src/bioetl`) и rg ignores. Self-check больше не утверждает «run on current HEAD».
- exception handling: Vulture false positives / dynamic entrypoints отмечены.
- score/severity consistency: Overall **3**; P2 для ignores без ticket; P3 для dead-code tooling gap.

## K. Verdict
**Overall Score 3/5.** На tip подтверждены: scoped ruff OK на `src/bioetl` и 24 `# type: ignore` без ticket. Pin-claims mypy `--strict`, full-tree ruff, radon и 1909 vulture **не** переприложены артефактами — не трактовать как Verified/PASS. Главный долг: трассируемые обоснования для type-suppressions и тюнинг dead-code анализа.

## Issue drafts
(Учетные данные GitHub API отсутствуют, Issue созданы как черновики)

### Draft Issue 1
**Title:** Type Safety Debt: Unjustified `type: ignore` usage (P19 Audit)
**Body:**
**Provenance:**
- Audit ID: pack-v2.1/P19
- Audited SHA: 7250ba1fee73d721ab78d4bac75763db24ef469e
- Root Cause ID: unjustified_type_ignores
- Source Finding IDs: P19-HYGIENE-001
- Severity: P2
- Confidence: High
- Status: CONFIRMED

**Problem:**
There are 24 `# type: ignore[...]` directives in `src/bioetl` that lack ticket/TODO references (error codes are usually present).

**Evidence:**
- `rg -n '# type:\s*ignore' src/bioetl` → 24 on tip spotcheck.
- See report: `reports/audit/pack-v2.1/P19-code-quality-hygiene.md`

**Expected vs actual:**
- *Expected:* Each `type: ignore` justified with a ticket ID or explicit technical reason.
- *Actual:* Coded ignores exist without ticket/TODO trail.

**Impact:**
Weakens type safety guarantees and obscures genuine architectural type mismatches.

**Scope / non-goals:**
- Update or remove the 24 identified `# type: ignore` instances in `src/bioetl`.
- Non-goal: Complete architecture type refactoring.

**Architecture constraints:**
- Must maintain strict mypy compliance (`--strict`).

**Implementation outline:**
- Review each of the 24 instances.
- If the type can be fixed natively, fix it and remove the ignore.
- If it cannot be fixed, append a comment referencing a specific TODO or ticket.

**Acceptance criteria:**
- 0 bare `type: ignore` statements in `src/bioetl` without justification.
- `mypy` still passes in strict mode.

**Verification commands/tests:**
- `uv run mypy --config-file pyproject.toml --strict --incremental src/bioetl`
- `grep -rn "type: ignore" src/bioetl`

**Dependencies:**
- None.

**Rollback/risk:**
- Low risk. Reverting type annotations if mypy fails.

---

### Draft Issue 2
**Title:** Dead Code Candidates: High volume of unverified vulture findings (P19 Audit)
**Body:**
**Provenance:**
- Audit ID: pack-v2.1/P19
- Audited SHA: 7250ba1fee73d721ab78d4bac75763db24ef469e
- Root Cause ID: high_volume_dead_code_candidates
- Source Finding IDs: P19-HYGIENE-002
- Severity: P3
- Confidence: Low
- Status: NOT_VERIFIABLE (actionable, evidence-collection)

**Problem:**
Running `vulture` on the repository yields 1909 dead code candidates, most of which are likely false positives due to lack of configuration (e.g., test fixtures, scripts).

**Evidence:**
- `uv run vulture src/bioetl scripts tests` outputs 1909 lines.
- See report: `reports/audit/pack-v2.1/P19-code-quality-hygiene.md`

**Expected vs actual:**
- *Expected:* A tuned dead code analysis configuration (e.g., `.vulture_whitelist.py`) that filters out false positives.
- *Actual:* No whitelist exists, rendering the tool output too noisy to act upon.

**Impact:**
Accumulation of actual dead code is masked by noise, degrading repository hygiene over time.

**Scope / non-goals:**
- Create and configure `.vulture_whitelist.py`.
- Non-goal: Manually verify and delete all 1909 items in one PR.

**Architecture constraints:**
- None.

**Implementation outline:**
- Generate a base whitelist using `vulture --make-whitelist`.
- Refine the whitelist to exclude common patterns (e.g., `test_*`, `conftest`, dynamic plugin loads).
- Integrate vulture check into a linting script.

**Acceptance criteria:**
- Vulture false positives are significantly reduced.
- Whitelist file is checked into the repository.

**Verification commands/tests:**
- `uv run vulture src/bioetl scripts tests`

**Dependencies:**
- None.

**Rollback/risk:**
- Low risk. Configuration only.
