# Root `concepts/` Archive

Этот archive surface хранит исторический `concepts/` subtree, который раньше
жил в корне репозитория как noncanonical documentation topology.

Причина архивации:

- `concepts/` создавал competing root-level docs surface вне canonical
  `docs/**` topology;
- файлы использовали Mintlify/MDX presentation format и не являлись active
  MkDocs source of truth;
- root governance теперь требует, чтобы такие carryover docs жили либо в
  canonical `docs/**`, либо в `docs/99-archive/**` как historical context.

Содержимое под этим каталогом сохраняется только как historical/reference
material и не считается normative documentation surface.
