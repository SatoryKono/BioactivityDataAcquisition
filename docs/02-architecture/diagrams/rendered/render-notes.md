# Render Notes

- Text-missing issue was reproduced in `rendered/*.png` and fixed.
- Root cause: missing system fonts for headless Chromium.
- Fix applied: installed `fontconfig`, `fonts-dejavu-core`, `fonts-liberation`, `fonts-noto-core`, `fonts-noto-color-emoji`.
- Re-rendered all diagrams with Mermaid CLI (`mmdc 11.12.0`) and Puppeteer config (`--no-sandbox`).
- Result: all `.mermaid` files rendered successfully (`156/156`).
