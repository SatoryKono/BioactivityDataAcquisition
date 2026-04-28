# Repository File Structure Remediation Plan

Дата: 2026-04-28
Статус: Active / execution-tracking plan
Основание: архитектурно-строгий аудит файловой структуры BioETL от 28/04/2026 SGT | DA
Владелец: Engineering / Architecture

## Цель

Вернуть файловую структуру BioETL к опубликованной root-policy без потери
replay, traceability, fixture-governance и control-plane guarantees.

План намеренно разделяет:

- безопасную очистку уже доказанных cache/local surfaces;
- review-required переносы и удаления после usage/security evidence;
- retention-sensitive зоны, где broad cleanup запрещен.

Этот документ не заменяет нормативные источники:

- `docs/00-project/RULES.md`
- `docs/01-requirements/REQUIREMENTS.md`
- ADR в `docs/02-architecture/decisions/`
- `docs/00-project/governance/**`
- `scripts/engineering/repo/audit_root_cleanliness.py`
- `configs/quality/repo_structure_catalog.yaml`

## Freshness Note

Аудит от 2026-04-28 зафиксировал drift между опубликованной governance-моделью
и root-tree, видимым в GitHub. Локальная рабочая копия может отличаться от
этого снимка. Поэтому каждое действие ниже начинается с повторной верификации
через `git ls-files`, root audit и usage-check. Нельзя выполнять `git rm`
только по историческому плану или по визуальному root-листингу.

Повторная локальная проверка на 2026-04-28 уже показывает более чистое живое
состояние: `scripts/engineering/repo/audit_root_cleanliness.py
--strict-untracked` проходит, большинство исторических root candidates из
аудита отсутствуют в tracked root, а оставшиеся review-required и blocked lanes
зафиксированы в `configs/quality/root_hygiene_review_registry.yaml`.

Предыдущий план
`docs/plans/repository-file-structure-cleanup-plan-2026-04-20.md` остается
историческим baseline и context document. Его live-state утверждение от
2026-04-21 про `root cleanliness passes` нельзя использовать как текущее
evidence после аудита 2026-04-28.

## Guardrails

### Запрещено для broad cleanup

Следующие зоны не являются мусором без отдельного path-specific evidence и
retention review:

- `src/bioetl/**`
- `configs/**`
- `tests/**`
- `tests/fixtures/**`
- `tests/fixtures/vcr/**`
- `docs/00-05/**`
- `docs/99-archive/**`
- `docs/reports/**`
- `reports/**`
- `data/**`
- control-plane artifacts: RunManifest, RunLedger, checkpoints, effective-config
  artifacts, protected references, cached Bronze snapshots.

### Разрешено только после evidence

Для review-required root surfaces нужны минимум:

- `git ls-files` confirmation, что путь tracked;
- usage-check через `rg`;
- byte-compare для предполагаемых duplicate helpers;
- security review для env-like файлов;
- architecture owner decision для AI/tooling surfaces.

### Единственный high-confidence SAFE кандидат из аудита

`tracked .python-user/` можно удалять первым, если он реально присутствует в
tracked tree на момент исполнения. Основание: путь прямо запрещен root policy,
root audit и cleanup automation, а также не входит в control-plane или
reproducibility boundary.

## Phase 0. Freeze And Evidence Baseline

Цель: зафиксировать текущую картину перед любым удалением.

Команды:

```bash
git switch -c chore/root-hygiene-remediation-2026-04-28

git status --short --untracked-files=no
git ls-files > reports/quality/root-hygiene-tracked-files-2026-04-28.txt

.venv/bin/python scripts/engineering/repo/audit_root_cleanliness.py
.venv/bin/python scripts/engineering/repo/audit_root_cleanliness.py --strict-untracked
.venv/bin/python scripts/engineering/diagnostics/audit_structure.py --path .

make clean-preflight DRY_RUN=1
python scripts/ops/support/repo/cleanup_repository.py --dry-run
```

Если `.venv/bin/python` недоступен, использовать штатный repo command:

```bash
uv run python scripts/engineering/repo/audit_root_cleanliness.py
uv run python scripts/engineering/repo/audit_root_cleanliness.py --strict-untracked
uv run python scripts/engineering/diagnostics/audit_structure.py --path .
```

Выходные артефакты:

- tracked root inventory в `reports/quality/`;
- root audit output в PR description;
- cleanup dry-run output в PR description;
- список расхождений между audit snapshot и live tracked tree.
- updated `configs/quality/root_hygiene_review_registry.yaml` with current
  lane status for review-required and blocked cleanup surfaces.

Критерий выхода:

- есть воспроизводимый список tracked root violations;
- ни один retention-sensitive путь не попал в deletion set;
- для каждого root candidate назначена категория `SAFE`, `BLOCKED` или
  `REVIEW_REQUIRED`.

## Phase 1. Policy Reconciliation

Цель: устранить конфликт между документами, catalog и enforcement до file moves.

Действия:

1. Считать audit snapshot 2026-04-28 текущим trigger evidence для remediation,
   а cleanup-plan 2026-04-20/2026-04-21 только historical baseline.
1. Вести review-required root candidates в
   `configs/quality/root_hygiene_review_registry.yaml`, а не только в prose.
1. Обновить plan index и `configs/quality/repo_structure_catalog.yaml`, чтобы
   remediation plan был cataloged supporting context.
1. Перед запуском root audit в PR убедиться, что новые cataloged plan files
   уже staged/tracked. `audit_root_cleanliness.py` читает tracked/indexed paths
   через `git ls-files`; cataloged but untracked plan files будут выглядеть как
   missing.
1. Проверить `.github/root-allowlist.txt` против фактических tracked root files:

```bash
comm -23 \
  <(git ls-files | awk -F/ 'NF == 1 {print}' | sort) \
  <(sed '/^\s*#/d;/^\s*$/d' .github/root-allowlist.txt | sort)
```

1. Для каждого allowlist mismatch принять одно из решений:
   `move`, `remove`, `allow with justification`.
1. Обновить root hygiene docs только после решения, а не заранее.

Критерий выхода:

- root allowlist отражает только intentionally allowed root files;
- новые плановые документы cataloged;
- review-required root lanes имеют machine-readable owner/status/evidence
  registry;
- старый cleanup-plan помечен как historical baseline для live-state claims.

## Phase 2. SAFE Cleanup Wave

Цель: удалить только однозначно запрещенный tracked cache/env tree.

Кандидат:

- `.python-user/**`, только если он присутствует в `git ls-files`.

Команды:

```bash
git ls-files .python-user/
git rm -r .python-user/

.venv/bin/python scripts/engineering/repo/audit_root_cleanliness.py
```

Запрещено в этой фазе:

- удалять `.env.local`;
- удалять `.claude/`, `.codex_tmp/`, `.vibe/`;
- удалять root helper files без `cmp`;
- трогать `data/**`, `reports/**`, `docs/reports/**`, fixtures или archive.

Критерий выхода:

- `.python-user/` отсутствует в tracked tree;
- root audit не сообщает forbidden tracked `.python-user/`;
- поведение runtime/test/control-plane не менялось.

## Phase 3. Security Lane For `.env.local`

Цель: вывести tracked local env surface из репозитория без утечки секретов и без
смешивания security incident с обычной cleanup wave.

Pre-checks:

```bash
git ls-files .env.local
git log -- .env.local
```

Действия:

1. Не печатать содержимое `.env.local` в CI logs, issue body или PR description.
1. Провести локальный security review владельцем секрета.
1. Если файл содержит или когда-либо содержал секреты:
   - открыть отдельный incident/security task;
   - rotate affected tokens;
   - удалить tracked файл через `git rm --cached .env.local`;
   - при необходимости выполнить repository secret decontamination flow.
1. Если файл безсекретный и нужен как пример:
   - перенести значения в `.env.example` или docs;
   - удалить tracked `.env.local`;
   - убедиться, что `.gitignore` запрещает `.env.local`.

Команды после approval:

```bash
git rm --cached .env.local
rg -n "^\.env\.local$|\.env\.local" .gitignore .dockerignore docs scripts .github
```

Критерий выхода:

- `.env.local` не tracked;
- local env guidance живет в `.env.example` или docs;
- при наличии секретов выполнена rotation/decontamination task.

## Phase 4. Duplicate Helper Consolidation

Цель: убрать ambiguity между root helpers и canonical helpers under
`scripts/engineering/dev/**`.

Кандидаты из аудита:

- `FixHypothesisDb.ps1`
- `WSL_COMMANDS.sh`
- `test-driver-via-docker.sh`
- `warp-setup.sh`

Evidence commands:

```bash
git ls-files FixHypothesisDb.ps1 WSL_COMMANDS.sh test-driver-via-docker.sh warp-setup.sh

cmp -s FixHypothesisDb.ps1 scripts/engineering/dev/powershell/FixHypothesisDb.ps1
cmp -s WSL_COMMANDS.sh scripts/engineering/dev/bash/WSL_COMMANDS.sh
cmp -s test-driver-via-docker.sh scripts/engineering/dev/bash/test-driver-via-docker.sh
cmp -s warp-setup.sh scripts/engineering/dev/bash/warp-setup.sh

rg -n "FixHypothesisDb\.ps1|WSL_COMMANDS\.sh|test-driver-via-docker\.sh|warp-setup\.sh" \
  .github docs scripts tests configs README.md Makefile pyproject.toml
```

Decision rules:

- If byte-identical to canonical counterpart and no root-specific call-site
  remains: `git rm <root copy>`.
- If diverged but active: merge useful differences into canonical path, update
  call-sites, then remove root copy.
- If diverged and historical only: move to `docs/99-archive/**` with a note.
- If active external dependency requires root path: add a temporary shim with
  sunset date and catalog/allowlist justification.

Критерий выхода:

- у каждого helper остается один canonical owner;
- root no longer contains duplicate helper copies unless explicitly approved
  as a time-boxed shim;
- CI/docs references point at canonical `scripts/engineering/dev/**`.

## Phase 5. AI Tooling Surface Stabilization

Цель: стабилизировать `.claude/`, `.codex_tmp/`, `.vibe/` как owned tooling
surfaces или вывести их из tracked root.

### `.claude/*`

Исполнять через существующий план:

- `docs/plans/claude-to-ai-runtime-migration-plan-2026-04-25.md`

Краткий порядок:

1. Move `.claude/agents/*` -> `ai/claude/agents/*`.
1. Move `.claude/rules/*` -> `ai/claude/rules/*`.
1. Move `.claude/skills/*` -> `ai/claude/skills/*`.
1. Обновить `.codex/skills/**`, CI, tests и docs.
1. Оставить compatibility layer на один релиз.
1. Удалить `.claude/*` только после:

```bash
rg -n "\.claude/" .
pytest tests/architecture -q
```

### `.codex_tmp/*` and `.vibe/*`

Decision path:

1. Определить owner и intended lifecycle:
   - shared tooling surface;
   - local-only temp surface;
   - historical artifact.
1. Если shared tooling: catalog/allowlist + docs ownership note.
1. Если local-only temp: удалить из tracked tree и добавить ignore rule.
1. Если historical: move to `docs/99-archive/**`.

Usage commands:

```bash
git ls-files .codex_tmp .vibe
rg -n "\.codex_tmp|\.vibe" .github docs scripts tests configs README.md pyproject.toml
```

Критерий выхода:

- `.claude/*` больше не является runtime dependency после migration PR2;
- `.codex_tmp/*` и `.vibe/*` имеют documented owner или удалены из tracked tree;
- root audit и architecture tests отражают принятое решение.

## Phase 6. Root Notes, Ad-Hoc Tests, And Diagnostics

Цель: убрать non-canonical root text/test/diagnostic files без потери активных
call-sites.

Кандидаты из аудита:

- `AGENT.md`
- `.codex_tmp_issue_*.md`
- `QUICK_START.md`
- `query_test_docs_memory.js`
- `seed_test_docs_memory.js`
- `test_*.js`
- `test_*.json`
- `test_neo4j_memory.py`
- `tinyproxy.conf`

Evidence commands:

```bash
git ls-files AGENT.md .codex_tmp_issue_*.md QUICK_START.md \
  query_test_docs_memory.js seed_test_docs_memory.js test_*.js test_*.json \
  test_neo4j_memory.py tinyproxy.conf

rg -n "AGENT\.md|QUICK_START\.md|query_test_docs_memory|seed_test_docs_memory|test_neo4j_memory|tinyproxy\.conf" \
  .github docs scripts tests configs README.md Makefile pyproject.toml package.json
```

Decision rules:

- Operator docs -> `docs/05-operations/**`.
- Active engineering plan/note -> `docs/plans/**` only if cataloged, otherwise
  `docs/99-archive/**`.
- Active tests -> `tests/**` with normal pytest/node test discovery.
- Active support config -> `configs/**`.
- Historical-only notes -> `docs/99-archive/**`.
- No call-site and generated/ad-hoc -> `git rm`.

Критерий выхода:

- root markdown/txt остается limited to canonical entrypoints;
- root ad-hoc tests/configs отсутствуют;
- active behavior moved under owned surfaces with tests or docs references.

## Phase 7. Docker And Runtime Root Surface Review

Цель: принять отдельное решение по root runtime files, которые audit отметил как
unknown/review-required.

Кандидаты:

- `Dockerfile`
- `entrypoint.sh`
- `requirements.txt`

Evidence commands:

```bash
git ls-files Dockerfile entrypoint.sh requirements.txt
rg -n "Dockerfile|entrypoint\.sh|requirements\.txt" \
  .github docs scripts tests configs README.md Makefile docker-compose*.yml pyproject.toml
```

Decision rules:

- If used by active CI/runtime: either add to `.github/root-allowlist.txt` with
  justification or move to a named canonical path and update call-sites.
- If superseded by `Dockerfile.bioetl`, `Dockerfile.warp`, `pyproject.toml`,
  or `uv.lock`: remove after usage-check.
- If needed only for one historical setup path: archive or move under
  `docs/99-archive/**`.

Критерий выхода:

- no unallowlisted root runtime file remains;
- Docker/runtime docs point at canonical Dockerfile/package surfaces;
- CI build paths are explicit.

## Phase 8. Retention-Sensitive Surfaces

Цель: явно не смешивать root cleanup с data/control-plane retention cleanup.

Blocked surfaces:

- `data/**`
- `reports/**`
- `docs/reports/**`
- `docs/99-archive/**`
- `tests/fixtures/**`
- `tests/fixtures/vcr/**`
- RunManifest/RunLedger/checkpoints/effective-config/protected references

Allowed actions:

- inventory only;
- checksum/report generation;
- retention policy proposal;
- bounded cleanup with owner approval and dry-run artifact.

Required retention preflight before any future cleanup:

```bash
python scripts/ops/data/verify_checksums.py --help
python scripts/ops/data/validate_data_dir.py --help
python scripts/ops/data/vacuum_delta.py --help
```

Критерий выхода:

- remediation PR does not delete retention-sensitive paths;
- any future retention cleanup has separate plan, approval and rollback story.

## Phase 9. Enforcement Hardening

Цель: сделать drift difficult to reintroduce.

Действия:

1. Убедиться, что root hygiene workflow запускается на PR:

```bash
sed -n '1,220p' .github/workflows/root-hygiene.yml
```

1. Перевести root hygiene из recommended в required status check в GitHub branch
   protection settings.
1. Добавить/уточнить tests around:
   - forbidden tracked `.python-user/`;
   - forbidden tracked `.env.local`;
   - non-canonical root markdown/txt;
   - forbidden root `test_*.js`, `test_*.json`, root `*.py`;
   - catalog requirement for every `docs/plans/*.md`.
1. Синхронизировать `.gitignore`, `.dockerignore`, root allowlist, structure
   catalog и cleanup scripts.

Verification commands:

```bash
.venv/bin/python scripts/engineering/repo/audit_root_cleanliness.py --strict-untracked
.venv/bin/python -m pytest tests/unit/scripts/repo/test_audit_root_cleanliness.py -q
.venv/bin/python -m pytest tests/architecture -q
```

Критерий выхода:

- root hygiene fails on reintroduced forbidden tracked artifacts;
- catalog drift fails locally and in CI;
- required branch protection blocks policy regression.

## Tracking Issues

- `RH-001`: https://github.com/SatoryKono/BioactivityDataAcquisition/issues/3219
- `RH-002`: https://github.com/SatoryKono/BioactivityDataAcquisition/issues/3220
- `RH-003`: https://github.com/SatoryKono/BioactivityDataAcquisition/issues/3221
- `RH-004`: https://github.com/SatoryKono/BioactivityDataAcquisition/issues/3222
- `RH-005`: https://github.com/SatoryKono/BioactivityDataAcquisition/issues/3223
- `RH-006`: https://github.com/SatoryKono/BioactivityDataAcquisition/issues/3224
- `RH-007`: https://github.com/SatoryKono/BioactivityDataAcquisition/issues/3225
- `RH-008`: https://github.com/SatoryKono/BioactivityDataAcquisition/issues/3226
- `RH-009`: https://github.com/SatoryKono/BioactivityDataAcquisition/issues/3227

## PR Decomposition

### PR 1. Plan And Policy Alignment

Scope:

- add this remediation plan;
- catalog it;
- mark 2026-04-20 cleanup-plan live-state claims as stale after 2026-04-28 audit;
- no file deletions.

Verification:

```bash
.venv/bin/python scripts/engineering/repo/audit_root_cleanliness.py
```

### PR 2. SAFE Cache Removal

Scope:

- remove tracked `.python-user/` if present;
- update ignore/audit tests only if needed.

Verification:

```bash
.venv/bin/python scripts/engineering/repo/audit_root_cleanliness.py --strict-untracked
```

### PR 3. Security Env Cleanup

Scope:

- remove tracked `.env.local` after security review;
- rotate secrets if required;
- update `.env.example`/docs.

Verification:

```bash
git ls-files .env.local
rg -n "\.env\.local" .gitignore .dockerignore docs scripts .github
```

### PR 4. Root Helper Consolidation

Scope:

- compare and remove or move root helper duplicates;
- update call-sites to canonical `scripts/engineering/dev/**`.

Verification:

```bash
rg -n "FixHypothesisDb\.ps1|WSL_COMMANDS\.sh|test-driver-via-docker\.sh|warp-setup\.sh" .
.venv/bin/python scripts/engineering/repo/audit_root_cleanliness.py
```

### PR 5. AI Tooling Migration

Scope:

- execute `.claude/*` -> `ai/claude/*` migration plan;
- decide `.codex_tmp/*` and `.vibe/*` ownership.

Verification:

```bash
rg -n "\.claude/|\.codex_tmp|\.vibe" .github docs scripts tests configs
pytest tests/architecture -q
```

### PR 6. Root Diagnostics And Runtime Surface Cleanup

Scope:

- relocate/delete root notes, ad-hoc tests and diagnostics after usage-check.

Verification:

```bash
.venv/bin/python scripts/engineering/repo/audit_root_cleanliness.py --strict-untracked
.venv/bin/python -m pytest tests/unit/scripts/repo/test_audit_root_cleanliness.py -q
```

### PR 7. Docker And Runtime Root Surface Review

Scope:

- review `Dockerfile`, `entrypoint.sh`, and `requirements.txt` if present in
  tracked root;
- move, remove, or explicitly allow them after usage-check.

Verification:

```bash
git ls-files Dockerfile entrypoint.sh requirements.txt
rg -n "Dockerfile|entrypoint\.sh|requirements\.txt" \
  .github docs scripts tests configs README.md Makefile docker-compose*.yml pyproject.toml
.venv/bin/python scripts/engineering/repo/audit_root_cleanliness.py
```

### PR 8. Retention Procedure Boundary

Scope:

- document a separate retention-driven procedure for `data/**`, `reports/**`,
  `docs/reports/**`, `docs/99-archive/**`, and fixtures;
- do not delete retention-sensitive paths in the root cleanup wave.

Verification:

```bash
python scripts/ops/data/verify_checksums.py --help
python scripts/ops/data/validate_data_dir.py --help
python scripts/ops/data/vacuum_delta.py --help
```

### PR 9. Enforcement Hardening

Scope:

- strengthen root hygiene tests and CI coverage;
- align `.gitignore`, `.dockerignore`, allowlist, catalog, and cleanup scripts;
- make root hygiene a required branch-protection check.

Verification:

```bash
.venv/bin/python scripts/engineering/repo/audit_root_cleanliness.py --strict-untracked
.venv/bin/python -m pytest tests/unit/scripts/repo/test_audit_root_cleanliness.py -q
.venv/bin/python -m pytest tests/architecture -q
```

## Rollback Strategy

- Use small PRs; avoid mixed security/tooling/runtime cleanup.
- For `git rm` paths, rollback is normal `git revert <commit>` unless secret
  decontamination was involved.
- For `.env.local`, rollback must not restore secrets to tracked history.
- For migrated helpers/tooling, keep compatibility shims for one release when
  external operator usage is plausible.
- For any moved active file, include call-site update and targeted test in the
  same PR.

## Completion Definition

The remediation is complete when:

- `audit_root_cleanliness.py --strict-untracked` passes in local and CI context;
- tracked root files all appear in `.github/root-allowlist.txt` or are removed;
- tracked root directories are approved surfaces only;
- `.python-user/` and tracked `.env.local` are absent;
- root duplicate helpers no longer compete with canonical `scripts/**` paths;
- `.claude/*` migration is closed or explicitly time-boxed;
- no retention-sensitive path was deleted by broad cleanup;
- branch protection requires root hygiene checks.
