# Architecture Audit Report

Date: 2026-02-15
Scope: `src/bioetl/**` import graph (`grimp.build_graph("bioetl")`) and `.importlinter` contracts

## Executive Summary

- Total findings: 4
- Critical (MUST): 0
- Moderate (SHOULD): 4
- Informational (MAY): 0
- Layer contracts: 5/5 kept (`domain-independence`, `application-independence`, `infrastructure-independence`, `composition-no-interfaces`, `no-direct-instantiation-in-application`)

## Moderate Findings

## [MODERATE] Domain package import cycle (`ports` ↔ `context`)

**Location**:

- `src/bioetl/domain/ports/__init__.py:83-87`
- `src/bioetl/domain/ports/runner.py:10-11`
- `src/bioetl/domain/context.py:17`

**Rule Violated**: Circular imports in architecture components (anti-pattern checklist: circular imports).

**Evidence**:

```python
# src/bioetl/domain/ports/__init__.py
from bioetl.domain.ports.runner import (
    MetricsExtractorPort,
    RunnablePort,
    RunnerFactoryPort,
)

# src/bioetl/domain/ports/runner.py
if TYPE_CHECKING:
    from bioetl.domain.context import PipelineRunContext

# src/bioetl/domain/context.py
from bioetl.domain.ports import LoggerPort
```

**Impact**: Coupling between the domain context module and the aggregate `ports` package increases refactoring cost and makes import direction less explicit.

**Recommendation**:

```python
# Prefer importing from a leaf module instead of package aggregator:
from bioetl.domain.ports.observability import LoggerPort

# Keep context types in a dependency-neutral module if both sides need them:
# bioetl.domain.contracts.shared (example)
```

**Verification**:

- `PYTHONPATH=src python - <<'PY' ... build_graph('bioetl') ... Tarjan SCC ... PY`
- `nl -ba src/bioetl/domain/ports/__init__.py | sed -n '76,90p'`
- `nl -ba src/bioetl/domain/ports/runner.py | sed -n '8,14p'`
- `nl -ba src/bioetl/domain/context.py | sed -n '13,20p'`

______________________________________________________________________

## [MODERATE] Infrastructure config/schema cycle (`config` ↔ `schemas`)

**Location**:

- `src/bioetl/infrastructure/config/_base.py:38-43`
- `src/bioetl/infrastructure/config_loader.py:37-38`
- `src/bioetl/infrastructure/config/pipeline_config_loader.py:25-26`
- `src/bioetl/infrastructure/config/__init__.py:22-36`

**Rule Violated**: Circular imports in configuration subsystem.

**Evidence**:

```python
# src/bioetl/infrastructure/config/_base.py
from bioetl.infrastructure.config_loader import (
    load_pipeline_config,
    load_source_config,
)
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

# src/bioetl/infrastructure/config/pipeline_config_loader.py
from bioetl.infrastructure.config_loader import load_pipeline_config as load_yaml_config
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

# src/bioetl/infrastructure/config/__init__.py
from bioetl.infrastructure.config._base import (
    PipelineConfig,
    load_pipeline_config,
    load_source_config,
)
```

**Impact**: Raises probability of partial module initialization and makes config loading paths harder to reason about.

**Recommendation**:

```python
# Enforce one-way imports:
# loaders -> schemas -> domain
# and prevent schemas/helpers from importing loaders.
```

**Verification**:

- `PYTHONPATH=src python - <<'PY' ... build_graph('bioetl') ... example cycle extraction ... PY`
- `nl -ba src/bioetl/infrastructure/config/_base.py | sed -n '34,44p'`
- `nl -ba src/bioetl/infrastructure/config_loader.py | sed -n '35,40p'`
- `nl -ba src/bioetl/infrastructure/config/pipeline_config_loader.py | sed -n '23,27p'`
- `nl -ba src/bioetl/infrastructure/config/__init__.py | sed -n '22,36p'`

______________________________________________________________________

## [MODERATE] Composition bootstrap/runtime/factory cycle

**Location**:

- `src/bioetl/composition/factories/runner_factory.py:15-17`
- `src/bioetl/composition/bootstrap/__init__.py:63`
- `src/bioetl/composition/bootstrap/runtime/__init__.py:58-60`
- `src/bioetl/composition/bootstrap/runtime/runner.py:14-17`

**Rule Violated**: Circular imports inside composition root internals.

**Evidence**:

```python
# src/bioetl/composition/factories/runner_factory.py
from bioetl.composition.providers.registration import register_all_providers

# src/bioetl/composition/bootstrap/__init__.py
from bioetl.composition.bootstrap.runtime import (...)

# src/bioetl/composition/bootstrap/runtime/__init__.py
from bioetl.composition.bootstrap.runtime.runner import (
    bootstrap_pipeline_runner_service,
)

# src/bioetl/composition/bootstrap/runtime/runner.py
from bioetl.composition.factories.runner_factory import (
    create_metrics_extractor,
    create_runner_factory,
)
```

**Impact**: Increases bootstrap fragility and complicates maintenance of composition wiring.

**Recommendation**:

```python
# Keep acyclic orchestration chain:
# entrypoints -> bootstrap -> runtime -> factories
# (no reverse imports from runtime/factories back into bootstrap aggregators).
```

**Verification**:

- `PYTHONPATH=src python - <<'PY' ... build_graph('bioetl') ... example cycle extraction ... PY`
- `nl -ba src/bioetl/composition/factories/runner_factory.py | sed -n '13,18p'`
- `nl -ba src/bioetl/composition/bootstrap/__init__.py | sed -n '60,66p'`
- `nl -ba src/bioetl/composition/bootstrap/runtime/__init__.py | sed -n '58,60p'`
- `nl -ba src/bioetl/composition/bootstrap/runtime/runner.py | sed -n '12,18p'`

______________________________________________________________________

## [MODERATE] Composition providers/factories cycle

**Location**:

- `src/bioetl/composition/factories/http_client_factory.py:21`
- `src/bioetl/composition/providers/__init__.py:32`
- `src/bioetl/composition/providers/registration.py:16-23`
- `src/bioetl/composition/providers/_config_helpers.py:29-34`

**Rule Violated**: Circular imports in provider registration/factory assembly.

**Evidence**:

```python
# src/bioetl/composition/factories/http_client_factory.py
from bioetl.composition.providers import ProviderRegistry, ensure_providers_loaded

# src/bioetl/composition/providers/__init__.py
from bioetl.composition.providers.registration import register_all_providers

# src/bioetl/composition/providers/registration.py
from bioetl.composition.providers._config_helpers import (
    _get_adapter_config,
    _get_batch_size_from_config,
    _get_circuit_breaker_from_config,
    _get_factories,
    _get_rate_limit_from_config,
    _wrap_with_filter,
)

# src/bioetl/composition/providers/_config_helpers.py
from bioetl.composition.factories.data_source_factory import DataSourceFactory
from bioetl.composition.factories.http_client_factory import HttpClientFactory
```

**Impact**: Blurs ownership between registry, registration, and factory construction logic.

**Recommendation**:

```python
# Move shared provider contracts/constants to an independent leaf module.
# Keep factory modules consuming provider registry, but prevent helper -> factory back edges.
```

**Verification**:

- `PYTHONPATH=src python - <<'PY' ... build_graph('bioetl') ... example cycle extraction ... PY`
- `nl -ba src/bioetl/composition/factories/http_client_factory.py | sed -n '21,22p'`
- `nl -ba src/bioetl/composition/providers/__init__.py | sed -n '30,33p'`
- `nl -ba src/bioetl/composition/providers/registration.py | sed -n '16,23p'`
- `nl -ba src/bioetl/composition/providers/_config_helpers.py | sed -n '29,34p'`

## Positive Observations

- `.importlinter` contracts are currently satisfied (no layer-boundary violations detected by configured rules).
- Cycle findings are intra-layer/module-cluster issues; they do not contradict current 5 configured import-linter contracts.

## Verification Log

1. `python -m pip install import-linter grimp`
1. `PYTHONPATH=src lint-imports --config .importlinter`
1. `PYTHONPATH=src python - <<'PY' ... build_graph('bioetl') ... Tarjan SCC analysis ... PY`
1. `PYTHONPATH=src python - <<'PY' ... build_graph('bioetl') ... example cycle extraction ... PY`
1. `nl -ba <file> | sed -n '<range>p'` for every cited import edge above.
