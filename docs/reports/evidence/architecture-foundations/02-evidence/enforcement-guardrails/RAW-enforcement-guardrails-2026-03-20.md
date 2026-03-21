# Raw Evidence: enforcement-guardrails (2026-03-21)

## Commands Run

### 1. Layer dependency suite

```bash
./.venv/Scripts/python.exe -m pytest -q tests/architecture/test_layer_dependencies.py
```

Observed result:

```text
.................                                                        [100%]
```

Interpretation:

- The current layer dependency suite passed on the active baseline.
- The suite currently covers domain purity, application dependency direction, and port placement checks.

### 2. Bootstrap and composition boundary suites

```bash
./.venv/Scripts/python.exe -m pytest -q \
  tests/architecture/test_bootstrap_layer_boundaries.py \
  tests/architecture/test_composition_factory_import_boundaries.py \
  tests/architecture/test_di_runtime_inline_construction.py
```

Observed result:

```text
............                                                             [100%]
```

Interpretation:

- The current bootstrap/composition boundary suites passed on the active baseline.
- The passing set covers runtime-vs-CLI bootstrap separation, composition factory back-edge prevention, and application-layer inline dependency construction guards.

### 3. Interfaces and DI hardening suites

```bash
./.venv/Scripts/python.exe -m pytest -q \
  tests/architecture/test_interfaces_no_infrastructure.py \
  tests/architecture/test_no_structlog_in_application_interfaces.py \
  tests/architecture/test_no_inline_construction_in_adapters.py \
  tests/architecture/test_factory_validator_enforcement.py
```

Observed result:

```text
........................                                                 [100%]
```

Interpretation:

- The current interface dependency and DI hardening suites passed on the active baseline.
- The passing set covers interface-to-infrastructure coupling, logging abstraction boundaries, provider-adapter helper injection, and composition-factory validator policy.

Revalidation note:

- This raw snapshot was refreshed against the current repository state after the 2026-03-20 remediation wave.
