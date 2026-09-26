# CodeRabbit leaf scope matrix — 2026-08-05

**Issue:** #7714
**Epic:** #7688
**BASE_SHA:** `26ad7ad98e14f1435ffec01c4d41ee6c6664cd8d`
**Cap:** ≤300 files per leaf (CodeRabbit CLI hard limit)

## How to invoke a leaf

```bash
export PATH="$HOME/.local/bin:$PATH"
# export CODERABBIT_API_KEY=...  # from env / secret store
# coderabbit auth login --api-key "$CODERABBIT_API_KEY"
coderabbit auth status
cd /path/to/repo
coderabbit review --base main --dir src/bioetl/domain/ports --plain \
  | tee reports/quality/coderabbit/$(date -u +%Y%m%d)/review_S01-domain-ports.log
```

For half/residual selections: filter `git ls-files` output, or sparse-checkout those paths.
See `docs/03-guides/development/coderabbit-local-reviews.md`.

## Leaf scopes

| id | wave | files | under_cap | globs / selection |
| --- | --- | ---: | --- | --- |
| `S01-domain-aggregates` | A | 19 | True | `src/bioetl/domain/aggregates`;  |
| `S01-domain-behavior` | A | 52 | True | `src/bioetl/domain/behavior`;  |
| `S01-domain-composite` | A | 26 | True | `src/bioetl/domain/composite`;  |
| `S01-domain-config` | A | 12 | True | `src/bioetl/domain/config`;  |
| `S01-domain-contracts` | A | 23 | True | `src/bioetl/domain/contracts`;  |
| `S01-domain-control_plane` | A | 32 | True | `src/bioetl/domain/control_plane`;  |
| `S01-domain-entities` | A | 27 | True | `src/bioetl/domain/entities`;  |
| `S01-domain-exceptions` | A | 27 | True | `src/bioetl/domain/exceptions`;  |
| `S01-domain-filtering` | A | 13 | True | `src/bioetl/domain/filtering`;  |
| `S01-domain-lineage` | A | 6 | True | `src/bioetl/domain/lineage`;  |
| `S01-domain-mapping` | A | 15 | True | `src/bioetl/domain/mapping`;  |
| `S01-domain-models` | A | 7 | True | `src/bioetl/domain/models`;  |
| `S01-domain-normalization` | A | 88 | True | `src/bioetl/domain/normalization`;  |
| `S01-domain-ports` | A | 76 | True | `src/bioetl/domain/ports`;  |
| `S01-domain-registry` | A | 6 | True | `src/bioetl/domain/registry`;  |
| `S01-domain-residual-root` | A | 31 | True | `src/bioetl/domain`; set(domain)-packages |
| `S01-domain-run_reports` | A | 10 | True | `src/bioetl/domain/run_reports`;  |
| `S01-domain-schemas` | A | 49 | True | `src/bioetl/domain/schemas`;  |
| `S01-domain-transformations` | A | 5 | True | `src/bioetl/domain/transformations`;  |
| `S01-domain-types` | A | 24 | True | `src/bioetl/domain/types`;  |
| `S01-domain-validation` | A | 4 | True | `src/bioetl/domain/validation`;  |
| `S01-domain-value_objects` | A | 41 | True | `src/bioetl/domain/value_objects`;  |
| `S01-domain-workflow` | A | 6 | True | `src/bioetl/domain/workflow`;  |
| `S02-app-core` | A | 192 | True | `src/bioetl/application/core`;  |
| `S03-app-control-plane` | A | 140 | True | `src/bioetl/application/services/control_plane`;  |
| `S04-app-services-other` | A | 230 | True | `src/bioetl/application/services`; services-CP |
| `S05-app-pipelines` | B | 99 | True | `src/bioetl/application/pipelines`;  |
| `S06-infra-adapters` | A | 195 | True | `src/bioetl/infrastructure/adapters`;  |
| `S07-infra-http-storage` | B | 143 | True | `src/bioetl/infrastructure/http`, `src/bioetl/infrastructure/storage`, `src/bioetl/infrastructure/delta`;  |
| `S08-infra-observability` | C | 57 | True | `src/bioetl/infrastructure/observability`;  |
| `S09-composition` | A | 283 | True | `src/bioetl/composition`;  |
| `S10-interfaces-cli` | A | 104 | True | `src/bioetl/interfaces/cli`;  |
| `S11-interfaces-http` | A | 46 | True | `src/bioetl/interfaces/http`;  |
| `S12-tests-architecture-1` | F | 247 | True | `tests/architecture`; sorted[:half] |
| `S12-tests-architecture-2` | F | 247 | True | `tests/architecture`; sorted[half:] |
| `S13-tests-unit-domain-1` | F | 161 | True | `tests/unit/domain`; sorted[:half] |
| `S13-tests-unit-domain-2` | F | 162 | True | `tests/unit/domain`; sorted[half:] |
| `S14-tests-unit-application-composite` | F | 82 | True | `tests/unit/application/composite`;  |
| `S14-tests-unit-application-core` | F | 93 | True | `tests/unit/application/core`;  |
| `S14-tests-unit-application-pipelines` | F | 62 | True | `tests/unit/application/pipelines`;  |
| `S14-tests-unit-application-residual` | F | 13 | True | `tests/unit/application`; residual application tests |
| `S14-tests-unit-application-services` | F | 129 | True | `tests/unit/application/services`;  |
| `S15-tests-integration` | F | 219 | True | `tests/integration`;  |
| `S16-configs-quality` | B | 97 | True | `configs/quality`;  |
| `S17-docs-00-map.md` | E | 1 | True | `docs/00-project/00-map.md`;  |
| `S17-docs-NORMATIVE_SOURCES.md` | E | 1 | True | `docs/00-project/NORMATIVE_SOURCES.md`;  |
| `S17-docs-RULES.md` | E | 1 | True | `docs/00-project/RULES.md`;  |
| `S17-docs-TOOLS.md` | E | 1 | True | `docs/00-project/TOOLS.md`;  |
| `S17-docs-ai` | E | 290 | True | `docs/00-project/ai`;  |
| `S17-docs-architecture-index.md` | E | 1 | True | `docs/00-project/architecture-index.md`;  |
| `S17-docs-decisions` | E | 63 | True | `docs/02-architecture/decisions`;  |
| `S17-docs-extended-docs-index.md` | E | 1 | True | `docs/00-project/extended-docs-index.md`;  |
| `S17-docs-glossary.md` | E | 1 | True | `docs/00-project/glossary.md`;  |
| `S17-docs-governance` | E | 11 | True | `docs/00-project/governance`;  |
| `S17-docs-index.md` | E | 1 | True | `docs/00-project/index.md`;  |
| `S17-docs-rules-summary.md` | E | 1 | True | `docs/00-project/rules-summary.md`;  |
| `S18-grafana` | E | 156 | True | `grafana`, `docs/03-guides/dashboards`;  |
| `S19-scripts-engineering` | E | 216 | True | `scripts/engineering`;  |
| `S20-security-surface` | D | 12 | True | `tests/security`;  |

## Over-cap remaining

None — all listed leaves report `under_cap: true`.

## Wave mapping

| Wave | Issue | Leaf ids |
| --- | ---: | --- |
| A | #7690 | `S01-domain-aggregates`, `S01-domain-behavior`, `S01-domain-composite`, `S01-domain-config`, `S01-domain-contracts`, `S01-domain-control_plane`, `S01-domain-entities`, `S01-domain-exceptions`, `S01-domain-filtering`, `S01-domain-lineage`, `S01-domain-mapping`, `S01-domain-models`, `S01-domain-normalization`, `S01-domain-ports`, `S01-domain-registry`, `S01-domain-residual-root`, `S01-domain-run_reports`, `S01-domain-schemas`, `S01-domain-transformations`, `S01-domain-types`, `S01-domain-validation`, `S01-domain-value_objects`, `S01-domain-workflow`, `S02-app-core`, `S03-app-control-plane`, `S04-app-services-other`, `S06-infra-adapters`, `S09-composition`, `S10-interfaces-cli`, `S11-interfaces-http` |
| B | #7691 | `S05-app-pipelines`, `S07-infra-http-storage`, `S16-configs-quality` |
| C | #7692 | `S08-infra-observability` |
| D | #7693 | `S20-security-surface` |
| E | #7694 | `S17-docs-00-map.md`, `S17-docs-NORMATIVE_SOURCES.md`, `S17-docs-RULES.md`, `S17-docs-TOOLS.md`, `S17-docs-ai`, `S17-docs-architecture-index.md`, `S17-docs-decisions`, `S17-docs-extended-docs-index.md`, `S17-docs-glossary.md`, `S17-docs-governance`, `S17-docs-index.md`, `S17-docs-rules-summary.md`, `S18-grafana`, `S19-scripts-engineering` |
| F | #7695 | `S12-tests-architecture-1`, `S12-tests-architecture-2`, `S13-tests-unit-domain-1`, `S13-tests-unit-domain-2`, `S14-tests-unit-application-composite`, `S14-tests-unit-application-core`, `S14-tests-unit-application-pipelines`, `S14-tests-unit-application-residual`, `S14-tests-unit-application-services`, `S15-tests-integration` |

## Machine-readable summary

```json
{
  "base_sha": "26ad7ad98e14f1435ffec01c4d41ee6c6664cd8d",
  "cap": 300,
  "leaf_count": 59,
  "over_cap": [],
  "leaves": [
    {
      "id": "S01-domain-ports",
      "wave": "A",
      "globs": [
        "src/bioetl/domain/ports"
      ],
      "file_count": 76,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S01-domain-normalization",
      "wave": "A",
      "globs": [
        "src/bioetl/domain/normalization"
      ],
      "file_count": 88,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S01-domain-behavior",
      "wave": "A",
      "globs": [
        "src/bioetl/domain/behavior"
      ],
      "file_count": 52,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S01-domain-schemas",
      "wave": "A",
      "globs": [
        "src/bioetl/domain/schemas"
      ],
      "file_count": 49,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S01-domain-value_objects",
      "wave": "A",
      "globs": [
        "src/bioetl/domain/value_objects"
      ],
      "file_count": 41,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S01-domain-entities",
      "wave": "A",
      "globs": [
        "src/bioetl/domain/entities"
      ],
      "file_count": 27,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S01-domain-exceptions",
      "wave": "A",
      "globs": [
        "src/bioetl/domain/exceptions"
      ],
      "file_count": 27,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S01-domain-contracts",
      "wave": "A",
      "globs": [
        "src/bioetl/domain/contracts"
      ],
      "file_count": 23,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S01-domain-control_plane",
      "wave": "A",
      "globs": [
        "src/bioetl/domain/control_plane"
      ],
      "file_count": 32,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S01-domain-composite",
      "wave": "A",
      "globs": [
        "src/bioetl/domain/composite"
      ],
      "file_count": 26,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S01-domain-aggregates",
      "wave": "A",
      "globs": [
        "src/bioetl/domain/aggregates"
      ],
      "file_count": 19,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S01-domain-mapping",
      "wave": "A",
      "globs": [
        "src/bioetl/domain/mapping"
      ],
      "file_count": 15,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S01-domain-types",
      "wave": "A",
      "globs": [
        "src/bioetl/domain/types"
      ],
      "file_count": 24,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S01-domain-config",
      "wave": "A",
      "globs": [
        "src/bioetl/domain/config"
      ],
      "file_count": 12,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S01-domain-filtering",
      "wave": "A",
      "globs": [
        "src/bioetl/domain/filtering"
      ],
      "file_count": 13,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S01-domain-lineage",
      "wave": "A",
      "globs": [
        "src/bioetl/domain/lineage"
      ],
      "file_count": 6,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S01-domain-models",
      "wave": "A",
      "globs": [
        "src/bioetl/domain/models"
      ],
      "file_count": 7,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S01-domain-registry",
      "wave": "A",
      "globs": [
        "src/bioetl/domain/registry"
      ],
      "file_count": 6,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S01-domain-run_reports",
      "wave": "A",
      "globs": [
        "src/bioetl/domain/run_reports"
      ],
      "file_count": 10,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S01-domain-transformations",
      "wave": "A",
      "globs": [
        "src/bioetl/domain/transformations"
      ],
      "file_count": 5,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S01-domain-validation",
      "wave": "A",
      "globs": [
        "src/bioetl/domain/validation"
      ],
      "file_count": 4,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S01-domain-workflow",
      "wave": "A",
      "globs": [
        "src/bioetl/domain/workflow"
      ],
      "file_count": 6,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S01-domain-residual-root",
      "wave": "A",
      "globs": [
        "src/bioetl/domain"
      ],
      "file_count": 31,
      "under_cap": true,
      "notes": "residual domain paths",
      "selection": "set(domain)-packages"
    },
    {
      "id": "S02-app-core",
      "wave": "A",
      "globs": [
        "src/bioetl/application/core"
      ],
      "file_count": 192,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S03-app-control-plane",
      "wave": "A",
      "globs": [
        "src/bioetl/application/services/control_plane"
      ],
      "file_count": 140,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S05-app-pipelines",
      "wave": "B",
      "globs": [
        "src/bioetl/application/pipelines"
      ],
      "file_count": 99,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S06-infra-adapters",
      "wave": "A",
      "globs": [
        "src/bioetl/infrastructure/adapters"
      ],
      "file_count": 195,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S07-infra-http-storage",
      "wave": "B",
      "globs": [
        "src/bioetl/infrastructure/http",
        "src/bioetl/infrastructure/storage",
        "src/bioetl/infrastructure/delta"
      ],
      "file_count": 143,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S08-infra-observability",
      "wave": "C",
      "globs": [
        "src/bioetl/infrastructure/observability"
      ],
      "file_count": 57,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S09-composition",
      "wave": "A",
      "globs": [
        "src/bioetl/composition"
      ],
      "file_count": 283,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S10-interfaces-cli",
      "wave": "A",
      "globs": [
        "src/bioetl/interfaces/cli"
      ],
      "file_count": 104,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S11-interfaces-http",
      "wave": "A",
      "globs": [
        "src/bioetl/interfaces/http"
      ],
      "file_count": 46,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S15-tests-integration",
      "wave": "F",
      "globs": [
        "tests/integration"
      ],
      "file_count": 219,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S16-configs-quality",
      "wave": "B",
      "globs": [
        "configs/quality"
      ],
      "file_count": 97,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S18-grafana",
      "wave": "E",
      "globs": [
        "grafana",
        "docs/03-guides/dashboards"
      ],
      "file_count": 156,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S19-scripts-engineering",
      "wave": "E",
      "globs": [
        "scripts/engineering"
      ],
      "file_count": 216,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S20-security-surface",
      "wave": "D",
      "globs": [
        "tests/security"
      ],
      "file_count": 12,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S04-app-services-other",
      "wave": "A",
      "globs": [
        "src/bioetl/application/services"
      ],
      "file_count": 230,
      "under_cap": true,
      "notes": "excl CP",
      "selection": "services-CP"
    },
    {
      "id": "S12-tests-architecture-1",
      "wave": "F",
      "globs": [
        "tests/architecture"
      ],
      "file_count": 247,
      "under_cap": true,
      "selection": "sorted[:half]"
    },
    {
      "id": "S12-tests-architecture-2",
      "wave": "F",
      "globs": [
        "tests/architecture"
      ],
      "file_count": 247,
      "under_cap": true,
      "selection": "sorted[half:]"
    },
    {
      "id": "S13-tests-unit-domain-1",
      "wave": "F",
      "globs": [
        "tests/unit/domain"
      ],
      "file_count": 161,
      "under_cap": true,
      "selection": "sorted[:half]"
    },
    {
      "id": "S13-tests-unit-domain-2",
      "wave": "F",
      "globs": [
        "tests/unit/domain"
      ],
      "file_count": 162,
      "under_cap": true,
      "selection": "sorted[half:]"
    },
    {
      "id": "S14-tests-unit-application-core",
      "wave": "F",
      "globs": [
        "tests/unit/application/core"
      ],
      "file_count": 93,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S14-tests-unit-application-services",
      "wave": "F",
      "globs": [
        "tests/unit/application/services"
      ],
      "file_count": 129,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S14-tests-unit-application-composite",
      "wave": "F",
      "globs": [
        "tests/unit/application/composite"
      ],
      "file_count": 82,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S14-tests-unit-application-pipelines",
      "wave": "F",
      "globs": [
        "tests/unit/application/pipelines"
      ],
      "file_count": 62,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S14-tests-unit-application-residual",
      "wave": "F",
      "globs": [
        "tests/unit/application"
      ],
      "file_count": 13,
      "under_cap": true,
      "notes": "residual application tests"
    },
    {
      "id": "S17-docs-decisions",
      "wave": "E",
      "globs": [
        "docs/02-architecture/decisions"
      ],
      "file_count": 63,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S17-docs-00-map.md",
      "wave": "E",
      "globs": [
        "docs/00-project/00-map.md"
      ],
      "file_count": 1,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S17-docs-ai",
      "wave": "E",
      "globs": [
        "docs/00-project/ai"
      ],
      "file_count": 290,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S17-docs-architecture-index.md",
      "wave": "E",
      "globs": [
        "docs/00-project/architecture-index.md"
      ],
      "file_count": 1,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S17-docs-extended-docs-index.md",
      "wave": "E",
      "globs": [
        "docs/00-project/extended-docs-index.md"
      ],
      "file_count": 1,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S17-docs-glossary.md",
      "wave": "E",
      "globs": [
        "docs/00-project/glossary.md"
      ],
      "file_count": 1,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S17-docs-governance",
      "wave": "E",
      "globs": [
        "docs/00-project/governance"
      ],
      "file_count": 11,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S17-docs-index.md",
      "wave": "E",
      "globs": [
        "docs/00-project/index.md"
      ],
      "file_count": 1,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S17-docs-NORMATIVE_SOURCES.md",
      "wave": "E",
      "globs": [
        "docs/00-project/NORMATIVE_SOURCES.md"
      ],
      "file_count": 1,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S17-docs-rules-summary.md",
      "wave": "E",
      "globs": [
        "docs/00-project/rules-summary.md"
      ],
      "file_count": 1,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S17-docs-RULES.md",
      "wave": "E",
      "globs": [
        "docs/00-project/RULES.md"
      ],
      "file_count": 1,
      "under_cap": true,
      "notes": ""
    },
    {
      "id": "S17-docs-TOOLS.md",
      "wave": "E",
      "globs": [
        "docs/00-project/TOOLS.md"
      ],
      "file_count": 1,
      "under_cap": true,
      "notes": ""
    }
  ]
}
```
