---
id: prompt.fragment.shell-portability
version: 1.0.0
status: active
class: fragment
owner: BioETL Team
summary: Portable shell notes for BioETL Windows-first operators
---

## Shell portability

- Primary operator OS for BioETL is **Windows**. Prefer
  `.\.venv-win\Scripts\python.exe` for Python; never Linux `.venv` from Win.
- Example commands may use `bash` + `rg` (Git Bash / CI). Mark GNU-only flags
  (e.g. `xargs -r`) and provide a portable alternative when the check is
  mandatory.
- Do not assume `npm` / `go` / `cargo` until manifests prove that stack.
- Destructive git (`clean` without `-n`, `reset --hard`) is forbidden in audit
  mode unless the operator explicitly approves.
