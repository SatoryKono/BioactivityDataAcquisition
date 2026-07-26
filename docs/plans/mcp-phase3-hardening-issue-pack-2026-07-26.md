# MCP Phase 3 hardening — GitHub issue pack

*Status: working planning artifact (non-normative)*  
*Created: 2026-07-26*  
*Umbrella: [#6589](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6589)*  
*Predecessor (closed): [#6563](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6563)*

## Dependency order

1. **#6590** — W0+W1 generator/ensure (ship first)
2. **#6594** — W2 Devin local shared projection
3. **#6593** — W3 plane reliability (deja / health)
4. **#6592** — W4 expand anti-thrash (optional tracks)
5. **#6591** — W5 docs / closeout

## Issue index

| # | Title | Priority | Labels (primary) |
| --- | --- | --- | --- |
| [#6589](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6589) | Phase 3 umbrella | P1 | mcp, ai-runtime, infrastructure, runtime |
| [#6590](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6590) | setup_mcp HTTP env ban + ensure PYTHONPATH | P0 | mcp, tooling, testing, codex |
| [#6594](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6594) | Devin local shared materializer | P1 | mcp, developer-experience |
| [#6593](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6593) | Plane reliability (deja DOWN) | P1 | mcp, infrastructure, observability |
| [#6592](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6592) | Expand anti-thrash | P2 | mcp, performance |
| [#6591](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6591) | OPERATOR + closeout | P2 | mcp, documentation |

## Guardrails (every issue)

- No `.env` edits without explicit approval
- No tech-debt budget increases
- No long-lived stdio MCP Compose (#6293)
- Tracked `.mcp.json` / tracked `.devin/config.json` stay portable full stdio
- Shared endpoints bind `127.0.0.1` only

## Suggested PR stack

| PR | Issues | Notes |
| --- | --- | --- |
| PR-1 | #6590 | Land working-tree fixes |
| PR-2 | #6594 | Devin apply helper |
| PR-3 | #6593 | deja + health |
| PR-4 | #6592 | Optional expansion |
| PR-5 | #6591 | Docs after runtime green |

## Related plans

- `docs/plans/mcp-shared-http-multi-client-plan-2026-07-24.md`
- `docs/plans/mcp-shared-plane-work-plan-2026-07-24.md`
- `docs/plans/mcp-shared-http-multi-client-issue-pack-2026-07-24.md` (#6563 pack)
