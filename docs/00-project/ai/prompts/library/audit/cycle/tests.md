---
id: prompt.audit.cycle.tests
version: 1.2.0
status: deprecated
class: operator-paste
owner: BioETL Team
successor: generated/tests/audit-readonly.md
summary: Deprecated library megacard; ADR-060 SSOT is overlay + generated render
---

# Redirect — `prompt.audit.cycle.tests`

> **Deprecated (ADR-060).** This file is a bookmark, not SSOT.
> Kernel + overlay replace the duplicated cyclic controller (D1/D2).

| Surface | Path |
| --- | --- |
| Overlay SSOT | [`overlays/tests.yaml`](../../../overlays/tests.yaml) |
| Default paste | [`generated/tests/audit-readonly.md`](../../../generated/tests/audit-readonly.md) |
| Explicit write | [`generated/tests/full-write.md`](../../../generated/tests/full-write.md) |
| Legacy id wrapper | [`compatibility/prompt.audit.cycle.tests.md`](../../../compatibility/prompt.audit.cycle.tests.md) |

```bash
python -m scripts.ai.prompts compile --domain tests --profile audit-readonly
python -m scripts.ai.prompts compile --domain tests --profile full-write
```

See [MIGRATION-GUIDE-KERNEL-V3.md](../../../MIGRATION-GUIDE-KERNEL-V3.md).
