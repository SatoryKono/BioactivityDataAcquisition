# TRIAGE — CR-FULL #7696

- Generated: 2026-08-06T07:45Z
- Policy: code wins; no tech-debt budget growth
- De-dupe: one open issue per residual path (prefer Wave A / lower number / higher sev)

## Counts

| Bucket | Count |
| --- | ---: |
| Canonical open | 220 |
| P0 critical | 12 |
| P1 major | 208 |
| P2 minor | 0 |
| trivial open | 0 |
| Duplicates closed | 48 |

## Agent NDJSON (raw)

| Wave | critical | major | minor | trivial | total |
| --- | ---: | ---: | ---: | ---: | ---: |
| A | 11 | 531 | 175 | 330 | 1047 |
| B | 10 | 170 | 68 | 119 | 367 |
| C | 0 | 31 | 9 | 3 | 43 |
| D | 1 | 4 | 1 | 5 | 11 |
| **ALL** | 22 | 736 | 253 | 457 | 1468 |

## P0 critical (canonical open)

- #7738 `src/bioetl/composition/bootstrap/runtime` (34 findings, Wave A)
- #7750 `src/bioetl/application/services/control_plane` (73 findings, Wave A)
- #7770 `src/bioetl/application/core/base_transformer` (4 findings, Wave A)
- #7779 `src/bioetl/application/core/batch_checkpoint_recovery_service.py` (3 findings, Wave A)
- #7793 `src/bioetl/interfaces/http/health_server_http_mixin.py` (2 findings, Wave A)
- #7809 `src/bioetl/infrastructure/adapters/http` (2 findings, Wave A)
- #7821 `src/bioetl/infrastructure/adapters/crossref` (10 findings, Wave A)
- #7840 `src/bioetl/application/core/batch_transformer_streaming.py` (1 findings, Wave A)
- #7887 `src/bioetl/interfaces/http/run_report_ops.py` (2 findings, Wave A)
- #7972 `src/bioetl/application/pipelines/crossref` (9 findings, Wave B)
- #7993 `src/bioetl/infrastructure/storage/metadata` (3 findings, Wave B)
- #8030 `tests/security` (5 findings, Wave D)

## P1 major — top 30 by findings

- #7739 `src/bioetl/composition/factories/pipeline` (17, Wave A)
- #7740 `src/bioetl/composition/factories/services` (16, Wave A)
- #7741 `src/bioetl/composition/factories/storage` (12, Wave A)
- #7822 `src/bioetl/infrastructure/adapters/common` (9, Wave A)
- #7742 `src/bioetl/composition/factories/pipeline_support` (8, Wave A)
- #7929 `src/bioetl/domain/contracts/gold` (8, Wave A)
- #7962 `src/bioetl/application/pipelines/chembl` (8, Wave B)
- #8006 `configs/quality` (8, Wave B)
- #7823 `src/bioetl/infrastructure/adapters/decorators` (7, Wave A)
- #7824 `src/bioetl/infrastructure/adapters/pubchem` (7, Wave A)
- #7973 `src/bioetl/application/pipelines/common` (7, Wave B)
- #7743 `src/bioetl/composition/bootstrap/cli` (6, Wave A)
- #7744 `src/bioetl/composition/factories/datasource` (6, Wave A)
- #7825 `src/bioetl/infrastructure/adapters/chembl` (6, Wave A)
- #7974 `src/bioetl/application/pipelines/pubmed` (6, Wave B)
- #7975 `src/bioetl/application/pipelines/uniprot` (6, Wave B)
- #7745 `src/bioetl/composition/bootstrap/assembly` (5, Wave A)
- #7746 `src/bioetl/interfaces/http/control_plane_identity` (5, Wave A)
- #7778 `src/bioetl/application/core/batch_execution` (5, Wave A)
- #7826 `src/bioetl/infrastructure/adapters/pubmed` (5, Wave A)
- #7852 `src/bioetl/interfaces/cli/commands` (5, Wave A)
- #7805 `src/bioetl/infrastructure/adapters/uniprot` (4, Wave A)
- #7986 `src/bioetl/infrastructure/storage/bronze` (4, Wave B)
- #7747 `src/bioetl/composition/factories/dq` (3, Wave A)
- #7749 `src/bioetl/composition/runtime_builders/_run_manifest_data_roots.py` (3, Wave A)
- #7751 `src/bioetl/composition/runtime_builders/_snapshot_mapping_support.py` (3, Wave A)
- #7752 `src/bioetl/composition/services/versioning.py` (3, Wave A)
- #7760 `src/bioetl/application/core/postrun` (3, Wave A)
- #7827 `src/bioetl/infrastructure/adapters/semanticscholar` (3, Wave A)
- #7911 `src/bioetl/domain/ports/runtime` (3, Wave A)
- … +178 more in FINDINGS.md

## Parallel streams

| Stream | Paths |
| --- | --- |
| 1 Edge | interfaces/http, interfaces/cli, adapters, pipelines, configs/quality |
| 2 Core | composition, application/core, domain, storage, observability |

## Reject / hold

- trivial: drop unless correctness risk at implement
- types-only without basedpyright: reject
- style without correctness: reject
- E/F CLI blocked: #8031 #8032
- Domain rate-limit residual: #7946

## Acceptance #7696

- [x] FINDINGS.md de-duped
- [x] TRIAGE.md
- [x] DE_DUPE_MAP.json
- [x] Duplicate path-cluster issues closed (48)
- [x] Severity counts
- [x] Findings pack published
