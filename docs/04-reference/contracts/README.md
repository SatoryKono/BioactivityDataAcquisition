---
Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-04-01'
---

# Contracts Registry

Кодовые контракты в `src/bioetl/domain/contracts/gold/` — **source of truth** для
контрактов Gold-слоя. JSON-экспорты в `docs/04-reference/contracts/gold/*.json`
являются сгенерированными артефактами для публикации и обзора.

## Published Contract Surfaces

Этот registry является published index для contract surfaces в
`docs/04-reference/contracts/`.

Для верхнеуровневой навигации по всему reference-разделу используйте
[`../index.md`](../index.md).

- **Gold contracts**:
  generated JSON under `docs/04-reference/contracts/gold/*.json`
- **Data Quality contracts**:
  [`dq-contracts.md`](dq-contracts.md) — canonical DQ contract pack
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

- изменения в `src/bioetl/domain/contracts/gold/` выполняются в коде;
- после изменения кодовых контрактов необходимо перегенерировать exported JSON;
- parity-check между кодом и exported JSON не должен допускать расхождений по `name/type/nullable/description`.

Обновление выполняется через unified script entry point:

```bash
python -m scripts.schema generate-contracts
```
