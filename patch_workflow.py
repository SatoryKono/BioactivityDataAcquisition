import re

with open(".github/workflows/type-checking.yml", "r") as f:
    content = f.read()

# Make sure we're piping stderr and stdout appropriately to create the log file BEFORE ratchet runs
content = content.replace(
    "2>&1 | tee -a reports/mypy_strict.log",
    "2>&1 | tee -a reports/mypy_strict.log"
) # Already seems to pipe in the CI script! Wait, the review said:
# "The ratchet script relies on reading mypy's output from a hardcoded path (`reports/mypy_strict.log`). However, the patch does not update the actual `mypy` execution step in `.github/workflows/type-checking.yml` to write or pipe its output to this file."
