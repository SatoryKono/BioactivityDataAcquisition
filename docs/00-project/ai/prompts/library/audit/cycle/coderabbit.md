---
id: prompt.audit.cycle.coderabbit
version: 1.2.0
status: deprecated
class: operator-paste
owner: BioETL Team
successor: generated/coderabbit/audit-readonly.md
summary: Deprecated library megacard; ADR-060 SSOT is overlay + generated render
---

# Redirect — `prompt.audit.cycle.coderabbit`

> **Deprecated (ADR-060).** This file is a bookmark, not SSOT.
> Kernel + overlay replace the duplicated cyclic controller (D1/D2).

| Surface | Path |
| --- | --- |
| Overlay SSOT | [`overlays/coderabbit.yaml`](../../../overlays/coderabbit.yaml) |
| Default paste | [`generated/coderabbit/audit-readonly.md`](../../../generated/coderabbit/audit-readonly.md) |
| Explicit write | [`generated/coderabbit/full-write.md`](../../../generated/coderabbit/full-write.md) |
| Legacy id wrapper | [`compatibility/prompt.audit.cycle.coderabbit.md`](../../../compatibility/prompt.audit.cycle.coderabbit.md) |

```bash
python -m scripts.ai.prompts compile --domain coderabbit --profile audit-readonly
python -m scripts.ai.prompts compile --domain coderabbit --profile full-write
```

See [MIGRATION-GUIDE-KERNEL-V3.md](../../../MIGRATION-GUIDE-KERNEL-V3.md).
