# Contributing to BioETL

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/SatoryKono/BioactivityDataAcquisition.git
cd BioactivityDataAcquisition
make install

# 2. Run checks before any changes
make lint && make test

# 3. After changes
make lint && make test && git commit
```

## Essential Reading

Before contributing, read these documents:

| Document | Purpose |
|----------|---------|
| [docs/RULES.md](docs/RULES.md) | Project constitution (MUST read) |
| [AGENT.md](AGENT.md) | Development workflow and patterns |
| [docs/00-map.md](docs/00-map.md) | Documentation navigator |

## Workflow

1. **Create branch** from `main`
2. **Read** relevant sections of RULES.md
3. **Implement** following architecture constraints
4. **Test** (`make test` before AND after changes)
5. **Lint** (`make lint`)
6. **Commit** using Conventional Commits format

## Commit Format

```
<type>(<scope>): <description>
```

**Types:** `feat`, `fix`, `refactor`, `docs`, `test`, `chore`

**Examples:**
- `feat(chembl): add activity pipeline`
- `fix(pubchem): handle rate limit 429`
- `docs: update architecture diagram`

## Architecture Constraints

### Layer Dependencies (MUST follow)

| From ↓ / To → | domain | application | composition | infrastructure | interfaces |
|---------------|--------|-------------|-------------|----------------|------------|
| **domain** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **application** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **composition** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **infrastructure** | ✅ | ❌ | ❌ | ✅ | ❌ |
| **interfaces** | ✅ | ✅ | ✅ | ✅ | ✅ |

### Key Rules

- **Dependency Injection**: Dependencies via constructor, not created inside classes
- **Composition Root**: `src/bioetl/composition/bootstrap.py` is the only place for wiring
- **Async I/O**: Use `httpx` for HTTP, `run_in_executor` for blocking operations
- **Logging**: Use `structlog` with `run_id`, never `print()`
- **Secrets**: Environment variables only (`BIOETL_{PROVIDER}_{KEY}`)

## Testing Requirements

| Type | Directory | Requirements |
|------|-----------|--------------|
| Unit | `tests/unit/` | No mocking domain entities, mock ports only |
| Integration | `tests/integration/` | VCR.py for HTTP, sanitize secrets from cassettes |
| Architecture | `tests/test_architecture.py` | Validates layer imports |

**Coverage target:** >95% line coverage

## Pull Request Checklist

- [ ] `make lint` passes
- [ ] `make test` passes (before AND after changes)
- [ ] No hardcoded secrets or paths
- [ ] Documentation updated if behavior changed
- [ ] Follows Conventional Commits format

## Getting Help

- **Questions**: Open an issue
- **Bugs**: Include reproduction steps
- **Features**: Discuss in issue first

## RFC 2119 Keywords

- **MUST**: Absolute requirement, violation is a release blocker
- **SHOULD**: Strong recommendation, deviation requires justification in PR
- **MAY**: Optional, developer discretion

## Troubleshooting

### Common Issues

**1. "Watermark not found" errors**
- Check S3/MinIO connectivity (`make test-integration` usually catches this).
- Ensure `Watermark` class usage is consistent (use `Watermark.from_*` factory methods).

**2. "Lock acquisition failed"**
- Check Redis is running: `docker ps`.
- Check logs for "Lock lost" messages.

**3. "Missing dependencies"**
- Run `uv sync --extra dev --extra tracing`.
- Check `pyproject.toml` for new groups.

### Observability & Metrics

- Metrics are available at `http://localhost:8000/metrics`.
- Dashboards are in `grafana/dashboards/`.
- Tracing is disabled by default. To enable: `export BIOETL_OBSERVABILITY__TRACING_ENABLED=true`.
