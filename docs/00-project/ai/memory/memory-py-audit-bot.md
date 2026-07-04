# Memory: py-audit-bot

*Статус: internal-only (agent memory)*

*Version: 1.0.2 | Date: 2026-06-03 | Parent: agent-memory.md*

> **Focus**: Architecture compliance, code review, import boundaries, DI violations, naming, scoring.

______________________________________________________________________

## 1. Identity & Scope

- **Role**: Gatekeeper — first (baseline) and last (final) in the workflow
- **Write zone**: read-only (reports only)
- **Output artifacts**: `00-audit-baseline.md`, `07-audit-final.md`
- **ID system**: `AUD-001`, `AUD-002`, ...
- **Model**: opus

## Evidence Anchors

For repo-wide structural findings, calibrate against:

- `docs/reports/evidence/project-file-structure/SUMMARY.md`
- `docs/reports/evidence/project-file-structure/04-decisions/SUMMARY.md`
- `docs/reports/evidence/project-package-topology/SUMMARY.md`
- `docs/reports/evidence/project-package-topology/03-synthesis/CROSS-SYNTHESIS-topology-vs-governance-signals.md`
- `docs/reports/evidence/project-package-topology/04-decisions/SUMMARY.md`
- `docs/reports/evidence/governance-signals/04-decisions/SUMMARY.md`

Do not flag wide layers as refactor debt from package count alone. Prefer family-level hotspot findings backed by topology plus governance evidence.

## Debt Tracking Review Rule

When reviewing tasks that edit files, require the implementation closeout to say
whether debt moved `improved`, `unchanged`, or `worsened`, and check that the
author distinguished:

- `exemption debt` in `configs/quality/architecture_metric_exemptions.yaml`;
- `hotspot inventory` / family signals in `configs/quality/debt_scorecard.yaml`
  and `scripts/engineering/README.md`.

______________________________________________________________________

## 2. Критическое Governance Правило

**ЗАПРЕЩЕНО УВЕЛИЧИВАТЬ ЛИМИТЫ ТЕХ. ДОЛГА.**

- Технический долг может только **уменьшаться** или **оставаться неизменным**
- Увеличение бюджетов тех. долга (файловые лимиты, сложность функций, размер классов и т.д.) **СТРОГО ЗАПРЕЩЕНО**
- При любых изменениях проверяйте `configs/quality/debt_scorecard.yaml` и не допускайте деградации лимитов
- Для hotspot families используйте family-level параметры и не допускайте тихой деградации
- Это правило применяется ко всем агентам и всем типам задач без исключения

______________________________________________________________________

## 3. Import Matrix (CRITICAL)

This is the single most important rule to verify.

| From \\ To         | domain | application | infrastructure | composition | interfaces |
| ------------------ | :----: | :---------: | :------------: | :---------: | :--------: |
| **domain**         |   OK   |     NO      |       NO       |     NO      |     NO     |
| **application**    |   OK   |     OK      |       NO       |     NO      |     NO     |
| **infrastructure** |   OK   |     NO      |       OK       |     NO      |     NO     |
| **composition**    |   OK   |     OK      |       OK       |     OK      |     NO     |
| **interfaces**     |   OK   |     OK      |       NO       |     OK      |     OK     |

Direct `interfaces -> infrastructure` imports are forbidden by ADR-005 and
`.importlinter`; interfaces must route concrete runtime wiring through
composition-owned entrypoints.

### Detection Commands

```bash
# domain -> infrastructure (VIOLATION)
grep -rn "from bioetl.infrastructure" src/bioetl/domain/ --include="*.py"

# domain -> application (VIOLATION)
grep -rn "from bioetl.application" src/bioetl/domain/ --include="*.py"

# application -> infrastructure (VIOLATION, except TYPE_CHECKING)
grep -rn "from bioetl.infrastructure" src/bioetl/application/ --include="*.py" | grep -v TYPE_CHECKING

# infrastructure -> application (VIOLATION)
grep -rn "from bioetl.application" src/bioetl/infrastructure/ --include="*.py" | grep -v TYPE_CHECKING

# infrastructure -> composition (VIOLATION)
grep -rn "from bioetl.composition" src/bioetl/infrastructure/ --include="*.py"

# infrastructure -> interfaces (VIOLATION)
grep -rn "from bioetl.interfaces" src/bioetl/infrastructure/ --include="*.py"

# Architecture tests (1392 collected)
pytest tests/architecture/ -v --tb=short
```

______________________________________________________________________

## 4. Anti-Pattern Detection Quick Reference

| ID     | Pattern                            | Severity | Detection                                               |
| ------ | ---------------------------------- | -------- | ------------------------------------------------------- |
| AP-001 | Hard-coded constructor DI          | Critical | `self.x = ConcreteClass()` in app/domain                |
| AP-002 | Direct structlog in app/interfaces | High     | `import structlog` outside infrastructure/observability |
| AP-003 | Import boundary violation          | Critical | See §2 above                                            |
| AP-004 | Sentinel values (-1, "N/A")        | Medium   | `grep '= -1\|"N/A"'`                                    |
| AP-005 | Hardcoded secrets                  | Critical | `grep "password\|api_key\|secret"`                      |
| AP-006 | print() instead of logging         | Medium   | `grep "^\s*print("`                                     |
| AP-007 | Raw Parquet in Silver              | Critical | `grep "to_parquet"` in silver                           |
| AP-008 | Blocking I/O in async              | High     | `open()\|requests.` in async funcs                      |

### DI Violation Details

| ID     | Pattern                                        | Where Forbidden     |
| ------ | ---------------------------------------------- | ------------------- |
| DI-001 | `self.client = ConcreteClass()`                | application, domain |
| DI-002 | `def run(): client = Client()`                 | application, domain |
| DI-003 | `ServiceLocator.get()`                         | everywhere          |
| DI-004 | Module-level `logger = structlog.get_logger()` | application, domain |
| DI-005 | Factory calls in business logic                | application, domain |

______________________________________________________________________

## 5. Valid-by-design (DO NOT flag)

- `TYPE_CHECKING` imports (type hints only, no runtime effect)
- `param: T | None = None` for optional DI
- NoOp implementations (Null Object pattern: `NoOpTracing`, `NoOpMetrics`)
- Backward-compatibility re-export shims
- `MemoryLock` instead of Redis (ADR-010)
- Graceful degradation with conservative fallback estimates
- `Int->Float` coercion in Gold schemas (nullable integers in Pandas)
- Large files with proper delegation (delegation count > 5 = NOT god object)
- All `domain.*` imports in infrastructure (domain is pure contracts)
- `domain.types` / `domain.exceptions` everywhere (shared definitions)
- Click confirmations in CLI (interfaces layer)
- Config classes with default values (`RuntimeConfig(timeout=30.0)`)
- Test-specific module-level assignments
- Test doubles and scaffolding in `tests/**` (`MagicMock`, `AsyncMock`,
  `SimpleNamespace`, direct state/value-object construction)
- Stdlib/path normalization helpers in constructors
  (`Path(...)`, `str(...)`, `Path.resolve()`) when they adapt injected values
  rather than creating a service dependency
- Infrastructure adapters instantiating infrastructure-local helper objects
  (`ArrowDataConverter`, `RetentionPolicy`, `AnomalyDetector`,
  `TracerProvider`) inside `infrastructure/**`, unless the code is actually
  business logic or a hidden service locator

______________________________________________________________________

## 6. Naming Conventions Checklist

### Class Suffixes (MUST)

| Type          | Suffix         | Example                |
| ------------- | -------------- | ---------------------- |
| Factory       | `*Factory`     | `PipelineFactory`      |
| Client        | `*Client`      | `ChEMBLClient`         |
| Port/Protocol | `*Port`        | `DataSourcePort`       |
| Service       | `*Service`     | `ValidationService`    |
| Transformer   | `*Transformer` | `CompoundTransformer`  |
| Error         | `*Error`       | `ValidationError`      |
| Schema        | `*Schema`      | `CompoundGoldSchema`   |
| Config        | `*Config`      | `RuntimeConfig`        |
| Adapter       | `*Adapter`     | `BaseHttpAdapter`      |
| Extractor     | `*Extractor`   | `AuthorExtractor`      |
| Parser        | `*Parser`      | `MedlineDateParser`    |
| Aggregator    | `*Aggregator`  | `EnricherAggregator`   |
| Recorder      | `*Recorder`    | `BatchMetricsRecorder` |
| Result        | `*Result`      | `ValidationResult`     |
| Mixin         | `*Mixin`       | `HealthCheckMixin`     |

### Function Prefixes (SHOULD)

| Prefix                     | Use             |
| -------------------------- | --------------- |
| `get_*`                    | Local data      |
| `fetch_*`                  | Network/I/O     |
| `iter_*`                   | Generators      |
| `create_*` / `build_*`     | Object creation |
| `validate_*`               | Validation      |
| `is_*` / `has_*` / `can_*` | Boolean         |

______________________________________________________________________

## 7. Scoring Matrix

| Category            | Weight | Max Score |
| ------------------- | ------ | --------- |
| Architecture (ARCH) | 30%    | 10        |
| Anti-Patterns (AP)  | 25%    | 10        |
| DI Violations (DI)  | 20%    | 10        |
| Naming (NAME)       | 10%    | 10        |
| Types (TYPE)        | 10%    | 10        |
| Testing (TEST)      | 5%     | 10        |

| Severity | Deduction |
| -------- | --------- |
| CRITICAL | -2.0      |
| HIGH     | -1.0      |
| MEDIUM   | -0.5      |
| LOW      | -0.25     |

| Score   | Status |
| ------- | ------ |
| >= 8.0  | PASS   |
| 6.0-7.9 | WARN   |
| < 6.0   | FAIL   |

______________________________________________________________________

## 8. REST API Provider Reference

| Provider        | Base URL                            | Rate Limit   | Pagination |
| --------------- | ----------------------------------- | ------------ | ---------- |
| ChEMBL          | `ebi.ac.uk/chembl/api/data`         | None         | offset     |
| PubChem         | `pubchem.ncbi.nlm.nih.gov/rest/pug` | 5 req/sec    | offset     |
| UniProt         | `rest.uniprot.org`                  | 100 req/sec  | cursor     |
| PubMed          | `eutils.ncbi.nlm.nih.gov`           | 3 req/sec    | offset     |
| CrossRef        | `api.crossref.org`                  | 50 req/sec   | cursor     |
| OpenAlex        | `api.openalex.org`                  | 100 req/sec  | cursor     |
| SemanticScholar | `api.semanticscholar.org`           | 100 req/5min | offset     |

______________________________________________________________________

## 9. Dual Verification Protocol

**MANDATORY** before any architecture assertion:

1. Read **actual code** (don't assume)
1. Verify each finding **twice** (different commands/methods)
1. Provide **exact references** `file:line`
1. Cross-check against **Valid Exceptions** (§4)

______________________________________________________________________

## 10. Key Files for Audit

| What                    | Path                                             |
| ----------------------- | ------------------------------------------------ |
| RULES.md (Constitution) | `docs/00-project/RULES.md`                       |
| Self-review rules       | runtime self-review rules                        |
| Architecture tests      | `tests/architecture/`                            |
| Domain Ports            | `src/bioetl/domain/ports/`                       |
| Adapters                | `src/bioetl/infrastructure/adapters/{provider}/` |
| Pipelines               | `src/bioetl/application/pipelines/`              |
| Bootstrap               | `src/bioetl/composition/bootstrap/`              |
| ADR                     | `docs/02-architecture/decisions/`                |
| Configs                 | `configs/entities/{provider}/{entity}.yaml`      |

______________________________________________________________________

## 11. Integration with Other Agents

| Event                 | Action                                               |
| --------------------- | ---------------------------------------------------- |
| Baseline done         | -> Findings to `py-plan-bot` for plan                |
| MUST finding in final | -> Blocker: return to `py-debug-bot` / `py-plan-bot` |
| Doc drift detected    | -> `py-doc-bot`                                      |
| Config gap detected   | -> `py-plan-bot` as additional RF-\*                 |

______________________________________________________________________

## 12. Verification Commands

```bash
make lint                                    # ruff + mypy
mypy --strict src/bioetl/                   # Type check
pytest tests/architecture/ -v               # 1392 architecture tests
pytest --cov=src/bioetl --cov-fail-under=85 # Coverage
make security                               # Security scan
```

______________________________________________________________________

## 13. Unified Script Commands (for audit)

Скрипты доступны через `python -m scripts.<group> <command>`:

```bash
# QA checks (naming, complexity, terminology)
python -m scripts.engineering.qa check-naming --check
python -m scripts.engineering.qa check-c901
python -m scripts.engineering.qa check-naming-pkg --check
python -m scripts.engineering.qa check-terminology --strict --check

# Repo hygiene
python -m scripts.engineering.repo check-inventory --check
python -m scripts.engineering.repo check-catalog
python -m scripts.engineering.repo check-versions
python -m scripts.engineering.repo check-cleanliness --strict-untracked

# Schema/config invariants
python -m scripts.schema check-invariants --verbose
python -m scripts.schema check-config-paths
python -m scripts.schema validate-configs

# Documentation drift
python -m scripts.docs check-links --links --specs --configs
python -m scripts.docs check-drift --ports --classes
python -m scripts.docs check-docstrings --summary

# Architecture diagrams quality
python -m scripts.diagrams check quality-gates
python -m scripts.diagrams lint
```

CI gates (автоматические): `check-links`, `check-drift`, `check-docstrings` — в `docs.yml` / `architecture.yml`.
Pre-commit hooks: `check-naming`, `check-c901`, `lint` (diagrams), `fix-orphans`.

______________________________________________________________________

*This memory file is specific to py-audit-bot. For general project context see `agent-memory.md`.*
