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
- **E3 EXECUTABLE**: `uv run vulture src/bioetl scripts tests` (1909 candidates in this broader scope; this is not the configured CI gate and requires contextual review).
- **E3 EXECUTABLE**: Configured architecture gate `tests/architecture/test_layer_dependencies.py::test_dead_code_vulture` scans `src/bioetl` with `min_confidence=80` and repository filters. On the audited follow-up worktree it reports one candidate: `src/bioetl/domain/ports/control_plane/run_evidence_location.py:51` (`expected_runtime_source_id`, 100% confidence). This is an observed gate finding, not evidence that Vulture is absent from CI.
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
- **concern**: Широкий запуск `vulture src/bioetl scripts tests` выявил 1909 кандидатов в указанном scope. Это число не является результатом настроенного CI gate: архитектурный тест отдельно сканирует `src/bioetl` с `min_confidence=80` и фильтрами репозитория.
- **severity**: P3
- **confidence**: low
- **status**: NOT_VERIFIABLE (actionable, evidence-collection required)
- **expected**: Различать широкий exploratory scan и настроенный CI gate; кандидаты требуют проверки контекста перед удалением или исключением.
- **actual**: Широкий scope вернул 1909 кандидатов; настроенный gate на проверенном follow-up worktree вернул один кандидат с confidence 100% (`expected_runtime_source_id`). Результат зависит от scope и фильтров.
- **evidence_ids**: E3
- **attempted_disproof**: В репозитории уже существует настроенный Vulture gate: `test_dead_code_vulture`, `min_confidence=80`, `VULTURE_IGNORED_NAMES` и `RESERVED_API_PARAMS`; он также охвачен heavy scan workflow. Широкий запуск включает иные каталоги и более низкие уровни confidence, поэтому его 1909 результатов не доказывают отсутствие CI-инструмента. Локальная проверка настроенного gate обнаружила конкретную строку, требующую проверки.
- **exceptions_checked**: Скрипты и тесты часто имеют неявные вызовы.
- **impact**: Накопление noise, усложнение понимания кодовой базы.
- **root cause**: Широкий exploratory запуск включает кандидатов разных типов и уровней confidence; это создаёт объём для ручной классификации, но не выявляет отсутствие настроенного CI gate.
- **recommendation**: Проверить конкретные findings настроенного gate, начиная с `expected_runtime_source_id`, и разбирать широкий набор кандидатов по контексту. Не добавлять параллельный gate или whitelist без подтверждённой потребности.
- **scope / non-goals**: Разбор всех 1909 случаев не входит в данный таск.
- **acceptance criteria**: Подтверждённые кандидаты настроенного gate устранены либо обоснованы; широкие exploratory results остаются классифицированными как не верифицированные до ручной проверки.
- **verification command/test**: `uv run pytest tests/architecture/test_layer_dependencies.py::test_dead_code_vulture -q`; broad scan: `uv run vulture src/bioetl scripts tests` (separate scope, not the CI gate).
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
- **review backlog**: Широкие exploratory Vulture candidates требуют контекстной проверки; настроенный архитектурный gate уже существует.

## G. Prioritized roadmap P0→P3
1. [P2] Ревизия `type: ignore` (Issue: unjustified_type_ignores).
2. [P3] Контекстная проверка широких exploratory Vulture candidates и findings настроенного gate (Issue: high_volume_dead_code_candidates).

## H. Verification Matrix
- Naming policy: Checked (ruff)
- Dead/zero-reference candidates: Broad exploratory scan checked (vulture, 1909 candidates); configured gate checked separately (1 candidate at 100% confidence on the follow-up worktree).
- Static typing ignores: Checked (grep, 25 instances)
- LOC/complexity/fan-in/out: Checked (radon, mostly A/B grades)

## I. `NOT_VERIFIABLE` и missing evidence
- Детальный разбор всех 1909 broad-scan candidates невозможен статически без контекста использования (entrypoints, plugins, dynamic imports). Этот объем не является результатом настроенного CI gate.

## J. Self-check
- unsupported claims: The initial claim that no configured dead-code analyzer exists was disproved by the architecture gate; the finding and issue draft now describe the broad scan and its limited scope.
- stale evidence: None. Run on current HEAD.
- exception handling: Noted for dead code (false positives).
- score/severity consistency: Yes, severities match guidelines (P2 for contract debt, P3 for hygiene).

## K. Verdict
Проект демонстрирует высокую общую гигиену (ruff 100% pass, mypy strict 100% pass), однако имеет локальные очаги технического долга в виде необоснованных `type: ignore` директив и широкого набора неподтвержденных exploratory Vulture candidates. Настроенный architecture gate уже существует и на проверенном follow-up worktree обнаружил один конкретный кандидат; это наблюдение требует проверки отдельно от широкого scan. Кодовая база пригодна для дальнейшего масштабирования при условии точечного погашения подтверждённого долга.

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
The exploratory command `vulture src/bioetl scripts tests` yielded 1909 candidates across a broader scope than the configured architecture gate. This does not show that the repository lacks a configured Vulture check. The configured `test_dead_code_vulture` scans `src/bioetl` at confidence 80 with repository filters; its follow-up run reported one candidate, `expected_runtime_source_id`, for contextual review.

**Evidence:**
- `uv run vulture src/bioetl scripts tests` outputs 1909 lines.
- See report: `reports/audit/pack-v2.1/P19-code-quality-hygiene.md`

**Expected vs actual:**
- *Expected:* Distinguish the configured CI gate from broader exploratory results and review confirmed gate findings in context.
- *Actual:* The broad scan produced 1909 candidates; the configured gate exists and reported one candidate in the follow-up worktree. The broad count is not a gate failure count.

**Impact:**
Accumulation of actual dead code is masked by noise, degrading repository hygiene over time.

**Scope / non-goals:**
- Review configured-gate findings and classify broad-scan candidates using repository context.
- Non-goal: Add a parallel gate/whitelist or manually verify and delete all 1909 items in one PR.

**Architecture constraints:**
- None.

**Implementation outline:**
- Run `tests/architecture/test_layer_dependencies.py::test_dead_code_vulture` and inspect reported candidates with their call sites.
- Keep broad scan findings separate from configured-gate output; record only verified root causes.

**Acceptance criteria:**
- Confirmed configured-gate candidates are resolved or have evidence-backed dispositions.
- No new gate or whitelist is proposed without a separately verified need.

**Verification commands/tests:**
- `uv run pytest tests/architecture/test_layer_dependencies.py::test_dead_code_vulture -q`
- `uv run vulture src/bioetl scripts tests` (exploratory scan, distinct scope)

**Dependencies:**
- None.

**Rollback/risk:**
- Low risk. Configuration only.
