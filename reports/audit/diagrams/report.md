# Diagrams audit

| Field | Value |
| --- | --- |
| Prompt | `prompt.audit.diagrams` v1.2.0 |
| SCOPE | docs diagrams + related scripts |
| MODE | `propose-patches` (патчи **не** применялись) |
| LANGUAGE | ru |
| AUDIT_MODE | full |
| `REQUIRE_GH_TRACKING` | true |
| Base | worktree `E:\github\BioactivityDataAcquisition\.worktrees\arch-closeout` @ `6b9c73935f1b` ≡ `origin/main` |
| `surface_score` | **3** / 3 |
| Open PROVEN | **0** |
| Confirmed secret | **нет** |

## Executive summary

Канон — text-as-code Mermaid (`.mmd` / views `.mermaid`), SVG в git, PNG **намеренно gitignored** (DOC-GOV-02). CI: pinned `@mermaid-js/mermaid-cli@10.6.1` через `npm ci` + lockfile, **без** `npx -y`. Lint 492 файла, **0 ERROR**. C4 current-state описывает процессы, не Docker; observability optional (ADR-010). PlantUML/drawio/dot в `docs/` нет.

Повтор после closeout #10983/#10984/#10985 (PR #10986, squash `5cc40b73b250`; tip `6b9c73935f1b`). Три прошлых P3 **VERIFIED_ALREADY_RESOLVED**. Новых PROVEN нет.

| Check | Result |
| --- | --- |
| Inventory | 328 `.mmd`, 165 `.mermaid`, 492 SVG, 0 tracked PNG, 0 puml/drawio |
| ADR-040 baseline | **328** `.mmd` / **165** views = live; core 290 historical 2026-07-18 |
| `@nodes` | 328/328 canonical `.mmd` имеют `%% @nodes`; broken `% @nodes` = 0 |
| `current-state-diagrams.md` | `Last verified: '2026-09-24'` |
| `lint_diagrams.py docs/02-architecture/diagrams --json` | exit 0; 0 ERROR; 174 WARNING |
| `check-artifacts` visual-smoke (6 SVG) | exit 0 |
| setup-mermaid | pin 10.6.1, refuse other versions |
| `npx -y` in `scripts/diagrams` / `.github` | не найдено |
| local `mmdc` | не гонялся (smoke рендер не требовался) |
| GH | #10983 #10984 #10985 **CLOSED** 2026-09-24T10:57Z |
| Corpus test `test_governance_docs_match_active_diagram_counts` | исходник ожидает `(89,145,55,28,5,5,328,165)`; live counts совпадают. Pytest hung на import (`asyncio_default_fixture_loop_scope` / autoload); не блокирует FACT census |

## Surface score

**3** — источники в VCS, CI lint + path-filtered validate/smoke, nightly extended/broad, модель C4/слоёв согласована с ADR-010, measured census = live, `@nodes` на всём canonical corpus.

Не 2: regeneration/review не «только ручные» — PR lint/artifacts + nightly. Не 1: не binary-only. Не 0: C4/observability не толкают к плохому deploy.

Остаточный (не PROVEN): PR visual-smoke = 6 SVG; 174 WARNING; STALE-002 24 файла (~135d, ERROR на 150d); foundation↔views sync в ADR назван ручным.

## Findings

Открытых PROVEN нет.

### Prior — VERIFIED_ALREADY_RESOLVED

| ID | GH | Evidence now |
| --- | --- | --- |
| DIAG-ADR040-CENSUS | #10983 CLOSED | ADR-040 `Итого: **328 `.mmd**`; live rglob 328; families 89+145+55+28+5+5+template |
| DIAG-META-NODES | #10984 CLOSED | `mmd_with_nodes=328`, missing=0 |
| DIAG-CURRENT-STATE-STAMP | #10985 CLOSED | `Last verified: '2026-09-24'`; C4 containers = processes |

## Lint warnings (не отдельные issues)

174 WARNING: SIZE-002×99 (+2 vs prior: `state-machines/04` `@nodes=21`, `05` `@nodes=25` после D4), STALE-002×24, LINK-001×22, LABEL-001×20, GRAPH-001×4 (orphans: architecture/27 `Profiles`; foundation/28 и views/28 `EXEC, MAINT`; foundation/38 `PR`), SIZE-003×3, CLASS-003×2. ERROR=0. Не GH, пока не ERROR.

## Canonical source map

См. `canonical-source-map.md`. Рендер: `docs/02-architecture/diagrams/tooling/render.sh` / CI `docs.yml` + `diagram-nightly.yml` + `.github/actions/setup-mermaid`.

PNG: `.gitignore` `docs/02-architecture/diagrams/**/png/` — не finding.

## Proposed patches

Нет. Новые GH issues не создавать.

## Skips

- Полный локальный `mmdc` render / `git diff` SVG (политика CI path-filter; local CLI не требовался).
- `lint-budget` без JSON input (CI передаёт lint JSON).
- Docker/monitoring stack не поднимался.
- Pytest corpus: hung/config без autoload plugins; census сверен командой collector.

## Residual risk

STALE-002 (~135d) станет STALE-001 ERROR после 150 дней. Visual-smoke PR покрывает 6/492 SVG; nightly имеет extended/broad. GRAPH-001 orphans остаются WARNING.
