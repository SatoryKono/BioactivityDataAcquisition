---
id: prompt.audit.cycle.diagrams
version: 1.2.0
status: deprecated
class: operator-paste
owner: BioETL Team
successor: generated/diagrams/audit-readonly.md
summary: Deprecated library megacard; ADR-060 SSOT is overlay + generated render
---

# Redirect — `prompt.audit.cycle.diagrams`

> **Deprecated (ADR-060).** This file is a bookmark, not SSOT.
> Kernel + overlay replace the duplicated cyclic controller (D1/D2).

| Surface | Path |
| --- | --- |
| Overlay SSOT | [`overlays/diagrams.yaml`](../../../overlays/diagrams.yaml) |
| Default paste | [`generated/diagrams/audit-readonly.md`](../../../generated/diagrams/audit-readonly.md) |
| Explicit write | [`generated/diagrams/full-write.md`](../../../generated/diagrams/full-write.md) |
| Legacy id wrapper | [`compatibility/prompt.audit.cycle.diagrams.md`](../../../compatibility/prompt.audit.cycle.diagrams.md) |

```bash
python -m scripts.ai.prompts compile --domain diagrams --profile audit-readonly
python -m scripts.ai.prompts compile --domain diagrams --profile full-write
```

See [MIGRATION-GUIDE-KERNEL-V3.md](../../../MIGRATION-GUIDE-KERNEL-V3.md).
