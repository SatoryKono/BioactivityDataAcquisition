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

## Root Directory Policy

The `scripts/` root contains only the launcher (`run.py`) and catalog metadata.
All scripts live in canonical subdirectories listed above.

Rules:
- New scripts must be placed in the appropriate canonical subdirectory.
- Do not add scripts to `scripts/` root.

## Unified Entry Points

Each canonical directory provides a `__main__.py` dispatcher, so scripts can be
invoked by domain and command name without knowing exact filenames:

```bash
python -m scripts.<group> <command> [args...]
python -m scripts.<group> --help          # list available commands
```

Available groups and example commands:

| Group | Example | Description |
|-------|---------|-------------|
| `repo` | `python -m scripts.repo check-inventory --check` | Repository governance |
| `ci` | `python -m scripts.ci quality-gate` | CI orchestration |
| `qa` | `python -m scripts.qa check-c901 --target src/bioetl` | Quality checks |
| `schema` | `python -m scripts.schema validate-configs` | Schema validation |
| `data` | `python -m scripts.data check-vcr-naming` | Data integrity |
| `docs` | `python -m scripts.docs check-drift` | Documentation checks |
| `diagrams` | `python -m scripts.diagrams lint` | Diagram tooling |
| `ops` | `python -m scripts.ops salt-rotate` | Operational automation |
| `dev` | `python -m scripts.dev setup --quick` | Developer workflows |
| `diagnostics` | `python -m scripts.diagnostics cleanup` | Debug & diagnostics |

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
- Validate catalog governance policy:
  - `python -m scripts.repo check-catalog --catalog scripts/catalog.yaml`
- Run all repo checks:
  - `python -m scripts.repo all`

## Architecture Drift Repair

Use project-local commands for architecture docs and compatibility drift:

```bash
./.venv/Scripts/python.exe -m pytest tests/architecture/test_architecture_dependency_docs_drift.py -q
./.venv/Scripts/python.exe scripts/qa/generate_architecture_dependency_map.py --update
./.venv/Scripts/python.exe -m pytest tests/architecture/test_compatibility_facade_inventory.py tests/architecture/test_documentation_sync.py -q
./.venv/Scripts/python.exe scripts/docs/check_doc_links.py --configs
```

Canonical repair flow:

1. `dependency-map drift` -> regenerate only through `scripts/qa/generate_architecture_dependency_map.py --update`.
2. `compatibility/documentation drift` -> verify against `docs/02-architecture/07-compatibility-facade-inventory.md` and rerun the targeted architecture tests above.
3. Historical files under `docs/reports/` explain past waves, but active repair guidance lives in `docs/02-architecture/**`, `docs/03-guides/**`, and this `scripts/README.md`.

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
```

### scripts.qa

```
check-naming       Naming convention audit
check-c901         C901 complexity baseline enforcement
check-naming-pkg   Package naming consistency check
check-exemptions   Quality exemptions audit
check-terminology  Terminology linting
report-dep-map     Generate/check architecture dependency map
report-hotspots    Generate hotspot degradation report
calibrate-hotspots Calibrate hotspot budgets
```

High-frequency sync commands:

```bash
python scripts/qa/generate_architecture_dependency_map.py --check
python scripts/qa/generate_architecture_dependency_map.py --update
python scripts/docs/check_doc_links.py --configs
```

### scripts.schema

```
check-invariants   Validate config CI invariants
check-config-paths Check for legacy dq/filter config path references
generate-pipeline  Generate pipeline JSON schema
generate-artifacts Generate schema artifacts
generate-pubtype   Generate publication type classification artifacts
generate-contracts Generate contracts
validate-configs   Validate unified pipeline YAML configs
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
test-changed       Run tests for changed files only (shell)
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
