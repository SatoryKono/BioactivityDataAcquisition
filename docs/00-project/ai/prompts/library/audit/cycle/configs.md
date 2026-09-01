---
id: prompt.audit.cycle.configs
version: 1.2.0
status: deprecated
class: operator-paste
owner: BioETL Team
successor: generated/configs/audit-readonly.md
summary: Deprecated library megacard; ADR-060 SSOT is overlay + generated render
---

# Redirect — `prompt.audit.cycle.configs`

> **Deprecated (ADR-060).** This file is a bookmark, not SSOT.
> Kernel + overlay replace the duplicated cyclic controller (D1/D2).

| Surface | Path |
| --- | --- |
| Overlay SSOT | [`overlays/configs.yaml`](../../../overlays/configs.yaml) |
| Default paste | [`generated/configs/audit-readonly.md`](../../../generated/configs/audit-readonly.md) |
| Explicit write | [`generated/configs/full-write.md`](../../../generated/configs/full-write.md) |
| Legacy id wrapper | [`compatibility/prompt.audit.cycle.configs.md`](../../../compatibility/prompt.audit.cycle.configs.md) |

```bash
python -m scripts.ai.prompts compile --domain configs --profile audit-readonly
python -m scripts.ai.prompts compile --domain configs --profile full-write
```

See [MIGRATION-GUIDE-KERNEL-V3.md](../../../MIGRATION-GUIDE-KERNEL-V3.md).
