> Scope:
> - USE WHEN handling credentials; never hardcode, load from env or secret manager (e.g., Vault)
> - Use when editing files matching: `src/**/*.py`, `configs/**/*.yaml`, `.env*`
# MANDATORY
- Do not hardcode secrets; load via environment or secret manager (Vault).
- Support rotation; do not commit secrets to VCS.

# BAD
```python
API_TOKEN = "abcd1234"
```

# GOOD
```python
import os
API_TOKEN = os.environ["API_TOKEN"]
```

# REFERENCE
See ../../docs/styleguide/09-secrets-config.md
