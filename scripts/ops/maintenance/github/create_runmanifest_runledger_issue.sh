#!/usr/bin/env bash
set -euo pipefail

DEFAULT_OWNER="SatoryKono"
DEFAULT_REPO="BioactivityDataAcquisition"
API_ROOT="https://api.github.com/repos"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/ops/maintenance/create_runmanifest_runledger_issue.sh [--apply] [--owner NAME] [--repo NAME]

Options:
  --apply        Create the issue in GitHub. Default mode is dry-run.
  --owner NAME   Repository owner (default: SatoryKono)
  --repo NAME    Repository name (default: BioactivityDataAcquisition)
  -h, --help     Show this help

Environment:
  GITHUB_PERSONAL_ACCESS_TOKEN   Required only with --apply

Behavior:
  - creates the RunManifest-and-Run-Ledger issue with the prepared title/body
  - uses dry-run by default so the payload can be reviewed safely first
EOF
  return 0
}

OWNER="$DEFAULT_OWNER"
REPO="$DEFAULT_REPO"
APPLY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)
      APPLY=1
      shift
      ;;
    --owner)
      OWNER="${2:-}"
      shift 2
      ;;
    --repo)
      REPO="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown argument: %s\n\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

json_payload() {
  python3 <<'PY'
import json

payload = {
    "title": "RunManifest & RunLedger: introduce execution contract and deterministic run journal",
    "body": """## Summary

Текущая модель выполнения использует разрозненные `run_id`, `context` и `checkpoint state`, что нарушает:

- детерминизм
- воспроизводимость
- единый execution contract

Необходимо внедрить:

- `RunManifest` — immutable execution descriptor
- `RunLedger` — append-only execution journal
- согласованную модель `resume` через replay, а не только checkpoint

## Goals

- Ввести единый execution contract (`RunManifest`)
- Перевести систему на event-sourced execution model
- Устранить дублирование состояния (`checkpoint` vs `runtime`)
- Обеспечить deterministic replay

## Non-Goals

- Изменение бизнес-логики пайплайнов
- Переписывание storage слоёв
- Добавление новых внешних зависимостей

## Scope

### 1. Domain Layer

#### 1.1 RunManifest

Добавить Value Object:

- `src/bioetl/domain/value_objects/run_manifest.py`

Поля:

- `run_id`
- `pipeline_name`
- `run_type`
- `config_hash`
- `contract_ref`
- `contract_version`
- `started_at`

Инварианты:

- immutable (`frozen dataclass`)
- no I/O
- no `datetime.now()`

#### 1.2 RunLedger

Добавить Aggregate:

- `src/bioetl/domain/aggregates/run_ledger.py`

События:

- `StageStarted`
- `StageCompleted`
- `StageFailed`

Инварианты:

- append-only
- строгая последовательность стадий

### 2. Application Layer

#### 2.1 RunManifest propagation

Обновить:

- `PipelineRunner`
- `RecordProcessor`
- `BatchWriter`

Требования:

- удалить передачу `run_id` отдельно
- использовать только `RunManifest`

#### 2.2 Composite Pipeline integration

Файлы:

- `src/bioetl/application/composite/runner_pkg/*`

Добавить emission событий в `RunLedger` для стадий:

- `seed`
- `dependencies`
- `enrichers`
- `merge`
- `gold_write`

#### 2.3 Preflight → Ledger

Файл:

- `_preflight_orchestration.py`

Изменения:

- `success` → event
- `failure` → event + pipeline fail

### 3. Infrastructure Layer

#### 3.1 RunLedgerPort

Реализовать:

- `src/bioetl/infrastructure/run_ledger/*`

Требования:

- JSONL append-only
- atomic writes
- idempotency

Ошибки:

- использовать `StorageError` taxonomy

### 4. Checkpoint Integration

#### 4.1 Extend checkpoint state

Файл:

- `composite/checkpoint/state.py`

Добавить:

- `last_event_id` / `ledger_offset`

#### 4.2 Resume via ledger

Файл:

- `CompositeCheckpointLoadService`

Изменения:

- восстановление состояния через replay ledger
- checkpoint = snapshot only

### 5. Observability

#### 5.1 Logging

Все логи содержат:

- `run_id` (из `RunManifest`)
- `pipeline`
- `stage`

Использовать только `LoggerPort`.

#### 5.2 Remove contextvars run_id

- удалить глобальные `run_id`
- заменить на `RunManifest`

### 6. Error Handling

Унифицировать ошибки:

- `StorageError`
- `CheckpointConflictError`

Согласовать с `adapter_error_classifier`.

## Acceptance Criteria

- [ ] `RunManifest` используется во всех application сервисах
- [ ] `RunLedger` фиксирует все стадии pipeline
- [ ] `Checkpoint` не содержит бизнес-логики состояния
- [ ] `Resume` работает через replay ledger
- [ ] Нет передачи `run_id` вне `RunManifest`
- [ ] Нет `datetime.now()` вне Application
- [ ] Нет нарушений слоёв

## Risks

| Risk | Description | Mitigation |
| --- | --- | --- |
| State duplication | `checkpoint` vs `ledger` | `ledger` = source of truth |
| Non-determinism | runtime timestamps | only from `RunManifest` |
| Layer violation | infra logic leakage | enforce ports |
| Contract drift | mismatch config/hash | anchor validation |

## References

- ADR-026 Composite Pipeline Pattern
- ADR-014 Deterministic Writes
- ADR-018 Gold Strict Validation

## Notes

Это изменение переводит систему с implicit execution state на explicit event-sourced execution model.

Любые обходы, например «просто прокинем `run_id`», считаются архитектурной деградацией.
""",
}

print(json.dumps(payload))
PY
  return 0
}

API_URL="${API_ROOT}/${OWNER}/${REPO}/issues"
PAYLOAD="$(json_payload)"

if [[ "$APPLY" -eq 0 ]]; then
  printf '[DRY-RUN] POST %s\n' "$API_URL"
  printf '%s\n' "$PAYLOAD"
  exit 0
fi

: "${GITHUB_PERSONAL_ACCESS_TOKEN:?Set GITHUB_PERSONAL_ACCESS_TOKEN first}"

curl -fsS -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer ${GITHUB_PERSONAL_ACCESS_TOKEN}" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  -H "Content-Type: application/json" \
  "$API_URL" \
  --data "$PAYLOAD" >/dev/null

printf 'Done.\n'
printf 'Created issue in %s/%s\n' "$OWNER" "$REPO"
