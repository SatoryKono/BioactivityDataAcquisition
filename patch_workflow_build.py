import re

with open(".github/workflows/type-checking.yml", "r") as f:
    content = f.read()

# Fix "omitting --no-build" issue from github-advanced-security
# "Python package manager scripts should not be executed during installation" -> uv run without --no-build might execute arbitrary stuff if it decides to build?
# Actually the prompt says ".github/workflows/type-checking.yml, строка 74: omitting --no-build — устранить безопасно (это же место — открытый тред github-advanced-security... тред должен закрыться исправлением"
# Line 74 in workflow is: uv run --frozen python -m scripts.engineering.ci.check_mypy_diagnostic_ratchet
content = content.replace(
    "uv run --frozen python -m scripts.engineering.ci.check_mypy_diagnostic_ratchet",
    "uv run --frozen --no-build python -m scripts.engineering.ci.check_mypy_diagnostic_ratchet"
)

with open(".github/workflows/type-checking.yml", "w") as f:
    f.write(content)
