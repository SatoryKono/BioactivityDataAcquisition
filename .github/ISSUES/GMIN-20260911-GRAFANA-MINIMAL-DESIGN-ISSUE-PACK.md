# Grafana minimal design — GMIN-20260911

**Status:** open (issues published 2026-09-11)
**Wave code:** GMIN
**Date:** 2026-09-11
**Source audit:** BioETL Grafana: сравнение и минимальные изменения дизайна (11.09.2026 14:22 EDT)
**Baseline:** `origin/main` `850fcb7424bc8962c5d70bf52663fff8c488f1e0`

## Context

Targeted comparison of a saved design concept against current shipped dashboards.
Do **not** replace the seven UIDs. PNG illustrations are not Grafana renders
and are not a business-semantics source.

Bodies: `.github/ISSUES/_gmin_bodies/`

## Portfolio (unchanged)

| uid | Board |
| --- | --- |
| `bioetl-control-plane-v1` | 0. Trust |
| `bioetl-overview-v2` | 1. Overview |
| `bioetl-runtime` | 2. Pipeline Diagnostics |
| `bioetl-provider-health-v2` | 3. Provider Health |
| `bioetl-dq-v2` | 4. Data Quality |
| `bioetl-incident-v1` | 5. Incident Workspace |
| `bioetl-run-explorer-v1` | 6. Run Explorer |

## Issue matrix

| Code | Issue | Pri | Title |
|------|-------|-----|-------|
| GMIN-00 | [#10387](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/10387) | P1 | epic — минимальные правки дизайна |
| GMIN-01 | [#10388](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/10388) | P1 | Исправить scope/time подписи |
| GMIN-02 | [#10389](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/10389) | P2 | Нейтральные статические banners |
| GMIN-03 | [#10390](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/10390) | P1 | `viewPanel=3022` в Run-link 3010 |
| GMIN-04 | [#10391](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/10391) | P2 | Qualifier top-N «до 2/3/5» |
| GMIN-OPT-01 | [#10392](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/10392) | P3 | DQ 9101 `colorMode=value` после рендера |
| GMIN-OPT-02 | [#10393](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/10393) | P3 | Trust 9418 freshness только при наличии поля |

## Delivery order

1. #10388 (copy/scope)
2. #10389 (neutral banners; updates DUX6 CSS contracts)
3. #10390 (Run link + browser gate)
4. #10391 (visible top-N)
5. Decide #10392 / #10393 from real renders

Budget: 0 new/deleted dashboards, 0 new data panels, 0 query/`gridPos` changes.

## Related open work

- #10170 contrast/reflow measurement — render evidence for GMIN-02/GMIN-03, not a rewrite of this pack.

## Rejected from the concept

Greenfield rewrite, Trust+Run Explorer merge, Trust Score, causal confidence,
Configuration UID, Investigating lifecycle, PNG coverage percentages,
raising forensic rows, nav-height 4 generator rerun without diff.
