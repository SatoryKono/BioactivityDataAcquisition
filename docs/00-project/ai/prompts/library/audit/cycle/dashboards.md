---
id: prompt.audit.cycle.dashboards
version: 1.2.0
status: deprecated
class: operator-paste
owner: BioETL Team
successor: generated/dashboards/audit-readonly.md
summary: Deprecated library megacard; ADR-060 SSOT is overlay + generated render
---

# Redirect — `prompt.audit.cycle.dashboards`

> **Deprecated (ADR-060).** This file is a bookmark, not SSOT.
> Kernel + overlay replace the duplicated cyclic controller (D1/D2).

| Surface | Path |
| --- | --- |
| Overlay SSOT | [`overlays/dashboards.yaml`](../../../overlays/dashboards.yaml) |
| Default paste | [`generated/dashboards/audit-readonly.md`](../../../generated/dashboards/audit-readonly.md) |
| Explicit write | [`generated/dashboards/full-write.md`](../../../generated/dashboards/full-write.md) |
| Legacy id wrapper | [`compatibility/prompt.audit.cycle.dashboards.md`](../../../compatibility/prompt.audit.cycle.dashboards.md) |

```bash
python -m scripts.ai.prompts compile --domain dashboards --profile audit-readonly
python -m scripts.ai.prompts compile --domain dashboards --profile full-write
```

See [MIGRATION-GUIDE-KERNEL-V3.md](../../../MIGRATION-GUIDE-KERNEL-V3.md).
