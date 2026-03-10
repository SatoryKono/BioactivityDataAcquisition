# RF-013 Exemption Burn-down Backlog

Date: 2026-03-04
Scope: `configs/quality/architecture_metric_exemptions.yaml`, `tests/architecture/test_code_metrics.py`, `tests/architecture/test_di_compliance.py`

## 1) Entries with nearest `expires_on`

Filtered window: all registry entries with minimal `expires_on`.

- Nearest `expires_on`: `2026-04-30`
- Entries at nearest date: `485/485`
- Registry breakdown for nearest date:
  - `function_length`: 118
  - `file_size_limits`: 97
  - `function_complexity`: 97
  - `class_size`: 82
  - `god_object`: 49
  - `domain_complexity`: 41
  - `class_method_count`: 1

> Mapping rule: each exemption entry is mapped to architecture test by its registry key, therefore **all 485 nearest-date entries are covered** via the table in section 2.

## 2) Exemption registry -> architecture test -> target refactoring

| Exemption registry key | Entries (nearest date) | Architecture test                                                                       | Target refactoring theme                                             | Target PR slice                     |
| ---------------------- | ---------------------: | --------------------------------------------------------------------------------------- | -------------------------------------------------------------------- | ----------------------------------- |
| `file_size_limits`     |                     97 | `tests/architecture/test_code_metrics.py::TestFileSizeLimits`                           | Split oversized modules into focused services/helpers by layer       | RF-013-PR01 (file decomposition)    |
| `function_complexity`  |                     97 | `tests/architecture/test_code_metrics.py::TestFunctionComplexity`                       | Extract branch-heavy logic into strategy/check modules               | RF-013-PR02 (complexity reduction)  |
| `function_length`      |                    118 | `tests/architecture/test_code_metrics.py::TestFunctionLength`                           | Break long functions into cohesive private methods/use-case helpers  | RF-013-PR03 (function slicing)      |
| `class_size`           |                     82 | `tests/architecture/test_code_metrics.py::TestClassSize::test_classes_under_300_lines`  | Split large classes into orchestrator + delegated components         | RF-013-PR04 (class decomposition)   |
| `class_method_count`   |                      1 | `tests/architecture/test_code_metrics.py::TestClassSize::test_classes_under_20_methods` | Move feature groups into collaborator classes                        | RF-013-PR05 (method-count fix)      |
| `god_object`           |                     49 | `tests/architecture/test_code_metrics.py::TestGodObjectDetection`                       | Increase delegation to injected services, remove monolithic behavior | RF-013-PR06 (delegation refactor)   |
| `domain_complexity`    |                     41 | `tests/architecture/test_code_metrics.py::TestFunctionComplexity` (domain thresholds)   | Simplify domain branching (value objects/specification helpers)      | RF-013-PR07 (domain simplification) |

## 3) Short backlog: “exemption -> specific PR”

1. **DI instantiation cleanup** (non-registry debt, architecture gate):

   - Test: `tests/architecture/test_di_compliance.py::test_no_direct_instantiation_in_application`, `::test_no_self_instantiation_of_dependencies`, `::test_no_httpx_client_in_application`
   - PR: **RF-013-PR08**
   - Refactoring: move object creation to composition factories; keep application on ports only.

1. **Factory placement normalization** (non-registry debt, architecture gate):

   - Test: `tests/architecture/test_di_compliance.py::test_factories_only_in_composition`
   - PR: **RF-013-PR09**
   - Refactoring: relocate `*Factory` classes to `composition/factories`, keep adapters/services outside composition root free from construction logic.

1. **Metrics exemption burn-down** (registry debt):

   - Tests: all `test_code_metrics.py` suites listed in section 2.
   - PRs: **RF-013-PR01..PR07**
   - Refactoring: category-driven removal of exemptions with per-PR measurable delta.

## 4) RF-011 policy (SilverDQAnalyzer)

- **Separate PR required**: keep `SilverDQAnalyzer` complexity/class-size remediation in **RF-011-PRxx** dedicated branch/PR.
- **Non-blocking for RF-013**: RF-013 continues with other categories and closes its own measurable debt slices.
- Integration point: RF-013 can reference RF-011 PR status, but does not wait for its merge to deliver category reductions outside SilverDQAnalyzer scope.

## 5) RF-013 Definition of Done (updated)

RF-013 is considered done when **active exemptions are reduced by category**, not only when baseline-mode tests stay green.

Mandatory readiness criteria:

1. `scripts/check_quality_exemptions.py --mode warn` passes.
1. Net reduction of active exemptions vs baseline snapshot (`485`) in at least **3 categories** from section 2.
1. At least **one category reaches zero** active exemptions (or is transferred to RF-011 with explicit owner/date).
1. `tests/architecture/test_code_metrics.py` remains green under current baseline policy.
1. `tests/architecture/test_di_compliance.py` remains green; DI/factory-placement changes are tracked by explicit PR slices (PR08/PR09).

Tracking metric for RF-013 reviews:

`burn_down_score = sum(active_exemptions_by_category)`

Target trend per PR: strictly decreasing burn-down score (no flat PRs without justified transfer to RF-011).
