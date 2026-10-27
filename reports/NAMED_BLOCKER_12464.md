# Named Blocker: CI Acceptance Pending Fullsuite Evidence (#12477)

**Status:** KEEP (pending) — **не** retired  
**Owner note (PSC RF-004 / #12569):** residue `#12477` задокументирован;
waiver ≠ PASS. См. `reports/domain-io-psc-rf004-closeout.md`.

## Blocker Description

Узкая SCC / entrypoint-проверка для `#12464` может быть зелёной, но по
спецификации задачи:

> «Пока совместимое fullsuite evidence #12477 не получено и не принято,
> CI-приёмка #12464 остаётся pending, даже если твой узкий тест зелёный.»

Поэтому независимая CI-приёмка `#12464` **не** закрывается узким Domain I/O
inventory green и **не** закрывается owner waiver без фактического PASS
fullsuite.

## Current fullsuite residue (#12477 / #12564)

| Field | Value |
| --- | --- |
| Evidence tip SHA | `100854af874059f7a873a501518e2955f6eb5916` |
| Evidence PR / commit | `#12564` |
| Command (canonical) | `pytest tests/architecture` (см. body `#12564`) |
| Result | **10 failed / 5592 passed / 19 skipped** |
| Verdict | **residue — не full PASS** |

`10 failed / 5592 passed / 19 skipped` **≠** PASS. Письменный owner
acceptance или waiver **не** переводит этот результат в test PASS.

## Action Required (owner path)

1. Триаж 10 failed на evidence tip / follow-up SHA для `#12477`.
2. Повторный полный прогон `tests/architecture` → exit 0.
3. Закрытие `#12477` с паспортом закрытия; затем reconcile этого blocker
   (retire) и CI-приёмки `#12464`.
4. До п.3 — **KEEP** этот файл; Domain I/O Variant A inventory green
   (`report-domain-io-taint-inventory --check`) ортогонален и **не** снимает
   blocker.

## Historical raw evidence (pre-#12564 narrow SCC)

- Temporary location (out-of-tree): `/tmp/evidence_artifact_12464.json`
- Source Commit: `928168ac9daca24f2c8a39eb4116c58ff98bb9a7`
- The results confirm 0 unreviewed SCCs and 1 accepted SCC.
- Artificial cycles detection succeeded.
- Entrypoint imports (`bioetl.domain.types`, `bioetl.domain.medallion`,
  `bioetl.interfaces.cli.main`, `bioetl.interfaces.http.health_server`)
  exited 0.

Эти узкие проверки **сохраняются как provenance** и **не** заменяют
fullsuite residue выше.
