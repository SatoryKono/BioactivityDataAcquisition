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
- **Known tuned dead-code surfaces (pin + tip):** `tests/architecture/test_layer_dependencies.py::test_dead_code_vulture` (`min_confidence=80`, `_is_reportable_vulture_item` / `VULTURE_IGNORED_NAMES` / `RESERVED_API_PARAMS`); `scripts/engineering/dev/zed_vulture.py` (тот же порог 80; явно предупреждает о шуме bare vulture confidence 60).

## C. Evidence Ledger
- **E2 STATIC**: Tip spotcheck `rg -n '# type:\s*ignore' src/bioetl` → **24** suppressions (nearly all with `[code]`); bare `rg -n 'type:\s*ignore' src/bioetl` → **25** hits including one prose mention in `arrow_typed.py`. Ticket/TODO refs on those lines: **0**.
- **E2 CLASSIFY (tip):** SHA `bc250b869a9120bde7d076fc9720d53db3fe5c54`. `src/bioetl/infrastructure/storage/gold/writer_metrics.py` L56/L62 — **2** `# type: ignore[attr-defined]` с inline-обоснованием `Any: gold write request duck-type` → **не** считать unjustified debt. Остальные **22** без ticket/TODO и без явного technical-reason комментария на той же строке → residual candidates (полная ручная классификация всех 22 **не** выполнена в этом PR). Placeholder `(PR tip)` **запрещён**.
- **E3 CLAIMED (pin, no artifact attached in this PR)**: `uv run mypy --config-file pyproject.toml --strict --incremental src/bioetl src/memory scripts/engineering/quality` — exit/output not stored here; treat as **NOT_REATTACHED**.
- **E3 TIP-SPOTCHECK**: SHA `bc250b869a9120bde7d076fc9720d53db3fe5c54`; `uv run --frozen --no-build ruff check src/bioetl` → exit 0 (scoped to `src/bioetl`, not full-tree `.`).
- **E3 CLAIMED (pin, no artifact attached)**: bare `uv run vulture src/bioetl scripts tests` → **1909** candidates reported by original audit run; **not re-executed on tip**; provenance = pin-claimed / **NOT_REATTACHED**. Default vulture confidence 60 (см. docstring `zed_vulture.py`).
- **E3 STATIC (pin+tip):** существуют `test_dead_code_vulture` и `zed_vulture.py` с `min_confidence=80` + фильтрами — настроенный анализатор **есть**; отсутствие `.vulture_whitelist.py` ≠ «нет tooling».
- **E3 TIP-SPOTCHECK**: SHA `bc250b869a9120bde7d076fc9720d53db3fe5c54`; `rg -n '# type:\s*ignore' src/bioetl | wc -l` → **24**.
- **E3 HARNESS `test_dead_code_vulture` (tip `bc250b869a9120bde7d076fc9720d53db3fe5c54`):**
  - command: `uv run --frozen --no-build pytest tests/architecture/test_layer_dependencies.py::test_dead_code_vulture -q --tb=line`
  - expected (success): тест **не** `pytest.skip`; exit **0**; 0 reportable dead-code items
  - actual: **ran (not skipped)**; exit **1**; FAILED — `Found 1 potentially dead code item(s): .../run_evidence_location.py:51 - unused variable 'expected_runtime_source_id' (confidence: 100%)`
  - interpretation: complete run with **fail** — **не** success; skip≠success тоже не применялся
- **E3 HARNESS `zed_vulture.py` (tip `bc250b869a9120bde7d076fc9720d53db3fe5c54`):**
  - command: `uv run --frozen --no-build python scripts/engineering/dev/zed_vulture.py`
  - expected (success): `ensure_ready` OK; полный scan `min_confidence=80`; recorded exit + reportable count
  - actual: **incomplete** — `zed_env_doctor`: `[missing_venv] Missing Windows project interpreter: .../.venv-win/Scripts/python.exe`; scan **не** выполнен
  - interpretation: incomplete/env-blocked ≠ success; dead-code result **NOT_REATTACHED**

## D. Findings Register

### finding_id: P19-HYGIENE-001
- **root_cause_id**: `unjustified_type_ignores`
- **owner_prompt**: P19
- **concern**: Из **24** `# type: ignore[...]` в `src/bioetl` без ticket/TODO **2** (`writer_metrics`) уже имеют technical-reason (`Any: gold write request duck-type`). Residual **≤22** требуют ручной классификации; нельзя метить все 24 как unjustified.
- **severity**: P2
- **confidence**: medium-high (счётчик 24/2 verified; полная классификация 22 — partial)
- **status**: CONFIRMED (для разделения justified vs residual); величина residual debt после полной классификации — **NOT_FULLY_CLASSIFIED**
- **expected**: Каждый `type: ignore` либо удалён, либо имеет ticket **или** явное technical-reason обоснование на строке.
- **actual**: 24 с кодами ошибок; 0 ticket/TODO; **2 justified** (`writer_metrics`); **22 residual** без inline technical-reason (не проверены по одной).
- **evidence_ids**: E2, E2 CLASSIFY, E3 TIP-SPOTCHECK
- **attempted_disproof**: Ruff не запрещает ignore без ticket; scoped `ruff check src/bioetl` → 0. Devin: justified `Any` duck-type не должен входить в measured unjustified debt — **принято**.
- **exceptions_checked**: `writer_metrics` L56/L62 исключены из unjustified count.
- **impact**: Смешение justified/residual раздувает backlog ревизии.
- **root cause**: Историческое накопление suppressions; метрика «нет ticket» ≠ «нет обоснования».
- **recommendation**: Ревизия **residual ≤22** (не 24): удалить ненужные; оставшиеся — ticket/TODO или technical-reason. `writer_metrics` — out of scope для «добавить пояснение».
- **scope / non-goals**: Только `# type: ignore` в `src/bioetl`; не prose; не переписывать уже обоснованные `writer_metrics`.
- **acceptance criteria**: Нет residual `type: ignore` без ticket **или** technical-reason; justified cases отдельно учтены.
- **verification command/test**: `rg -n '# type:\s*ignore' src/bioetl` + ручная классификация
- **dependencies**: None
- **related_findings**: None

### finding_id: P19-HYGIENE-002
- **root_cause_id**: `raw_vulture_noise_vs_tuned_harness`
- **owner_prompt**: P19
- **concern**: Pin-claimed bare vulture прогон сообщил **1909** кандидатов (confidence≈60). Это **не** доказательство отсутствия tooling и **не** verified tip count. Уже есть настроенный harness: `test_dead_code_vulture` + `zed_vulture.py` (`min_confidence=80`, ignore lists).
- **severity**: P3
- **confidence**: low
- **status**: PARTIAL — tip pytest harness ran+failed (1 item); `zed_vulture` incomplete; 1909 pin-claimed / NOT_REATTACHED; CI-coverage gap — NOT_VERIFIABLE
- **expected**: Dead-code контроль через существующий tuned harness; bare low-confidence runs не использовать как primary debt signal; skip/incomplete ≠ success.
- **actual**: 1909 pin-claimed only. Tip `test_dead_code_vulture` @ `bc250b869a…`: expected exit 0 / not-skip → actual exit 1 / 1 item (fail). Tip `zed_vulture.py`: expected full scan → actual env-doctor incomplete (missing `.venv-win`).
- **evidence_ids**: E3 CLAIMED vulture, E3 STATIC harness, E3 HARNESS pytest, E3 HARNESS zed
- **attempted_disproof**: Codex P2 — harness уже на pin и tip — **принято**. Bare 1909 не обосновывает «внедрить анализатор с нуля».
- **exceptions_checked**: Шум confidence 60 документирован в `zed_vulture.py`; pytest может `skip` без vulture — здесь skip **не** был.
- **impact**: Ложный «tooling gap» и раздутый issue draft; fail harness ≠ green Verified.
- **root cause**: Смешение bare vulture (60) с отсутствием настроенного анализатора; CI inclusion harness **не** подтверждён.
- **recommendation**: Не предлагать повторное внедрение vulture tooling. Follow-up: разобрать tip fail `expected_runtime_source_id`; повторить `zed_vulture` в ready env; отдельно CI inclusion.
- **scope / non-goals**: Не удалять 1909 items; не invent `.vulture_whitelist.py` как обязательный deliverable этого finding.
- **acceptance criteria**: Отчёт/issue не утверждают «нет настроенного анализатора»; 1909 pin-claimed/unverified; harness evidence = expected vs actual + SHA; skip/incomplete ≠ success.
- **verification command/test**: см. E3 HARNESS (recorded); не bare `vulture` @60
- **dependencies**: None
- **related_findings**: None

## E. Quantitative Scorecard
- **Scale:** 1 (критичный незакрытый hygiene/typing debt) … 5 (чистые ratchets, tuned dead-code, обоснованные ignores).
- **Overall Score:** **3** (не 5): −1 за pin-claimed bare-vulture noise / NOT_REATTACHED (не за «отсутствие tooling»); −1 за residual typing suppressions (≤22) + mypy pin-claim без артефакта.
- Repository hygiene, naming: 4 (tip spotcheck: `ruff check src/bioetl` exit 0; full-tree `.` не перепроверялся)
- Duplication: **NOT_VERIFIABLE** на tip (radon A/B — pin-claim без сохранённого вывода)
- Dead code: 3 (harness exists; tip pytest fail≠success; zed incomplete≠success; bare 1909 pin-claimed; CI wiring NOT_VERIFIABLE)
- Static typing: 3 (2 justified `writer_metrics` excluded; ≤22 residual без ticket/technical-reason; mypy `--strict` **NOT_REATTACHED**)
- Build/package hygiene: **NOT_VERIFIABLE** в этом PR
- Debt budgets/ratchets: 3 (нет явного CI-ratchet на «ignore без ticket/reason»)

## F. Cross-cutting/root-cause clusters
- **type-safety debt**: Residual suppressions без ticket/technical-reason (после исключения justified).
- **measurement hygiene**: Bare vulture@60 ≠ отсутствие `test_dead_code_vulture` / `zed_vulture`.

## G. Prioritized roadmap P0→P3
1. [P2] Классификация residual `type: ignore` (≤22; исключая `writer_metrics` justified).
2. [P3] Follow-up evidence: tip-run tuned vulture harness + отдельно проверить CI inclusion (не «внедрить whitelist с нуля»).

## H. Verification Matrix
- Naming/ruff (`src/bioetl`): tip `bc250b869a…` exit 0.
- Dead/zero-reference: bare 1909 — **NOT_REATTACHED**; harness files — **STATIC OK**; `test_dead_code_vulture` tip — **FAIL** (exit 1, 1 item, not skip); `zed_vulture` tip — **INCOMPLETE** (env doctor / missing `.venv-win`) → scan **NOT_REATTACHED**.
- Static typing ignores: tip classify SHA `bc250b869a9120bde7d076fc9720d53db3fe5c54`; 24 total; **2 justified**; **≤22 residual**.
- mypy `--strict`: pin-claimed — **NOT_REATTACHED**.
- LOC/complexity/radon: pin-claimed A/B — **NOT_VERIFIABLE** на tip.

## I. `NOT_VERIFIABLE` и missing evidence
- Tip re-run bare vulture (не требуется как primary signal).
- Successful `zed_vulture` full scan на tip (сейчас incomplete).
- CI job matrix: входит ли `test_dead_code_vulture` в required lane.
- Полная построчная классификация всех 22 residual ignores.
- Audited pin `7250ba1fee73d721ab78d4bac75763db24ef469e` ≠ tip `bc250b869a9120bde7d076fc9720d53db3fe5c54` (до follow-up commits).

## J. Self-check
- unsupported claims: Убраны `(PR tip)`, «нет анализатора», «все 24 unjustified», PASS; skip/incomplete ≠ success; fail harness ≠ Verified green.
- stale evidence: Pin для 1909/mypy; tip SHA explicit for classify + harness runs.
- exception handling: Justified `writer_metrics` excluded; vulture@60 vs harness@80; pytest skip path noted but not taken.
- score/severity consistency: Overall **3**; P2 residual ignores; P3 harness follow-up (не greenfield tooling).

## K. Verdict
**Overall Score 3/5.** Tip `bc250b869a…`: ruff(`src/bioetl`) OK; **2** justified ignores; residual **≤22**. Dead-code harness **существует**; tip pytest **fail** (1 item) — не success; `zed_vulture` **incomplete** — не success; bare **1909** pin-claimed. Не трактовать как Verified/PASS.

## Issue drafts
(Pre-P20 draft only. Не создавать GitHub Issue до сверки P20.)

### Draft Issue 1
**Title:** Type Safety Debt: Residual `type: ignore` without ticket/technical-reason (P19)
**Body:**
**Provenance:**
- Audit ID: pack-v2.1/P19
- Audited SHA: 7250ba1fee73d721ab78d4bac75763db24ef469e
- Tip classify SHA: `bc250b869a9120bde7d076fc9720d53db3fe5c54`
- Root Cause ID: unjustified_type_ignores
- Source Finding IDs: P19-HYGIENE-001
- Severity: P2
- Confidence: Medium-High
- Status: CONFIRMED (residual set); full per-line classify partial

**Problem:**
24 `# type: ignore[...]` in `src/bioetl` lack ticket/TODO. **2** in `writer_metrics.py` already have technical-reason (`Any: gold write request duck-type`) and must **not** be counted as unjustified. Residual **≤22** need classification/fix.

**Evidence:**
- `rg -n '# type:\s*ignore' src/bioetl` → 24
- `writer_metrics.py` L56/L62 justified
- Report: `reports/audit/pack-v2.1/P19-code-quality-hygiene.md`

**Expected vs actual:**
- *Expected:* Each ignore has ticket **or** technical-reason (or is removed).
- *Actual:* 2 justified; ≤22 residual without ticket/technical-reason on-line.

**Scope / non-goals:**
- Do **not** rewrite justified `writer_metrics` comments.
- Non-goal: full architecture typing rewrite.

**Acceptance criteria:**
- Residual ignores have ticket/technical-reason or are removed.
- Justified cases remain explicitly excluded from unjustified debt count.

**Verification commands/tests:**
- `rg -n '# type:\s*ignore' src/bioetl`
- Manual classify residual lines

---

### Draft Issue 2
**Title:** Dead-code follow-up: tip-verify tuned vulture harness (not bare 1909)
**Body:**
**Provenance:**
- Audit ID: pack-v2.1/P19
- Audited SHA: 7250ba1fee73d721ab78d4bac75763db24ef469e
- Root Cause ID: raw_vulture_noise_vs_tuned_harness
- Source Finding IDs: P19-HYGIENE-002
- Severity: P3
- Confidence: Low
- Status: NOT_VERIFIABLE (actionable evidence-collection)

**Problem:**
Original audit cited **1909** bare-vulture candidates. That figure is **pin-claimed / NOT_REATTACHED** (not re-run on tip) and used default ~60% confidence. It must **not** be pasted into Issues as a live verified count.

**Existing tooling (do not reinvent):**
- `tests/architecture/test_layer_dependencies.py::test_dead_code_vulture` (`min_confidence=80`, filters)
- `scripts/engineering/dev/zed_vulture.py` (same threshold; documents confidence-60 noise)

**Evidence:**
- Pin-claimed only: bare vulture → 1909 (**NOT_REATTACHED** on tip)
- Static: harness files present on pin and tip
- Tip SHA `bc250b869a9120bde7d076fc9720d53db3fe5c54` harness runs — see report E3 HARNESS
- See report: `reports/audit/pack-v2.1/P19-code-quality-hygiene.md`

**Expected vs actual (tip `bc250b869a9120bde7d076fc9720d53db3fe5c54`):**
- `test_dead_code_vulture`: expected not-skip + exit 0 → **actual not-skip + exit 1** (1 unused var) — fail ≠ success
- `zed_vulture.py`: expected full scan → **actual incomplete** (`zed_env_doctor` missing `.venv-win`) — incomplete ≠ success
- Skip path exists in pytest when vulture missing — **not** taken on this run

**Scope / non-goals:**
- Record expected/actual/SHA; optional CI-wiring check.
- Non-goal: delete 1909 items; non-goal: mandatory new whitelist file.

**Acceptance criteria:**
- Any Issue text marks 1909 as pin-claimed/unverified if mentioned at all.
- Root cause does **not** claim «нет настроенного анализатора».
- Harness evidence never treats skip/incomplete as success.

**Verification commands/tests:**
- Recorded: `uv run --frozen --no-build pytest …::test_dead_code_vulture` @ `bc250b869a…` → exit 1
- Recorded: `uv run --frozen --no-build python scripts/engineering/dev/zed_vulture.py` @ `bc250b869a…` → incomplete (env doctor)
