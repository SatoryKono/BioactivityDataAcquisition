# Domain Ports Catalog

## Status

Obsolete duplicate catalog retained only as a historical redirect surface.

This page is no longer the canonical source of truth for the BioETL domain-port
inventory. Its former enumerations drifted from the live export facade and the
published reference catalog.

## Canonical Sources

- Published semantic catalog: [Domain Ports](../04-reference/domain/ports.md)
- Live import/export facade: `src/bioetl/domain/ports/__init__.py`
- API-oriented module reference: [API Reference: domain ports](../04-reference/api/domain/ports.md)

## Retirement Notes

- Use `docs/04-reference/domain/ports.md` for the supported port-family catalog.
- Use `bioetl.domain.ports` and `src/bioetl/domain/ports/__init__.py` for the
  live sanctioned import surface.
- Do not add new port descriptions or maintenance updates to this page.

## Reason For Retention

The file remains on disk only to preserve historical inbound links until all
external references have migrated to the canonical published domain-port docs.
