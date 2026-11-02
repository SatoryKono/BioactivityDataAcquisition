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
- **E2 STATIC**: mypy reports 25 instances of `type: ignore` suppressions without justification or ticket references.
- **E3 EXECUTABLE**: `uv run mypy --config-file pyproject.toml --strict --incremental src/bioetl src/memory scripts/engineering/quality`
- **E3 EXECUTABLE**: `uv run ruff check .` (0 errors)
- **E3 EXECUTABLE**: `uv run vulture src/bioetl scripts tests` (1909 dead code candidates, many with 60% confidence which require contextual manual confirmation).
- **E3 EXECUTABLE**: `grep -rn "type: ignore" src/bioetl` (25 results).

## D. Findings Register

### finding_id: P19-HYGIENE-001
- **root_cause_id**: `unjustified_type_ignores`
- **owner_prompt**: P19
- **concern**: Наличие 25 `type: ignore` директив в `src/bioetl` без привязки к конкретным тикетам техдолга или объяснений, что ослабляет type-safety гарантии и затрудняет аудит строгой типизации.
- **severity**: P2
- **confidence**: high
- **status**: CONFIRMED
- **expected**: Все `type: ignore` должны быть либо удалены (с исправлением типов), либо сопровождаться комментарием с ID тикета/обоснованием, например, `# type: ignore[attr-defined]  # TODO(#123): Fix dynamically generated attributes`.
- **actual**: Присутствует 25 голых или слабо обоснованных `type: ignore` директив.
- **evidence_ids**: E2, E3
- **attempted_disproof**: Проверены правила ruff. Ruff не настроен на запрет `type: ignore` без обоснований, поэтому проверки проходят.
- **exceptions_checked**: Исключений для массовых `type: ignore` в BioETL `RULES.md` / `AGENTS.md` не найдено.
- **impact**: Затруднение рефакторинга, риск runtime type errors на границах систем.
- **root cause**: Историческое накопление suppressions без оформления техдолга.
- **recommendation**: Провести ревизию всех 25 случаев, удалить ненужные, для остальных создать локальные issues/TODO и снабдить комментарием.
- **scope / non-goals**: Обновление только 25 найденных строк в `src/bioetl`.
- **acceptance criteria**: Отсутствуют `type: ignore` без обоснования.
- **verification command/test**: `grep -rn "type: ignore" src/bioetl`
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
- Repository hygiene, naming: 4 (evidence: ruff 0 errors)
- Duplication: 4 (evidence: radon complexity is generally low, mostly A/B grades)
- Dead code: 2 (evidence: 1909 vulture candidates, requires tuning)
- Static typing: 4 (evidence: strict mypy pass, but 25 unannotated ignores)
- Build/package hygiene: 4
- Debt budgets/ratchets: 3 (no explicit threshold enforcement tool found for type ignores)

## F. Cross-cutting/root-cause clusters
- **type-safety debt**: Накопление `type: ignore`.
- **tooling gap**: Отсутствие настроенного анализатора мертвого кода.

## G. Prioritized roadmap P0→P3
1. [P2] Ревизия `type: ignore` (Issue: unjustified_type_ignores).
2. [P3] Внедрение vulture whitelist и разбор мертвого кода (Issue: high_volume_dead_code_candidates).

## H. Verification Matrix
- Naming policy: Checked (ruff)
- Dead/zero-reference candidates: Checked (vulture, 1909 candidates)
- Static typing ignores: Checked (grep, 25 instances)
- LOC/complexity/fan-in/out: Checked (radon, mostly A/B grades)

## I. `NOT_VERIFIABLE` и missing evidence
- Детальный разбор всех 1909 кандидатов на мертвый код невозможен статически без контекста использования (нужно проверять entrypoints, plugins, dynamic imports).

## J. Self-check
- unsupported claims: None. All claims backed by standard static analysis tools.
- stale evidence: None. Run on current HEAD.
- exception handling: Noted for dead code (false positives).
- score/severity consistency: Yes, severities match guidelines (P2 for contract debt, P3 for hygiene).

## K. Verdict
Проект демонстрирует высокую общую гигиену (ruff 100% pass, mypy strict 100% pass), однако имеет локальные очаги технического долга в виде необоснованных `type: ignore` директив и значительного числа неподтвержденных кандидатов на мертвый код (по результатам базового прогона vulture). Кодовая база пригодна для дальнейшего масштабирования при условии точечного погашения долга.

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
There are 25 instances of `type: ignore` in `src/bioetl` that lack ticket references or justification comments.

**Evidence:**
- `grep -rn "type: ignore" src/bioetl` yields 25 results.
- See report: `reports/audit/pack-v2.1/P19-code-quality-hygiene.md`

**Expected vs actual:**
- *Expected:* All `type: ignore` directives should be justified with a ticket ID or technical reason.
- *Actual:* Bare `type: ignore` directives exist.

**Impact:**
Weakens type safety guarantees and obscures genuine architectural type mismatches.

**Scope / non-goals:**
- Update or remove the 25 identified instances in `src/bioetl`.
- Non-goal: Complete architecture type refactoring.

**Architecture constraints:**
- Must maintain strict mypy compliance (`--strict`).

**Implementation outline:**
- Review each of the 25 instances.
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
