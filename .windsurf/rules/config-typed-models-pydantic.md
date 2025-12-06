> Scope:
> - USE WHEN defining configuration; use typed models (e.g., Pydantic), validate on load
> - Use when editing files matching: `src/**/config*.py`, `configs/**/*.yaml`
# SHOULD
- Define configuration as typed models; validate on load and provide defaults where safe.

# EXAMPLE
```python
from pydantic import BaseModel, AnyUrl

class PipelineConfig(BaseModel):
    timeout: int = 30
    output_dir: str
    api_url: AnyUrl
```

# REFERENCE
See ../../docs/styleguide/09-secrets-config.md
