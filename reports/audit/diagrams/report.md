# Audit: diagrams

- **domain_id:** `diagrams`
- **prompt_id:** `prompt.audit.diagrams`
- **mode:** `audit` / `AUDIT_MODE=full`
- **language:** `ru`
- **base:** `main`
- **repo:** `SatoryKono/BioactivityDataAcquisition`
- **date:** 2026-08-21
- **surface_score:** `2` (acceptable — text-as-code + pinned render + CI; local model/drift gaps remain)
- **blocked:** `false`

## Executive summary

Канонические диаграммы BioETL живут как text-as-code (Mermaid `.mmd` / `.mermaid`) под `docs/02-architecture/diagrams/`, рендерятся pinned `@mermaid-js/mermaid-cli@10.6.1` (lockfile в `.github/actions/setup-mermaid`, Docker fallback `minlag/mermaid-cli:10.6.1`), и закрываются CI (`docs.yml`: syntax/lint/render/drift; `diagram-nightly.yml`: smoke/budget/canary). PNG не трекается (DOC-GOV-02). PlantUML / Graphviz / drawio как источники не найдены.

Контроль зрелый, но не score 3: (1) runtime-диаграмма observability всё ещё ведёт logs/traces в Grafana после вывода Loki/Tempo; (2) security-диаграмма рендерит безымянные узлы `BW`/`SW`/`HASHED`; (3) skill `technical-designer-mermaid` указывает на несуществующий `mmd-diagrams/`; (4) secondary families (`providers/`, `sequence/`, `state-machines/`) не входят в PR drift-gate и pre-commit globs; (5) generated `90-pkg-*` class slices не имеют CI `--check`.

P0 нет. P1: 1. Proven findings: 8.

## Surface score legend

| Score | Meaning (this domain) |
| ---: | --- |
| 3 | Text source in VCS; deterministic render; CI validation; model matches system |
| 2 | Diagrams current; some regeneration/review still manual |
| 1 | Binary-only, unclear source, or regular drift |
| 0 | Key diagram wrong enough to cause a bad security/deploy decision |

**Mapping used:** domain card `prompt.audit.diagrams` surface score (0–3), not 0–5 dimension average.

## Inventory (SCOPE)

| Family | Format | Count (sources) | Sibling SVG | Classification |
| --- | --- | ---: | --- | --- |
| `architecture/` | `.mmd` | 89 | 89 | context/container/component/data/runtime |
| `class-diagrams/` | `.mmd` | 94 | 94 | class (19 curated + sandbox + 74 `90-pkg-*`) |
| `foundation/` | `.mmd` | 55 | 55 | historical/system reference |
| `_template.mmd` | `.mmd` | 1 | n/a | scaffolding (lint-excluded) |
| `views/` | `.mermaid` | 165 | 165 | decomposed review views |
| `sequence/` | `.mmd` | 5 | 5 | sequence/runtime |
| `state-machines/` | `.mmd` | 5 | 5 | state |
| `providers/{7}/` | `.mmd` | 28 | 28 | provider data flows |
| **Total sources** | | **442** | **441 SVG** | PNG gitignored |

ADR-040 / `diagrams-index.md` baseline (guarded by `tests/architecture/test_diagram_corpus_regression_guards.py`): 89+94+55+1 = **239** `.mmd` + **165** `.mermaid`. Secondary families (+38 `.mmd`) есть в дереве и в README, но не в ADR-040 inventory counts.

Other formats:

- PlantUML / `.puml` / drawio / Graphviz source diagrams: **не найдены** (кроме CLI `--format dot` для lineage, не architecture SSOT).
- Embedded Mermaid in active `docs/02-architecture/**/*.md`: C4/context pages (`current-state-diagrams.md`, `system-context.md`, `observability-layers.md`, …). CI `validate-mermaid` uses `--include-embedded`.
- Renderer pin: `10.6.1` in `setup-mermaid/package.json` + `mmdc_wrapper.sh`. **No `npx -y` in `.github/workflows`.**

## Checks run / skipped

| Check | Result |
| --- | --- |
| File inventory (`docs/02-architecture/diagrams/**`, `scripts/diagrams/**`) | done |
| Format search (PlantUML/drawio/dot/mermaid/npx) | done |
| ADR-040, POL-LLM-DIAGRAMS-001, render-retention, README | done |
| CI: `docs.yml`, `diagram-nightly.yml`, `setup-mermaid` | done |
| Pre-commit diagram hooks | done |
| Architecture tests for corpus/drift | done |
| Observability/security model vs ADR-010 / current-state | done |
| Secrets/internal endpoints in `.mmd`/`.mermaid` | no secret values; `api_key` is field name only |
| `python -m scripts.diagrams lint` | **skipped** (no shell in this agent) |
| `validate_mermaid_syntax.sh` / `render.sh` | **skipped** (no shell) |
| Memory `pre-task`/`post-task` | **skipped** (no shell) |

## Findings

| ID | Pri | Status | Path | Observation |
| --- | --- | --- | --- | --- |
| DIAG-001 | P1 | PROVEN | `architecture/22-data-operations-observability.mmd:67-69` | Logs and traces sink into Grafana after Loki/Tempo retirement |
| DIAG-002 | P2 | PROVEN | `architecture/17-security-pii-audit.mmd:39,71` | Unlabeled `HASHED`/`BW`/`SW` nodes in source and tracked SVG |
| DIAG-003 | P2 | PROVEN | `.codex`/`.junie` `technical-designer-mermaid/SKILL.md:72` | Skill still targets `mmd-diagrams/` (removed canonical root) |
| DIAG-004 | P2 | PROVEN | `docs.yml` drift globs + pre-commit `files:` | `providers/`/`sequence/`/`state-machines/` outside PR SVG-drift gate |
| DIAG-005 | P2 | PROVEN | `generate_package_family_class_diagrams.py` + `90-pkg-*` | Generator `--check` not in CLI/CI; `@date 2026-03-27` |
| DIAG-006 | P3 | PROVEN | `diagrams/README.md:101-107` | Links to gitignored `**/png/INDEX.md` |
| DIAG-007 | P3 | PROVEN | `ADR-040` inventory | Secondary families omitted from measured baseline counts |
| DIAG-008 | P3 | PROVEN | `09-observability-stack.mmd:72` / `09b` | Grafana shown as required external, not optional (ADR-010) |

## What is healthy

- Canonical source is Mermaid text, not PNG-first (anti-pattern avoided).
- Renderer version pinned; CI install is lockfile-backed (`npm ci`), not bare `npx -y`.
- SVG tracked; PNG gitignored; PR `check-diagram-drift` for primary families.
- Lint policy (SIZE/META/COLOUR/GRAPH/NBSP/STALE) + quality budget + nightly canary.
- Hexagonal overview does not show `domain -> infrastructure` (implements-ports only).
- No Redis/Loki/Tempo/Quarantine Explorer nodes in `.mmd` corpus (grep).
- `90-pkg-*` slices stay ≤30 nodes (`MAX_SLICE_NODES`) — not a full-monorepo class dump.

## Top remediations (MODE=full; not applied)

1. Rewrite `22-data-operations-observability.mmd`: metrics → optional Prometheus/Grafana; logs → files/CLI; traces → OTLP/console. Re-render SVG.
2. Define labeled nodes `HASHED`, `BronzeWriter`, `SilverWriter` in `17-security-pii-audit.mmd`; re-render SVG.
3. Replace `mmd-diagrams/` with `diagrams/` in `.codex` and `.junie` `technical-designer-mermaid` skills (then docs mirrors).
4. Extend `check-diagram-drift` and pre-commit `files:` to `providers/**`, `sequence/`, `state-machines/`.
5. Add `python -m scripts.diagrams` command + CI `--check` for `generate_package_family_class_diagrams.py`.
6. Drop dead `png/INDEX.md` links from `diagrams/README.md` (or point to render-retention policy).
7. Add sequence/providers/state-machines counts to ADR-040 / `diagrams-index.md` (keep architecture test in sync).
8. Label Grafana as optional in `09` / `09b`.

## Kit extras

- `diagram-inventory.csv`
- `render-failures.txt`
- `diagram-code-drift.csv`
- `canonical-source-map.md`

## Debt outcome

`unchanged` (audit-only; no code edits; no debt budget changes).
