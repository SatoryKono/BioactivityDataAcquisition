______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-06'

______________________________________________________________________

# Contracts Registry

Domain schemas в `src/bioetl/domain/schemas/` — **source of truth** для
контрактов всех слоёв (Pandera DataFrameModel). JSON-экспорты в
`docs/04-reference/contracts/gold/*.json` являются сгенерированными артефактами для
публикации и обзора.

Текущий published contract pack должен оставаться согласованным с live code и
config surfaces:

- Domain schemas: `src/bioetl/domain/schemas/` (Pandera DataFrameModel contracts)
- Contract configs: `configs/contracts/**`
- Control-plane domain models and ports:
  `src/bioetl/domain/control_plane/`,
  `src/bioetl/domain/ports/control_plane/`

## Published Contract Surfaces

Этот registry является published index для contract surfaces в
`docs/04-reference/contracts/`.

Для верхнеуровневой навигации по всему reference-разделу используйте
[`../index.md`](../index.md).

- **Gold contracts**:
  generated JSON under `docs/04-reference/contracts/gold/*.json`
- **Data Quality contracts**:
  [`dq-contracts.md`](dq-contracts.md) — canonical DQ contract pack backed by
  `configs/contracts/**`
- **Current data contract inventory**:
  [`data-contracts-current.md`](data-contracts-current.md) — current 27-contract
  YAML inventory and runtime contract chain
- **Control-plane contract**:
  [`run-manifest-ledger.md`](run-manifest-ledger.md) — published contract for
  `RunManifest` / `RunLedger`

Control-plane контракты `RunManifest` / `RunLedger` документируются отдельно в
[`run-manifest-ledger.md`](run-manifest-ledger.md). Для них текущим source of
truth являются доменные модели и порты в:

- `src/bioetl/domain/control_plane/`
- `src/bioetl/domain/ports/control_plane/`

## Supported Inspection Surface Pack

Для supported control-plane inspection surface published documentation MUST
оставаться связанной как единый feature-rollout pack:

- contract:
  [`run-manifest-ledger.md`](run-manifest-ledger.md)
- CLI reference:
  [`../cli.md`](../cli.md)
- mandatory runbook:
  [`../../05-operations/runbooks/run-manifest-inspection.md`](../../05-operations/runbooks/run-manifest-inspection.md)
- governing ADRs:
  [`ADR-044`](../../02-architecture/decisions/ADR-044-run-manifest-ledger-control-plane.md),
  [`ADR-045`](../../02-architecture/decisions/ADR-045-dq-contract-system.md)

Этот pack относится к published documentation surface и не должен
трактоваться как internal-only traceability artifact, пока inspection CLI и
runbook остаются supported.

Правило синхронизации:

- изменения в `src/bioetl/domain/schemas/` выполняются в коде;
- после изменения схем необходимо перегенерировать exported JSON;
- parity-check между кодом и exported JSON не должен допускать расхождений по `name/type/nullable/description`.

## Published Surface Hygiene

**Forbidden artifacts in active published tree**:

- Backup files (например, `*.backup-*`, `*.bak`) запрещены в `docs/04-reference/contracts/`
- Все backup artifacts должны храниться в `docs/99-archive/`
- Published contract surface должен содержать только активные, утверждённые контракты

Эта политика предотвращает неоднозначность и риск случайной публикации/ссылок на устаревшие артефакты.

Для test-facing drift baselines Gold layer теперь использует отдельный bounded
snapshot registry:

- `tests/fixtures/golden/gold/schema_registry.v1.json`
- `tests/contract/test_gold_schema_snapshot_registry.py`
- `tests/contract/test_gold_dq_golden_snapshots.py`

Этот registry не заменяет published JSON exports; он фиксирует canonical local
baseline для schema drift и bounded DQ-sensitive output bundles.

Repo-only planning or audit artifacts under `docs/plans/**`, `docs/reports/**`,
and `docs/99-archive/**` MAY be cited as supporting context, but they are not
part of the published contract surface.

Обновление выполняется через unified script entry point:

```bash
python -m scripts.schema generate-contracts
```
