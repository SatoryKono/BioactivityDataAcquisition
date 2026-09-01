---
id: prompt.audit.cycle.agents-memory
version: 1.2.0
status: deprecated
class: operator-paste
owner: BioETL Team
successor: generated/agents-memory/audit-readonly.md
summary: Deprecated library megacard; ADR-060 SSOT is overlay + generated render
---

# Redirect — `prompt.audit.cycle.agents-memory`

> **Deprecated (ADR-060).** This file is a bookmark, not SSOT.
> Kernel + overlay replace the duplicated cyclic controller (D1/D2).

| Surface | Path |
| --- | --- |
| Overlay SSOT | [`overlays/agents-memory.yaml`](../../../overlays/agents-memory.yaml) |
| Default paste | [`generated/agents-memory/audit-readonly.md`](../../../generated/agents-memory/audit-readonly.md) |
| Explicit write | [`generated/agents-memory/full-write.md`](../../../generated/agents-memory/full-write.md) |
| Legacy id wrapper | [`compatibility/prompt.audit.cycle.agents-memory.md`](../../../compatibility/prompt.audit.cycle.agents-memory.md) |

```bash
python -m scripts.ai.prompts compile --domain agents-memory --profile audit-readonly
python -m scripts.ai.prompts compile --domain agents-memory --profile full-write
```

See [MIGRATION-GUIDE-KERNEL-V3.md](../../../MIGRATION-GUIDE-KERNEL-V3.md).
