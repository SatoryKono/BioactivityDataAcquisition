---
id: prompt.audit.cycle.architecture
version: 1.2.0
status: deprecated
class: operator-paste
owner: BioETL Team
successor: generated/architecture/audit-readonly.md
summary: Deprecated library megacard; ADR-060 SSOT is overlay + generated render
---

# Redirect — `prompt.audit.cycle.architecture`

> **Deprecated (ADR-060).** This file is a bookmark, not SSOT.
> Kernel + overlay replace the duplicated cyclic controller (D1/D2).

| Surface | Path |
| --- | --- |
| Overlay SSOT | [`overlays/architecture.yaml`](../../../overlays/architecture.yaml) |
| Default paste | [`generated/architecture/audit-readonly.md`](../../../generated/architecture/audit-readonly.md) |
| Explicit write | [`generated/architecture/full-write.md`](../../../generated/architecture/full-write.md) |
| Legacy id wrapper | [`compatibility/prompt.audit.cycle.architecture.md`](../../../compatibility/prompt.audit.cycle.architecture.md) |

```bash
python -m scripts.ai.prompts compile --domain architecture --profile audit-readonly
python -m scripts.ai.prompts compile --domain architecture --profile full-write
```

See [MIGRATION-GUIDE-KERNEL-V3.md](../../../MIGRATION-GUIDE-KERNEL-V3.md).
