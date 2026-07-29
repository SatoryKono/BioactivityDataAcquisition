# Typed test doubles (PD5-1)

Use these helpers so basedpyright accepts test wiring without weakening product Ports.

| Module | Use when |
| --- | --- |
| `tests.helpers.typed_ids` | APIs require `RunID` / `BatchID` / `EntityID` / `ContentHash` |
| `tests.helpers.protocol_stubs` | Need Logger/Metrics/DataSource-shaped doubles or `protocol_mock(Port, …)` |
| `tests.helpers.settings_doubles` | Replace `SimpleNamespace` for settings/config bags |
| `tests.helpers.entity_fixtures` | Entity dataclass construction kwargs |

## Examples

```python
from tests.helpers.typed_ids import as_run_id, new_run_id
from tests.helpers.protocol_stubs import RecordingLogger, protocol_mock
from tests.helpers.settings_doubles import as_settings

run_id = as_run_id("run-001")
logger = RecordingLogger()
settings = as_settings(enabled=True, limit=10)
```

Intentional invalid inputs (extra fields, frozen assign) should use local
`cast(Any, …)` or file-level pyright directives on the test module only —
never loosen product NewTypes.
