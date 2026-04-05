# Scripts Layout

This directory uses a **canonical-by-domain** structure.

## Canonical Directories

- `scripts/ci/` — CI orchestration and reporting jobs.
- `scripts/dev/` — local developer workflows and setup (canonical entry points:
  `python -m scripts.dev ...`; `dev_setup.sh` remains a legacy placeholder only).
- `scripts/qa/` — architecture/quality/debt checks and reports.
- `scripts/docs/` — docs build, lint, drift checks, docs maintenance.
- `scripts/schema/` — schema/contracts/config invariants tooling.
- `scripts/data/` — data integrity, VCR policy, checksum/Delta utilities.
- `scripts/repo/` — repository hygiene and governance inventory.
- `scripts/ops/` — operational and platform support scripts.
- `scripts/diagnostics/` — manual probes, debug, one-off diagnostics.
- `scripts/migrations/active/` — active/repeatable migrations.
- `scripts/migrations/oneoff/` — one-time migration scripts.
- `scripts/diagrams/` — diagram quality/render tooling.

## Retained Support Directories

- `scripts/archive/` — retired or superseded scripts preserved for traceability.
- `scripts/baselines/` — baseline/reference artifacts used by selected quality workflows.
- `scripts/ai/` — internal agent-launcher compatibility scripts retained outside
  the canonical grouped entrypoint surface.

## Root Directory Policy

The `scripts/` root is intentionally minimal. Canonical long-lived scripts live
in the domain directories above, while the root retains only:

- launcher/catalog files (`run.py`, `catalog.yaml`, package markers, this README)
- compatibility wrappers (`run_pytest.sh`, `run_pytest.ps1`)
- a small number of legacy bridge entry points still referenced by docs/tests
  (`generate_architecture_dependency_map.py`, `rerender_grafana_screenshots.py`)

Canonical root-level direct paths retained for compatibility:

- `scripts/run_pytest.sh`
- `scripts/run_pytest.ps1`
- `scripts/generate_architecture_dependency_map.py`
- `scripts/rerender_grafana_screenshots.py`

Inventory/governance should treat these root-level paths as legacy
compatibility entrypoints unless a live CI/build/agent caller still depends on
them directly.

Rules:

- New scripts must be placed in the appropriate canonical subdirectory.
- Do not add new long-lived scripts to `scripts/` root unless they are
  explicitly approved as compatibility wrappers.

## Unified Entry Points

Each canonical directory provides a `__main__.py` dispatcher, so scripts can be
invoked by domain and command name without knowing exact filenames:

```bash
python -m scripts.<group> <command> [args...]
python -m scripts.<group> --help          # list available commands
```

Available groups and example commands:

| Group         | Example                                               | Description            |
| ------------- | ----------------------------------------------------- | ---------------------- |
| `repo`        | `python -m scripts.repo check-inventory --check`      | Repository governance  |
| `ci`          | `python -m scripts.ci quality-gate`                   | CI orchestration       |
| `qa`          | `python -m scripts.qa check-c901 --target src/bioetl` | Quality checks         |
| `schema`      | `python -m scripts.schema validate-configs`           | Schema validation      |
| `data`        | `python -m scripts.data check-vcr-naming`             | Data integrity         |
| `docs`        | `python -m scripts.docs check-drift`                  | Documentation checks   |
| `diagrams`    | `python -m scripts.diagrams lint`                     | Diagram tooling        |
| `ops`         | `python -m scripts.ops salt-rotate`                   | Operational automation |
| `dev`         | `python -m scripts.dev run-tests unit`                | Developer workflows    |
| `diagnostics` | `python -m scripts.diagnostics cleanup`               | Debug & diagnostics    |

Each script also remains standalone-executable:

```bash
python scripts/qa/check_c901_baseline.py --target src/bioetl  # still works
```

## Inventory Governance

- Check inventory drift:
  - `python -m scripts.repo check-inventory --check --manifest configs/quality/scripts_inventory_manifest.json`
- Update inventory manifest:
  - `python scripts/repo/check_scripts_inventory.py --update --manifest configs/quality/scripts_inventory_manifest.json`
- Validate lifecycle coverage for non-active scripts:
  - `python scripts/repo/check_scripts_inventory.py --check-lifecycle --forbid-evaluate-active --lifecycle-registry configs/quality/scripts_lifecycle_registry.json`
  - When inventory is fully active-only, `configs/quality/scripts_lifecycle_registry.json` may legitimately contain `entries: {}` and this check should still pass.
- Validate catalog governance policy:
  - `python -m scripts.repo check-catalog --catalog scripts/catalog.yaml`
- Run all repo checks:
  - `python -m scripts.repo all`

## Architecture Drift Repair

Use project-local commands for architecture docs and compatibility drift:

```bash
uv run python -m pytest tests/architecture/test_architecture_dependency_docs_drift.py -q
uv run python -m scripts.qa report-dep-map --update
uv run python -m pytest tests/architecture/test_compatibility_facade_inventory.py tests/architecture/test_documentation_sync.py -q
uv run python -m scripts.docs check-links --configs
```

Canonical repair flow:

1. `dependency-map drift` -> regenerate only through `scripts/qa/generate_architecture_dependency_map.py --update`.
1. `compatibility/documentation drift` -> verify against `docs/02-architecture/07-compatibility-facade-inventory.md` and rerun the targeted architecture tests above.
1. Historical files under `docs/reports/` explain past waves, but active repair guidance lives in `docs/02-architecture/**`, `docs/03-guides/**`, and this `scripts/README.md`.

## Launcher

Use `scripts/run.py` for discovery and consistent invocation:

- `python scripts/run.py list`
- `python scripts/run.py find quality`
- `python scripts/run.py exec qa check_c901_baseline -- --help`

## Command Reference

### scripts.repo

```
check-inventory    Check scripts inventory drift
check-catalog      Validate catalog governance policy
check-versions     Check version consistency across project files
check-cleanliness  Audit repository root layout allowlist
all                Run all checks sequentially
```

### scripts.ci

```
run-tests          Run pytest with resilient retry logic
quality-gate       Integral quality gate for CI
e2e-skip-rate      Check E2E matrix skip rate against threshold
e2e-rerun          Check E2E rerun stability
debt-report        Generate weekly quality debt report
apply-ci-fixes     Apply one-off hosted GitHub workflow fixes
```

### scripts.qa

```
check-naming       Naming convention audit
check-architecture Infrastructure architecture compatibility check
check-app-deps     Application dependency compatibility check
check-constructor-args Constructor argument compatibility check
check-c901         C901 complexity baseline enforcement
check-naming-pkg   Package naming consistency check
check-exemptions   Quality exemptions audit
generate-debt-tasks Generate architecture debt task backlog from registry
reduce-architecture-debt Build execution plan from latest architecture debt tasks
check-terminology  Terminology linting
report-dep-map     Generate/check architecture dependency map
report-vcr-metadata Generate/check canonical VCR metadata catalog
report-hotspots    Generate performance hotspot degradation report
report-duplication-baseline Generate report-only duplication baseline
analyze-duplicate-functions Analyze duplicate function names across selected code areas
calibrate-hotspots Calibrate hotspot budgets
```

Notes:

- `check-c901` is a blocking complexity baseline gate for new structural debt.
- `generate-debt-tasks` is the canonical backlog generator for architecture metric exemptions.
- `reduce-architecture-debt` is the canonical execution-plan builder consumed by the debt-reduction agent.
- `report-hotspots` and `calibrate-hotspots` are **performance** tools backed by benchmark observations. They do **not** describe the repo-wide source-tree size tail.
- `report-duplication-baseline` is a **report-only structural** tool for duplication visibility in `composition` and `application`. It is intended to create a baseline artifact before any blocking ratchet is considered.
- `scripts/qa/report_duplication_baseline.py` is the canonical direct script path behind `python -m scripts.qa report-duplication-baseline`.
- In governance discussions, distinguish:
  - `exemption debt`: counts from `configs/quality/architecture_metric_exemptions.yaml` that are enforced by the debt scorecard
  - `hotspot inventory`: raw source-tree size/LOC measurements used for analysis and prioritization

### Source-tree hotspot inventory

When you need a reproducible raw snapshot of large Python modules under `src/bioetl`, use a local command like this:

```bash
uv run python - <<'PY'
from pathlib import Path

root = Path("src/bioetl")
files = [p for p in root.rglob("*.py") if "__pycache__" not in p.parts]
rows: list[tuple[str, int, int, str]] = []
for path in files:
    text = path.read_text(encoding="utf-8")
    loc = len(text.splitlines())
    size = path.stat().st_size
    layer = path.relative_to(root).parts[0]
    rows.append((path.as_posix(), size, loc, layer))

size_hotspots = [r for r in rows if r[1] > 10240]
loc_hotspots = [r for r in rows if r[2] > 350]
overlap = [r for r in rows if r[1] > 10240 and r[2] > 350]

print(f"total_files={len(rows)}")
print(f"size_hotspots_gt_10kb={len(size_hotspots)}")
print(f"loc_hotspots_gt_350={len(loc_hotspots)}")
print(f"overlap={len(overlap)}")
PY
```

Use this output as an evidence/inventory snapshot. Do not interpret it as equivalent to scorecard exemption debt unless a governance policy explicitly says so.

High-frequency sync commands:

```bash
uv run python -m scripts.qa report-dep-map --check
uv run python -m scripts.qa report-dep-map --update
uv run python -m scripts.qa report-vcr-metadata --check
uv run python -m scripts.qa report-vcr-metadata --update
uv run python -m scripts.docs check-links --configs
```

### scripts.schema

```
check-invariants   Validate config CI invariants
check-config-paths Check for legacy dq/filter config path references
generate-pipeline  Generate pipeline JSON schema
generate-artifacts Generate schema artifacts
generate-pubtype   Generate publication type classification artifacts
generate-contracts Generate contracts
generate-config-matrix Generate unified entity/composite config comparison matrix
validate-configs   Validate unified pipeline YAML configs
validate-unified-configs Validate legacy unified entity config structure
analyze-gaps       Config gap analysis
```

### scripts.data

```
check-vcr-placement  Block VCR cassette anti-patterns
check-vcr-naming     Enforce VCR filename policy
check-delta          Check Delta Lake integrity
check-data-dir       Validate data directory structure
vacuum               Vacuum Delta tables
checksums            Generate/verify file checksums
dq-baseline          Update DQ baseline metrics
report-null-fields   Extract null field statistics
report-content-hash  Generate content hash comparison report
```

### scripts.docs

```
check-links        Check documentation links, specs, and configs
check-drift        Check documentation drift
check-docstrings   Check docstring coverage
check-kpi          Report documentation KPI metrics
fix-links-auto     Auto-fix broken documentation links
fix-links-explicit Fix documentation links with explicit rules
fix-link-warnings  Fix link warnings in specified files
audit-sentence     Sentence-level documentation audit
```

### scripts.diagrams

```
lint               Lint architecture diagrams
lint-summarize     Summarize diagram lint report
lint-budget        Enforce diagram quality budget
check-artifacts    Check diagram artifact manifest
check-quality-gates Check diagram quality gates
check-visual-smoke Visual smoke test for diagrams
check-svg-text     Check SVG text visibility
check-class-methods Check class method render integrity
check-pdf-bounds   Check PDF image bounds
check-padding      Report diagram padding issues
fix-operators      Fix Mermaid operators
fix-svg-text       Add SVG text fallback
fix-svg-styles     Inject SVG styles
fix-foreign-object Strip SVG foreignObject elements
fix-orphans        Prune orphan nodes in diagrams
fix-sizes          Uniform diagram sizes
fix-pagebreaks     Fix pagebreaks in bundles
render-pdf         Generate architecture PDF bundle
render-pdf-desc    Generate PDF with descriptions
render-docx        Generate DOCX with descriptions
render-views       Generate views bundle
nightly            Run full diagram nightly suite
```

### scripts.ops

```
salt-rotate        Rotate PII hashing salt
fix-grafana        Fix Grafana dashboard configurations
wsl-proxy          Start WSL proxy helper
setup-plugins      Setup plugins (shell)
setup-agents       Setup agents (shell)
setup-skills       Setup skills (shell)
check-skills       Check AI skills layout (shell)
check-mirror       Check skills mirror sync (shell)
check-mcp          Check MCP server configuration (shell)
deploy             Deploy BioETL (shell)
delete-branches    Delete stale git branches (shell)
```

### scripts.dev

```
setup              Full developer environment setup (shell)
install-deps       Install project dependencies
run-tests          Run tests
mock-metrics       Start mock metrics server
test-changed       Run tests for changed files only
setup-mcp          Setup Copilot/Codex MCP integration
```

### scripts.diagnostics

```
cleanup            Clean caches, build artifacts, and temp files
cleanup-audit      Consolidated cleanup and quality audit
audit-structure    Validate project structure against file policy
ast-inventory      AST-based code inventory
debug-pandera      Debug Pandera schema validation
debug-storage      Debug storage health checks
inspect-vcr        Temporary VCR cassette inspector
```
