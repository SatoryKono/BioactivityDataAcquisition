# CLI Boundary Test Families

Thin CLI wrappers should use the shared boundary-test families before adding a
dedicated suite.

- `test_runtime_compat_aliases.py`
  Use for top-level compat modules that alias to a canonical domain module via
  `alias_module(...)`.
- `test_boundary_families.py`
  Use for command-layer lazy delegation into composition/interface facades and
  for `bioetl.interfaces.cli.main` lazy registration checks.
- `../test_wrapper_families.py`
  Use for package-level convenience exports such as `bioetl.interfaces.cli` and
  `bioetl.interfaces.cli.registry_helpers`.

Create a standalone boundary file only when the wrapper has behavior that does
not fit one of those families.
