# BioETL Requirements

Version: 1.12.3
Status: active
Aligned with: RULES.md v6.1.9 ([source](../00-project/RULES.md); architecture stamp re-check 2026-08-10)
Last verified: 2026-08-10

## Purpose and authority

This document is the entry point for testable BioETL requirements. It does not
replace the normative rules or accepted architecture decisions:

1. [`RULES.md`](../00-project/RULES.md) owns normative MUST/SHOULD/MAY policy.
2. Accepted [ADR](../02-architecture/decisions/) record architecture decisions.
3. This catalog projects those sources into stable requirement identifiers and
   executable verification surfaces.

When this catalog conflicts with code, configuration, an accepted ADR, or
`RULES.md`, investigate the conflict against the precedence defined in
[`AGENTS.md`](../../AGENTS.md); this document must not be used to override the
runtime or normative source.

## Machine-readable traceability

The complete catalog contains **168 active requirements**:

- 147 `MUST`;
- 16 `MUST NOT`;
- 4 `SHOULD`;
- 1 `MAY`.

Every requirement has its modality, `RULES.md` section, ADR references,
verification method, executable surface, and reconciliation status in:

- [requirements-traceability-crosswalk.csv](traceability/requirements-traceability-crosswalk.csv)
- [requirements-traceability-crosswalk.md](traceability/requirements-traceability-crosswalk.md)

The CSV is the exhaustive row-level traceability artifact. The Markdown
crosswalk records its snapshot, counts, and reconciliation notes. A requirement
is not considered fully traceable merely because an ADR is listed here: its CSV
row must also identify a verification method or executable surface.

## Coverage by normative area

| Normative area | Requirements | Primary `RULES.md` sections | Representative decisions and evidence |
| --- | ---: | --- | --- |
| Architecture and layers | 7 | §1 | ADR-005, ADR-048; `tests/architecture/` |
| Medallion, data, DQ, replay, composites | 51 | §2, §6.1 | ADR-002, ADR-014, ADR-018, ADR-026, ADR-045, ADR-050; `configs/entities/`, `configs/composites/`, `tests/contract/` |
| Errors and observability | 39 | §3 | ADR-006, ADR-007, ADR-016, ADR-017, ADR-019; `src/bioetl/infrastructure/observability/`, `grafana/` |
| Code and testing | 25 | §4 | ADR-032, ADR-042, ADR-049; `pyproject.toml`, `tests/` |
| Operations and control plane | 28 | §5, §6.1 | ADR-010, ADR-044, ADR-046, ADR-047; `src/bioetl/domain/control_plane/run_manifest.py`, `src/bioetl/domain/control_plane/run_ledger.py`, `configs/workflows/` |
| Documentation | 2 | §6 | `scripts/docs/`, documentation CI checks |
| Contracts and change management | 6 | §8 | ADR-037, ADR-038, ADR-039, ADR-048; `configs/base/contract_registry.yaml`, `reports/quality/contract-coverage-matrix.json` |
| Developer experience | 5 | §9 | `Makefile`, `scripts/engineering/dev/` |
| Dependencies | 2 | Appendix B | `pyproject.toml`, `uv.lock`, dependency audit workflow |
| Provider health | 3 | §1.1.2, §3.5 | provider adapters and health-check tests |

Counts in this table are derived from the current traceability crosswalk. They
must be updated together with that artifact.

## Critical architecture requirements

| Requirement family | Normative rule | Decision | Runtime/config evidence | Verification evidence |
| --- | --- | --- | --- | --- |
| `REQ-ARCH-*` | Pure domain, inward dependencies, ports and composition-only DI (`RULES.md` §1) | ADR-005, ADR-048 | `src/bioetl/domain/ports/`, `src/bioetl/composition/` | `tests/architecture/` import, port, DI, and domain-purity guards |
| `REQ-DATA-*`, `REQ-DELTA-*` | Bronze append-only; Silver/Gold Delta only (no raw Parquet). The exact final DataFrame MUST pass Pandera validation after the last transformation and immediately before persistence; any post-validation transformation requires re-validation before write. Silver validation MUST cover schema, nullability, types, and applicable DQ/business constraints; invalid rows stop the write or enter quarantine. Gold validation is strict/fail-closed (`strict=True`). (`RULES.md` §2.1) | ADR-001, ADR-002, ADR-018 | `src/bioetl/infrastructure/storage/`, `src/bioetl/domain/schemas/` | `tests/contract/test_gold_*.py`, storage integration tests, Silver DQ/contract suites |
| `REQ-DQ-*` | DQ contracts, thresholds, quarantine, and bounded metrics (`RULES.md` §2.8, §3.4) | ADR-027, ADR-045 | `configs/quality/`, `src/bioetl/domain/behavior/dq_rule_evaluator.py`, `src/bioetl/domain/value_objects/dq_report.py` | DQ contract, golden, and observability tests |
| `REQ-BACKFILL-*`, `REQ-CLEAR-*` | Deterministic replay, exclusive rebuild, explicit clear lifecycle (`RULES.md` §2.4, §6.1) | ADR-014, ADR-044, ADR-046 | run manifest, ledger, checkpoint and replay services | replay, reproducibility, lifecycle, and lock tests |
| `REQ-COMPOSITE-*` | Composite DAG and deterministic merge policy (`RULES.md` §2.9) | ADR-026 | `configs/composites/`, `src/bioetl/domain/composite/` | composite contract, dependency, and golden tests |
| `REQ-OBS-*`, `REQ-HEALTH-*` | Structured logs, bounded metrics, tracing, provider health (`RULES.md` §3.2–§3.5) | ADR-006, ADR-017, ADR-019 | observability ports/adapters, Prometheus rules, dashboards | observability architecture and metric-governance tests |
| `REQ-TEST-*`, `REQ-GOV-*` | Deterministic tests and change-set gates (`RULES.md` §4.2–§4.5) | ADR-042, ADR-049 | `pyproject.toml`, quality configs and reports | architecture, unit, integration, contract, golden and replay suites |
| `REQ-CONTRACT-*` | Versioned schemas and synchronized generated artifacts (`RULES.md` §8.1) | ADR-037, ADR-038, ADR-039, ADR-048 | contract registry, Pandera sources, published JSON schemas | contract-registry and generated-artifact drift tests |

`REQ-DQ-002`: Метрика `bioetl_dq_validation_score` с bounded labels `pipeline`, `entity`
MUST сохранять этот label contract; детализация по columns/checks публикуется
отдельными метриками или reports.

## ADR coverage

The catalog explicitly covers the current architecture through ADR-052,
including:

- ADR-044 — Run Manifest and Run Ledger control plane;
- ADR-045 — DQ Contract System;
- ADR-046 — checkpoint versus ledger-based resume;
- ADR-047 — declarative workflow control plane;
- ADR-048 — domain schema boundary and Pandera runtime compatibility;
- ADR-049 — context-aware LOC target policy;
- ADR-050 — Silver structural and Gold semantic filter boundary;
- ADR-051 — QuarantineEntry wide constructor as intentional aggregate surface;
- ADR-052 — `bioetl.infrastructure.config` package root as permanent public API.
- ADR-057 — deterministic Settings/provider authority and versioned raw,
  resolved, and effective configuration identity.

ADR presence is not proof of implementation. Use the executable evidence in the
traceability CSV and inspect the cited code, configuration, and tests.

## Maintenance rules

When a normative requirement changes:

1. update `RULES.md` or the owning ADR first;
2. update the matching row in the traceability CSV;
3. update the crosswalk snapshot/counts and this index if category totals or
   representative evidence changed;
4. update code/configuration and its regression test;
5. run documentation links/version checks and the relevant architecture,
   contract, golden, replay, or configuration tests.

Technical-debt budgets, exemption limits, and hotspot thresholds must not be
increased as a documentation remedy.

## Version history

- v1.12.3 (2026-08-10): normative traceability advanced through `RULES.md`
  v6.1.9 and ADR-057 (deterministic runtime config authority and identity).
- v1.12.2 (2026-08-09): normative traceability advanced through `RULES.md`
  v6.1.8 and ADR-056 (Proof-or-Stop lifecycle control).
- v1.12.1 (2026-07-28): ADR coverage extended through ADR-052 (ARCH-REF-07).
- v1.12 (2026-07-23): restored the requirements entry point and explicit
  traceability to all 168 crosswalk rows, `RULES.md` v6.1.8, ADR-001…ADR-056,
  runtime/configuration surfaces, and executable evidence.
- v6.1 (historical compact catalog): listed selected ADRs but did not provide
  complete requirement-to-evidence traceability.
