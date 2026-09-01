---
id: prompt.audit.cycle.telemetry
version: 1.2.0
status: deprecated
class: operator-paste
owner: BioETL Team
successor: generated/telemetry/audit-readonly.md
summary: Deprecated library megacard; ADR-060 SSOT is overlay + generated render
---

# Redirect — `prompt.audit.cycle.telemetry`

> **Deprecated (ADR-060).** This file is a bookmark, not SSOT.
> Kernel + overlay replace the duplicated cyclic controller (D1/D2).

| Surface | Path |
| --- | --- |
| Overlay SSOT | [`overlays/telemetry.yaml`](../../../overlays/telemetry.yaml) |
| Default paste | [`generated/telemetry/audit-readonly.md`](../../../generated/telemetry/audit-readonly.md) |
| Explicit write | [`generated/telemetry/full-write.md`](../../../generated/telemetry/full-write.md) |
| Legacy id wrapper | [`compatibility/prompt.audit.cycle.telemetry.md`](../../../compatibility/prompt.audit.cycle.telemetry.md) |

```bash
python -m scripts.ai.prompts compile --domain telemetry --profile audit-readonly
python -m scripts.ai.prompts compile --domain telemetry --profile full-write
```

See [MIGRATION-GUIDE-KERNEL-V3.md](../../../MIGRATION-GUIDE-KERNEL-V3.md).
