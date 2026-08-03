# Security Policy

## Threat Model

### Data Sources

BioETL integrates with the following public APIs:

- **ChEMBL** — Bioactivity data from scientific literature
- **PubChem** — Chemical compound information
- **UniProt** — Protein sequence and functional data
- **PubMed** — Scientific publication metadata

### Trust Boundaries

| Boundary           | Risk Level | Mitigation                            |
| ------------------ | ---------- | ------------------------------------- |
| API responses      | Medium     | Schema validation, input sanitization |
| User configuration | Low        | YAML schema validation                |
| Local filesystem   | Low        | Path traversal prevention             |

### Attack Vectors

| Vector                         | Description                            | Mitigation                                      |
| ------------------------------ | -------------------------------------- | ----------------------------------------------- |
| **API Injection**              | Malformed data in API responses        | Strict schema validation at adapter level       |
| **Data Poisoning**             | Corrupted or malicious records         | Multi-layer validation (Bronze → Silver → Gold) |
| **Secrets Exposure**           | Credentials in logs/code/VCR cassettes | Environment variables, sanitization hooks       |
| **Dependency Vulnerabilities** | CVEs in third-party packages           | Regular pip-audit scans, Dependabot             |

## Secret Management

### Environment Variables

All secrets MUST follow the naming convention:

```
BIOETL_{PROVIDER}_{KEY}
```

Examples:

- `BIOETL_CHEMBL_API_KEY`
- `BIOETL_PUBCHEM_API_KEY`
- `BIOETL_UNIPROT_API_KEY`

### Security Requirements

| Requirement               | Status                                  |
| ------------------------- | --------------------------------------- |
| Never commit `.env` files | ✅ Enforced via `.gitignore`            |
| VCR cassettes sanitized   | ✅ `before_record` hooks remove secrets |
| No hardcoded credentials  | ✅ Checked by linting rules             |
| Secrets not in logs       | ✅ Structlog filtering configured       |

### Loading Secrets

```python
import os

# CORRECT: Load from environment
api_key = os.environ.get("BIOETL_CHEMBL_API_KEY")

# INCORRECT: Hardcoded value
api_key = "sk-1234567890"  # NEVER do this
```

## Data Validation

### Multi-Layer Validation Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Bronze    │ ──► │   Silver    │ ──► │    Gold     │
│  (Raw API)  │     │  (Cleaned)  │     │ (Validated) │
└─────────────┘     └─────────────┘     └─────────────┘
      │                   │                   │
      ▼                   ▼                   ▼
 Schema checks      PyArrow schema      Pandera rules
 at adapters        enforcement         + business logic
```

### Validation Layers

| Layer        | Tool           | Validation Type                        |
| ------------ | -------------- | -------------------------------------- |
| **Adapters** | Custom schemas | Input format, required fields          |
| **Silver**   | PyArrow/Delta  | Schema enforcement, type coercion      |
| **Gold**     | Pandera        | Business rules, cross-field validation |

### Invalid Record Handling

- Records failing validation are sent to **Quarantine**
- Quarantine records include: original data, error details, timestamp
- Thresholds: >5% errors = warning, >20% errors = batch failure

## Dependencies

### Security Scanning

```bash
# Run dependency audit
pip-audit

# Check for known vulnerabilities
make security-check
```

### Automated Monitoring

- **Dependabot alerts**: Enabled via `.github/dependabot.yml` (pip + GitHub Actions)
- **detect-secrets**: Runs in CI (`.github/workflows/security.yml`) to prevent credential leaks
- **pip-audit**: Runs in CI (`.github/workflows/security.yml`) for dependency vulnerability scanning
- **Trivy**: Container image scanning in `.github/workflows/docker.yml` (SHA-pinned)
- **Update policy**: Security patches applied within 72 hours

### Dependency Versioning Policy

BioETL uses the canonical mixed dependency strategy:

- compatibility ranges live in `pyproject.toml`
- reproducibility is enforced through committed `uv.lock`
- exact `==` pins are reserved for justified exceptions, not the default policy

## Reporting Vulnerabilities

### Private Reporting Channel

- Use GitHub Security Advisories private reporting for this repository:
  `https://github.com/SatoryKono/BioactivityDataAcquisition/security/advisories/new`
- Initial acknowledgment target: 72 hours

### Disclosure Process

1. **Report** — Submit a private vulnerability report through GitHub Security Advisories
1. **Acknowledgment** — We respond within 72 hours
1. **Investigation** — We assess severity and impact
1. **Fix** — Patch developed and tested
1. **Disclosure** — Coordinated public disclosure after fix

### What to Include

- Description of the vulnerability
- Steps to reproduce
- Potential impact assessment
- Suggested fix (if any)

### Scope

| In Scope               | Out of Scope                   |
| ---------------------- | ------------------------------ |
| BioETL codebase        | Third-party API security       |
| Configuration handling | Infrastructure not owned by us |
| Data validation logic  | Social engineering attacks     |
| Secret management      | Physical security              |

## Security Best Practices for Contributors

### Code Review Checklist

- [ ] No hardcoded secrets or credentials
- [ ] Input validation for external data
- [ ] Proper error handling (no stack traces in production)
- [ ] VCR cassettes sanitized before commit
- [ ] Dependencies from trusted sources only

### Forbidden Patterns

```python
# ❌ Hardcoded secrets
API_KEY = "sk-secret-key-here"

# ❌ Unsanitized input in queries
query = f"SELECT * FROM {user_input}"

# ❌ Secrets in logs
logger.info(f"Using API key: {api_key}")

# ❌ Disabled SSL verification
httpx.get(url, verify=False)
```

### Recommended Patterns

```python
# ✅ Environment variables
api_key = os.environ["BIOETL_CHEMBL_API_KEY"]

# ✅ Parameterized queries
query = "SELECT * FROM compounds WHERE id = ?"

# ✅ Masked logging
logger.info("API key configured", has_key=bool(api_key))

# ✅ SSL verification enabled (default)
httpx.get(url)  # verify=True by default
```

______________________________________________________________________

*Last updated: 2026-06-25*
