---
id: prompt.audit.cycle.tech-debt
version: 1.2.0
status: deprecated
class: operator-paste
owner: BioETL Team
successor: generated/tech-debt/audit-readonly.md
summary: Deprecated library megacard; ADR-060 SSOT is overlay + generated render
---

# Redirect — `prompt.audit.cycle.tech-debt`

> **Deprecated (ADR-060).** This file is a bookmark, not SSOT.
> Kernel + overlay replace the duplicated cyclic controller (D1/D2).

| Surface | Path |
| --- | --- |
| Overlay SSOT | [`overlays/tech-debt.yaml`](../../../overlays/tech-debt.yaml) |
| Default paste | [`generated/tech-debt/audit-readonly.md`](../../../generated/tech-debt/audit-readonly.md) |
| Explicit write | [`generated/tech-debt/full-write.md`](../../../generated/tech-debt/full-write.md) |
| Legacy id wrapper | [`compatibility/prompt.audit.cycle.tech-debt.md`](../../../compatibility/prompt.audit.cycle.tech-debt.md) |

```bash
python -m scripts.ai.prompts compile --domain tech-debt --profile audit-readonly
python -m scripts.ai.prompts compile --domain tech-debt --profile full-write
```

See [MIGRATION-GUIDE-KERNEL-V3.md](../../../MIGRATION-GUIDE-KERNEL-V3.md).
