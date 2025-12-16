# Vendoring Mermaid for local/offline MkDocs builds

This project prefers to vendor the Mermaid JS bundle so MkDocs builds can run offline and render diagrams consistently.

Steps to vendor Mermaid locally (Windows PowerShell):

1. From repository root run (PowerShell):

   powershell.exe -NoProfile -ExecutionPolicy Bypass -File assets\javascripts\download_mermaid.ps1 -Version "10.4.0"

2. Verify files were created:

  - assets/javascripts/mermaid.min.js
  - assets/javascripts/mermaid.esm.min.mjs
  - assets/stylesheets/mermaid.css
  - assets/javascripts/MERMAID_VERSION

3. Add the vendored files to your commit:

   git add assets/javascripts/mermaid.min.js assets/javascripts/mermaid.esm.min.mjs assets/stylesheets/mermaid.css
   assets/javascripts/MERMAID_VERSION
   git commit -m "vendor: add mermaid v10.4.0"

Notes:

- If you are behind a corporate proxy or have TLS/SSL restrictions, the PowerShell script may fail ("Could not create
  SSL/TLS secure channel"). In that case, download the files manually
  from https://cdn.jsdelivr.net/npm/mermaid@10.4.0/dist/ and place them into the `assets/` directories.
- The project includes `assets/javascripts/mermaid-loader.js` which will attempt to load mermaid from the CDN at runtime
  if local vendored files are not present. That prevents previews from breaking but for reproducible builds we still
  recommend vendoring the files in the repo.
- To automate in CI, use the `make vendor-mermaid` or the `make check-mermaid` target (see the repository Makefile).
  `make check-mermaid` will fail if the vendored files are not present.

