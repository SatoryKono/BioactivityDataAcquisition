______________________________________________________________________

Version: 1.0.0
Status: draft
Class: operational
Owner: BioETL Team
Reviewers:

- BioETL Team
  Priority: P2
  Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
  Last verified: '2026-05-29'

______________________________________________________________________

# Merge Campaign Runbook

## Trigger

- Применяется для консолидирующих merge в ветке `consolidation/*`.
- Используется перед входом PR/веток в campaign branch и после каждого rebase/merge этапа.

## Impact

- Изменения влияют на порядок интеграции PR с high-value invariants (determinism, replay, control-plane).
- Неправильный порядок может нарушить reproducibility и инварианты `manifest`/`ledger`.

## Preconditions

- Ветка `main` обновлена (`git checkout main && git pull --ff-only`).
- Есть локальный `uv` environment:
  - `make install`
  - `make test-deps`
- Доступны артефакты из `.github/workflows/consolidation-gates.yml` и `.github/workflows/nightly-replay-parity.yml`.

## Procedure

### 1) Freeze baseline

```bash
git checkout -b consolidation/<campaign> main
git rev-parse HEAD | tee baseline.sha
uv sync --frozen --all-extras --dev
```

### 2) Run campaign gates (pre-merge)

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src tests

uv run pytest tests/architecture/test_ci_test_strategy.py -q
uv run pytest tests/architecture/test_config_golden_master.py -q
uv run pytest tests/architecture/test_gold_schema_contracts.py -q
uv run pytest tests/architecture/test_medallion_invariants.py -q
uv run pytest tests/architecture/test_explicit_gold_scd2_policy.py -q
uv run pytest tests/architecture/test_no_random_in_writers.py -q
uv run pytest tests/architecture/test_no_datetime_now_in_infrastructure.py -q
uv run pytest tests/architecture/test_no_structlog_in_application_interfaces.py -q
uv run pytest tests/architecture/test_lock_safety_guard.py -q
uv run pytest tests/architecture/test_metadata_output_contract.py -q
uv run pytest tests/architecture/test_provider_regression_matrix.py -q

uv run pytest tests/integration/determinism tests/integration/idempotency tests/integration/composite_resume -q
uv run pytest tests/snapshots -q
```

### 3) Rebase and evidence logging

- Перед rebase каждого PR в `consolidation/<campaign>`:
  - Проверить overlap и зависимость с `control-plane`/`replay` изменениями.
  - Пропускать PR с отсутствующим unique runtime-semantics diff как `superseded`.
- После каждого rebase сохранять `reproducibility`-отчёт:

```bash
ls -R tests/integration/determinism/reports/reproducibility \
  tests/integration/idempotency/reports/reproducibility \
  tests/integration/composite_resume/reports/reproducibility 2>/dev/null || true
```

### 4) Reconcile stale tails

- PR с документально чистым документ/репорт-only scope переносить cherry-pick/сводным commit.
- PR с изменениями `dedup/order/state-machine/infrastructure` проходят полный gate-проход.

### 5) Close campaign

- После завершения слияний выполнить nightly replay parity lane:

```bash
uv run pytest tests/integration/determinism tests/integration/idempotency tests/integration/composite_resume -q
```

- Перед merge в `main` проверить:
  - Все evidence-файлы в `.github/workflows/consolidation-gates.yml` и `nightly-replay-parity.yml` собраны;
  - Нет незакрытых stale tail веток.

## Verification

- Зафиксированы:
  - baseline hash
  - отчёты `reports/gates`
  - журналы rebase/merge по этапам
- Merge разрешается только после успешного прохода всех gate-команд.

## Rollback/Recovery

- Если после rebase обнаружен regression:
  - откатить последний squash/merge commit в campaign branch;
  - повторить полный gate-пакет перед продолжением.

## Post-incident

- Очистить campaign branch после merge.
- Закрыть служебные ветки-стандарты (`stale`, `docs`, `tail`) согласно triage policy.

## Compliance

- Campaign merges must preserve ADR-010 local-only assumptions and must not add
  Docker, Redis, Kubernetes, or external orchestration as runtime requirements.
- Evidence from replay, determinism, control-plane, and architecture gates must
  be attached to the campaign summary or PR notes before merge to `main`.
