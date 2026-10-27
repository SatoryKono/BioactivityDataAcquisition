import re

with open("scripts/engineering/ci/check_mypy_diagnostic_ratchet.py", "r") as f:
    content = f.read()

content = content.replace(
    "if not log_path.exists():\n        return diagnostics",
    "if not log_path.exists():\n        raise FileNotFoundError(f\"mypy log file not found at {log_path}. Ensure mypy runs before this script.\")"
)

with open("scripts/engineering/ci/check_mypy_diagnostic_ratchet.py", "w") as f:
    f.write(content)
