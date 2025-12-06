> Scope:
> - USE WHEN creating or modifying CLI; use Typer, explicit flags, input validation, clear exit codes and help
> - Use when editing files matching: `src/**/cli.py`, `src/scripts/**/*.py`
# INTERFACE
- Typer-based commands; prefer named options over ambiguous positionals.
- Validate inputs (paths exist, dirs writable) before execution.
- Standard exit codes: 0 success; 1 general error; 2 config error; 3 external dependency.

# UX
- Helpful error messages with remediation; progress indication for long tasks.

# REFERENCE
See [docs/styleguide/06-cli-contracts.md](../../docs/styleguide/06-cli-contracts.md) for detailed documentation.
