---
id: prompt.audit.cycle.docs
version: 1.2.0
status: deprecated
class: operator-paste
owner: BioETL Team
successor: generated/docs/audit-readonly.md
summary: Deprecated library megacard; ADR-060 SSOT is overlay + generated render
---

# Redirect — `prompt.audit.cycle.docs`

> **Deprecated (ADR-060).** This file is a bookmark, not SSOT.
> Kernel + overlay replace the duplicated cyclic controller (D1/D2).

| Surface | Path |
| --- | --- |
| Overlay SSOT | [`overlays/docs.yaml`](../../../overlays/docs.yaml) |
| Default paste | [`generated/docs/audit-readonly.md`](../../../generated/docs/audit-readonly.md) |
| Explicit write | [`generated/docs/full-write.md`](../../../generated/docs/full-write.md) |
| Legacy id wrapper | [`compatibility/prompt.audit.cycle.docs.md`](../../../compatibility/prompt.audit.cycle.docs.md) |

```bash
python -m scripts.ai.prompts compile --domain docs --profile audit-readonly
python -m scripts.ai.prompts compile --domain docs --profile full-write
```

See [MIGRATION-GUIDE-KERNEL-V3.md](../../../MIGRATION-GUIDE-KERNEL-V3.md).
