🎯 **What:** Modified `scripts/test_selection_strategy.py` to use `shell=False` and split the command string with `shlex.split()` in `_run_pre_checks()`.
⚠️ **Risk:** Using `shell=True` allows shell injection vulnerabilities if the command strings come from untrusted sources, potentially leading to arbitrary code execution.
🛡️ **Solution:** By turning off `shell=True` and parsing the command into an argument list with `shlex.split()`, the system executes the command directly without invoking a shell, avoiding the risk of shell injection.
