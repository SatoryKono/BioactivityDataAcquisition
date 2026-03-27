# Code Review Report — S6: Tests
**Date**: 2026-03-24
**Scope**: tests
**Files reviewed**: 1153
**Total LOC**: 298301
**Status**: FAIL
**Score**: 0.0/10.0

---

## Summary
| Category | Issues | CRIT | HIGH | MED | LOW | Score |
|----------|--------|------|------|-----|-----|-------|
| Architecture | 0 | 0 | 0 | 0 | 0 | - |
| Anti-Patterns | 33 | 0 | 0 | 0 | 0 | - |
| DI Violations | 0 | 0 | 0 | 0 | 0 | - |
| Naming | 0 | 0 | 0 | 0 | 0 | - |
| Types | 5280 | 0 | 0 | 0 | 0 | - |
| Testing | 0 | 0 | 0 | 0 | 0 | - |
| **TOTAL** | **5313** | **14** | **5027** | **19** | **253** | **0.0** |


## Critical Issues
### AP-005: Hardcoded secret
- **Rule**: AP-005
- **Severity**: CRITICAL
- **File**: `tests/unit/infrastructure/test_adapters.py:303`
- **Description**: Hardcoded secret
- **Code**:
  ```python
  api_key="test_key",
  ```
### AP-005: Hardcoded secret
- **Rule**: AP-005
- **Severity**: CRITICAL
- **File**: `tests/unit/infrastructure/adapters/semanticscholar/test_adapter.py:51`
- **Description**: Hardcoded secret
- **Code**:
  ```python
  api_key="test-api-key",
  ```
### AP-005: Hardcoded secret
- **Rule**: AP-005
- **Severity**: CRITICAL
- **File**: `tests/unit/infrastructure/adapters/semanticscholar/test_fallback.py:171`
- **Description**: Hardcoded secret
- **Code**:
  ```python
  api_key="test-api-key",
  ```
### AP-005: Hardcoded secret
- **Rule**: AP-005
- **Severity**: CRITICAL
- **File**: `tests/unit/infrastructure/adapters/semanticscholar/test_request_metadata.py:47`
- **Description**: Hardcoded secret
- **Code**:
  ```python
  api_key="test-api-key",
  ```
### AP-005: Hardcoded secret
- **Rule**: AP-005
- **Severity**: CRITICAL
- **File**: `tests/unit/infrastructure/adapters/uniprot/test_uniprot_client_coverage.py:381`
- **Description**: Hardcoded secret
- **Code**:
  ```python
  api_key="secret",
  ```
### AP-005: Hardcoded secret
- **Rule**: AP-005
- **Severity**: CRITICAL
- **File**: `tests/unit/composition/providers/test_registration_data_sources.py:308`
- **Description**: Hardcoded secret
- **Code**:
  ```python
  pipeline_config.source.api_key = "${BIOETL_PUBMED_API_KEY}"
  ```
### AP-005: Hardcoded secret
- **Rule**: AP-005
- **Severity**: CRITICAL
- **File**: `tests/unit/composition/providers/test_registration_data_sources.py:340`
- **Description**: Hardcoded secret
- **Code**:
  ```python
  pipeline_config.source.api_key = "pipeline-key"
  ```
### AP-005: Hardcoded secret
- **Rule**: AP-005
- **Severity**: CRITICAL
- **File**: `tests/unit/composition/providers/test_registration_biblio_profiles.py:27`
- **Description**: Hardcoded secret
- **Code**:
  ```python
  _pipeline_config(email="pipeline@example.org", api_key="pipeline-key"),
  ```
### AP-005: Hardcoded secret
- **Rule**: AP-005
- **Severity**: CRITICAL
- **File**: `tests/unit/composition/factories/datasource/test_http_client_factory.py:116`
- **Description**: Hardcoded secret
- **Code**:
  ```python
  settings = SimpleNamespace(pubmed_api_key="non-empty")
  ```
### AP-005: Hardcoded secret
- **Rule**: AP-005
- **Severity**: CRITICAL
- **File**: `tests/unit/composition/factories/datasource/test_http_client_factory.py:165`
- **Description**: Hardcoded secret
- **Code**:
  ```python
  settings = SimpleNamespace(pubmed_api_key="key", empty_value="", zero_value=0)
  ```
### AP-005: Hardcoded secret
- **Rule**: AP-005
- **Severity**: CRITICAL
- **File**: `tests/unit/composition/factories/datasource/test_http_client_factory.py:265`
- **Description**: Hardcoded secret
- **Code**:
  ```python
  settings = SimpleNamespace(pubmed_api_key="non-empty")
  ```
### AP-005: Hardcoded secret
- **Rule**: AP-005
- **Severity**: CRITICAL
- **File**: `tests/unit/composition/factories/datasource/test_data_sources.py:46`
- **Description**: Hardcoded secret
- **Code**:
  ```python
  "uniprot", http_client=mock_http_client, logger=mock_logger, api_key="test_key"
  ```
### AP-005: Hardcoded secret
- **Rule**: AP-005
- **Severity**: CRITICAL
- **File**: `tests/unit/domain/config/test_base_provider.py:91`
- **Description**: Hardcoded secret
- **Code**:
  ```python
  api_key="test-key",
  ```
### AP-005: Hardcoded secret
- **Rule**: AP-005
- **Severity**: CRITICAL
- **File**: `tests/unit/domain/configs/test_base_configs.py:99`
- **Description**: Hardcoded secret
- **Code**:
  ```python
  api_key="secret-key",
  ```

## High Issues
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `tests/test_architecture.py:194`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def test_domain_purity_ast(src_dir: Path):
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `tests/test_architecture.py:238`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def test_domain_no_infrastructure_imports(src_dir: Path):
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `tests/test_architecture.py:262`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def test_silver_schemas_match_domain_entities(src_dir: Path):
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `tests/test_architecture.py:350`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def test_ports_are_protocols(src_dir: Path):
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `tests/test_architecture.py:370`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def test_io_ports_are_async():
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `tests/test_architecture.py:417`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def test_application_no_concrete_infrastructure(src_dir: Path):
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `tests/test_architecture.py:441`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def test_application_no_direct_adapter_imports(src_dir: Path):
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `tests/test_architecture.py:491`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def test_infrastructure_boundaries(src_dir: Path):
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `tests/test_architecture.py:522`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def test_no_unsafe_functions(src_dir: Path):
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `tests/test_architecture.py:565`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def test_env_var_centralization(src_dir: Path):
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `tests/test_architecture.py:596`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def test_dependencies_versions(pyproject_toml: Path):
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `tests/test_architecture.py:607`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def test_deprecated_files(project_root: Path):
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `tests/test_architecture.py:618`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def test_pipeline_configs_schema(project_root: Path):
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `tests/test_architecture.py:653`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def test_observability_library_isolation(src_dir: Path):
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `tests/test_architecture.py:682`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def test_adapters_implement_protocols(src_dir: Path):
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `tests/test_architecture.py:769`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def test_http_adapters_inherit_base(src_dir: Path):
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `tests/test_architecture.py:798`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def test_public_methods_have_docstrings(src_dir: Path):
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `tests/test_architecture.py:837`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def test_metrics_implementations_are_compliant(src_dir: Path):
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `tests/conftest.py:32`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def pytest_cmdline_main(config):
  ```
### TYPE-001: Missing return type annotation
- **Rule**: TYPE-001
- **Severity**: HIGH
- **File**: `tests/conftest.py:47`
- **Description**: Missing return type annotation
- **Code**:
  ```python
  def pytest_configure(config):
  ```

## Medium Issues
### AP-006: Print statement found
- **Rule**: AP-006
- **Severity**: MEDIUM
- **File**: `tests/test_architecture.py:523`
- **Description**: Print statement found
- **Code**:
  ```python
  """No print() or unsafe builtins."""
  ```
### AP-006: Print statement found
- **Rule**: AP-006
- **Severity**: MEDIUM
- **File**: `tests/architecture/test_any_budget.py:128`
- **Description**: Print statement found
- **Code**:
  ```python
  print(f"\n[Any Budget] Unjustified: {count} / Threshold: {MAX_UNJUSTIFIED}")
  ```
### AP-006: Print statement found
- **Rule**: AP-006
- **Severity**: MEDIUM
- **File**: `tests/architecture/test_antipatterns.py:108`
- **Description**: Print statement found
- **Code**:
  ```python
  assert not violations, "print() usage found:\n" + "\n".join(violations[:50])
  ```
### AP-006: Print statement found
- **Rule**: AP-006
- **Severity**: MEDIUM
- **File**: `tests/architecture/test_no_print_in_docstrings.py:1`
- **Description**: Print statement found
- **Code**:
  ```python
  """Architecture test: no print() in docstring examples in non-domain layers.
  ```
### AP-006: Print statement found
- **Rule**: AP-006
- **Severity**: MEDIUM
- **File**: `tests/architecture/test_no_print_in_docstrings.py:4`
- **Description**: Print statement found
- **Code**:
  ```python
  MUST use LoggerPort in docstring examples instead of print().
  ```
### AP-006: Print statement found
- **Rule**: AP-006
- **Severity**: MEDIUM
- **File**: `tests/architecture/test_no_print_in_docstrings.py:7`
- **Description**: Print statement found
- **Code**:
  ```python
  return values with print() in Python doctests.
  ```
### AP-006: Print statement found
- **Rule**: AP-006
- **Severity**: MEDIUM
- **File**: `tests/architecture/test_no_print_in_docstrings.py:9`
- **Description**: Print statement found
- **Code**:
  ```python
  See CLAUDE.md §11 Anti-Patterns: ❌ `print()` → `structlog` с `run_id`
  ```
### AP-006: Print statement found
- **Rule**: AP-006
- **Severity**: MEDIUM
- **File**: `tests/architecture/test_no_print_in_docstrings.py:28`
- **Description**: Print statement found
- **Code**:
  ```python
  # Pattern to detect print() calls in docstrings
  ```
### AP-006: Print statement found
- **Rule**: AP-006
- **Severity**: MEDIUM
- **File**: `tests/architecture/test_no_print_in_docstrings.py:29`
- **Description**: Print statement found
- **Code**:
  ```python
  # Matches: print(, print (, but not logger.print or _print
  ```
### AP-006: Print statement found
- **Rule**: AP-006
- **Severity**: MEDIUM
- **File**: `tests/architecture/test_no_print_in_docstrings.py:68`
- **Description**: Print statement found
- **Code**:
  ```python
  """Check for print() in docstring examples in a directory.
  ```
### AP-006: Print statement found
- **Rule**: AP-006
- **Severity**: MEDIUM
- **File**: `tests/architecture/test_no_print_in_docstrings.py:90`
- **Description**: Print statement found
- **Code**:
  ```python
  # Check if docstring contains Example: section with print()
  ```
### AP-006: Print statement found
- **Rule**: AP-006
- **Severity**: MEDIUM
- **File**: `tests/architecture/test_no_print_in_docstrings.py:96`
- **Description**: Print statement found
- **Code**:
  ```python
  f"{rel_path}:{lineno + i}: print() in docstring example"
  ```
### AP-006: Print statement found
- **Rule**: AP-006
- **Severity**: MEDIUM
- **File**: `tests/architecture/test_no_print_in_docstrings.py:114`
- **Description**: Print statement found
- **Code**:
  ```python
  structured logging patterns, not print() statements.
  ```
### AP-006: Print statement found
- **Rule**: AP-006
- **Severity**: MEDIUM
- **File**: `tests/architecture/test_no_print_in_docstrings.py:117`
- **Description**: Print statement found
- **Code**:
  ```python
  show return values with print() in Python doctests.
  ```
### AP-006: Print statement found
- **Rule**: AP-006
- **Severity**: MEDIUM
- **File**: `tests/architecture/test_no_print_in_docstrings.py:122`
- **Description**: Print statement found
- **Code**:
  ```python
  f"print() in docstring examples found in {layer_dir.name} layer:\n"
  ```
### AP-006: Print statement found
- **Rule**: AP-006
- **Severity**: MEDIUM
- **File**: `tests/architecture/test_no_print_in_docstrings.py:124`
- **Description**: Print statement found
- **Code**:
  ```python
  + "\n\nUse logger.info/debug/warning/error instead of print()."
  ```
### AP-006: Print statement found
- **Rule**: AP-006
- **Severity**: MEDIUM
- **File**: `tests/integration/pipelines/test_crossref_date_normalization.py:191`
- **Description**: Print statement found
- **Code**:
  ```python
  async def test_online_date_used_when_no_print(
  ```
### AP-006: Print statement found
- **Rule**: AP-006
- **Severity**: MEDIUM
- **File**: `tests/unit/domain/hash_policy/test_hash_policy_stability.py:39`
- **Description**: Print statement found
- **Code**:
  ```python
  def _policy_fingerprint(policy: dict[str, Any]) -> str:
  ```
### AP-006: Print statement found
- **Rule**: AP-006
- **Severity**: MEDIUM
- **File**: `tests/unit/domain/hash_policy/test_hash_policy_stability.py:104`
- **Description**: Print statement found
- **Code**:
  ```python
  "policy_fingerprint": _policy_fingerprint(policy),
  ```

## Low Issues
### TYPE-002: Any used without comment
- **Rule**: TYPE-002
- **Severity**: LOW
- **File**: `tests/conftest.py:170`
- **Description**: Any used without comment
- **Code**:
  ```python
  def isolated_registry() -> Any:
  ```
### TYPE-002: Any used without comment
- **Rule**: TYPE-002
- **Severity**: LOW
- **File**: `tests/conftest.py:178`
- **Description**: Any used without comment
- **Code**:
  ```python
  def populated_isolated_registry(isolated_registry: Any) -> Any:
  ```
### TYPE-002: Any used without comment
- **Rule**: TYPE-002
- **Severity**: LOW
- **File**: `tests/conftest.py:211`
- **Description**: Any used without comment
- **Code**:
  ```python
  def query_ignore_email(request_1: Any, request_2: Any) -> bool:
  ```
### TYPE-002: Any used without comment
- **Rule**: TYPE-002
- **Severity**: LOW
- **File**: `tests/conftest.py:222`
- **Description**: Any used without comment
- **Code**:
  ```python
  ) -> Any:
  ```
### TYPE-002: Any used without comment
- **Rule**: TYPE-002
- **Severity**: LOW
- **File**: `tests/fakes/storage_fake.py:130`
- **Description**: Any used without comment
- **Code**:
  ```python
  schema: Any,
  ```
### TYPE-002: Any used without comment
- **Rule**: TYPE-002
- **Severity**: LOW
- **File**: `tests/architecture/test_any_budget.py:1`
- **Description**: Any used without comment
- **Code**:
  ```python
  """Architecture test: Any usage justification (TYPE-002).
  ```
### TYPE-002: Any used without comment
- **Rule**: TYPE-002
- **Severity**: LOW
- **File**: `tests/architecture/test_config_ci_invariants.py:141`
- **Description**: Any used without comment
- **Code**:
  ```python
  def _deep_string_search(obj: Any, fragment: str) -> bool:
  ```
### TYPE-002: Any used without comment
- **Rule**: TYPE-002
- **Severity**: LOW
- **File**: `tests/architecture/test_config_golden_master.py:51`
- **Description**: Any used without comment
- **Code**:
  ```python
  def _convert_for_json(obj: Any) -> Any:
  ```
### TYPE-002: Any used without comment
- **Rule**: TYPE-002
- **Severity**: LOW
- **File**: `tests/architecture/test_port_contracts_hypothesis.py:37`
- **Description**: Any used without comment
- **Code**:
  ```python
  def run_async(coro) -> Any:
  ```
### TYPE-002: Any used without comment
- **Rule**: TYPE-002
- **Severity**: LOW
- **File**: `tests/architecture/test_port_contracts_hypothesis.py:649`
- **Description**: Any used without comment
- **Code**:
  ```python
  def test_dumps_loads_roundtrip(self, data: Any) -> None:
  ```
### TYPE-002: Any used without comment
- **Rule**: TYPE-002
- **Severity**: LOW
- **File**: `tests/architecture/test_regression_metrics.py:497`
- **Description**: Any used without comment
- **Code**:
  ```python
  def _load_dep_map_module() -> Any | None:
  ```
### TYPE-002: Any used without comment
- **Rule**: TYPE-002
- **Severity**: LOW
- **File**: `tests/e2e/conftest.py:369`
- **Description**: Any used without comment
- **Code**:
  ```python
  async def run_pipeline_or_skip_transient(context: PipelineRunContext) -> Any:
  ```
### TYPE-002: Any used without comment
- **Rule**: TYPE-002
- **Severity**: LOW
- **File**: `tests/helpers/transformer_dependencies.py:23`
- **Description**: Any used without comment
- **Code**:
  ```python
  **kwargs: Any,
  ```
### TYPE-002: Any used without comment
- **Rule**: TYPE-002
- **Severity**: LOW
- **File**: `tests/helpers/adapter_error_logging.py:29`
- **Description**: Any used without comment
- **Code**:
  ```python
  **context: Any,
  ```
### TYPE-002: Any used without comment
- **Rule**: TYPE-002
- **Severity**: LOW
- **File**: `tests/integration/adapters/test_uniprot.py:49`
- **Description**: Any used without comment
- **Code**:
  ```python
  def uniprot_http_client(self, token_bucket: Any, circuit_breaker: Any) -> Any:
  ```
### TYPE-002: Any used without comment
- **Rule**: TYPE-002
- **Severity**: LOW
- **File**: `tests/integration/adapters/test_uniprot.py:60`
- **Description**: Any used without comment
- **Code**:
  ```python
  def uniprot_adapter(self, uniprot_http_client: Any, mock_logger: MagicMock) -> Any:
  ```
### TYPE-002: Any used without comment
- **Rule**: TYPE-002
- **Severity**: LOW
- **File**: `tests/integration/adapters/test_uniprot.py:74`
- **Description**: Any used without comment
- **Code**:
  ```python
  def test_provider_name(self, uniprot_adapter: Any) -> None:
  ```
### TYPE-002: Any used without comment
- **Rule**: TYPE-002
- **Severity**: LOW
- **File**: `tests/integration/adapters/test_uniprot.py:80`
- **Description**: Any used without comment
- **Code**:
  ```python
  self, uniprot_http_client: Any, mock_logger: MagicMock
  ```
### TYPE-002: Any used without comment
- **Rule**: TYPE-002
- **Severity**: LOW
- **File**: `tests/integration/adapters/test_uniprot.py:111`
- **Description**: Any used without comment
- **Code**:
  ```python
  self, uniprot_http_client: Any, mock_logger: MagicMock
  ```
### TYPE-002: Any used without comment
- **Rule**: TYPE-002
- **Severity**: LOW
- **File**: `tests/integration/adapters/test_chembl.py:47`
- **Description**: Any used without comment
- **Code**:
  ```python
  def chembl_client(self, token_bucket: Any, circuit_breaker: Any) -> Any:
  ```

## Positive Observations
- The code is overall well-structured.

## Scoring Calculation
| Category | Weight | Raw Score | Deductions | Weighted |
|----------|--------|-----------|------------|----------|
| Final | 100% | 10.0 | -10.0 | 0.0 |
